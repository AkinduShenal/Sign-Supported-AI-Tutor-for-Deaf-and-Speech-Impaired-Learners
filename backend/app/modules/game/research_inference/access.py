"""Dedicated researcher credential and explicitly pinned session approvals."""

import hashlib
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import ENV_FILE
from .contract import CONTRACT, KNOWN_EXCLUDED

HEADERS = {"Cache-Control": "no-store"}


def unavailable():
    return HTTPException(503, "Experimental Game prediction is unavailable.", headers=HEADERS)


def not_available():
    return HTTPException(404, "Requested research prediction is unavailable.", headers=HEADERS)


class ResearchMLSettings(BaseSettings):
    game_ml_experimental_enabled: bool = False
    game_ml_research_token: SecretStr | None = None
    game_ml_session_manifest: Path | None = None
    game_ml_manifest_sha256: str | None = None
    game_ml_model_archive: Path | None = None
    game_ml_python: Path | None = None
    game_ml_timeout_sec: int = Field(default=30, ge=1, le=60)
    # Set by compose only: behind Docker's port mapping, a localhost browser
    # arrives from the private bridge gateway rather than 127.0.0.1.
    game_ml_container_network: bool = False
    # Used only to prevent credential reuse; never authenticates this endpoint.
    game_collection_export_key: SecretStr | None = None
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


def get_research_settings() -> ResearchMLSettings:
    try:
        return ResearchMLSettings()
    except (ValueError, TypeError, OSError):
        raise unavailable() from None


class ApprovedSession(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    game_session_id: str = Field(min_length=1, max_length=100)
    student_code: str = Field(pattern=r"^STU_[0-9]{3}$")
    concept_id: str = Field(min_length=1, max_length=100)
    learning_cycle_id: UUID
    assessment_phase: Literal["pre_tutor", "post_tutor"]

    @field_validator("student_code")
    @classmethod
    def exact_code(cls, value):
        if not re.fullmatch(r"STU_[0-9]{3}", value):
            raise ValueError("Invalid student code")
        return value

    @field_validator("game_session_id", "concept_id")
    @classmethod
    def exact_string(cls, value):
        if value.strip() != value:
            raise ValueError("Whitespace is not an identity mapping")
        return value


class ApprovalManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["game-ml-research-access-v1"]
    feature_contract: Literal[CONTRACT]
    approved_by: str = Field(min_length=1, max_length=200)
    approval_reference: str = Field(min_length=1, max_length=500)
    approved_at: AwareDatetime
    legacy_contract_accepted: Literal[True]
    excluded_session_ids: list[str]
    quarantined_session_ids: list[str]
    approved_sessions: list[ApprovedSession]

    @model_validator(mode="after")
    def no_duplicate_approvals(self):
        ids = [entry.game_session_id for entry in self.approved_sessions]
        if len(ids) != len(set(ids)) or not self.approved_by.strip() or not self.approval_reference.strip():
            raise ValueError("Approval manifest is ambiguous")
        return self


@dataclass(frozen=True)
class ResearchAccess:
    settings: ResearchMLSettings
    binding: ApprovedSession
    excluded: frozenset[str]


research_bearer = HTTPBearer(auto_error=False, scheme_name="GameMLResearchBearer")


def require_research_access(
    game_session_id: str,
    settings: Annotated[ResearchMLSettings, Depends(get_research_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(research_bearer)],
) -> ResearchAccess:
    if not settings.game_ml_experimental_enabled:
        raise unavailable()
    expected = settings.game_ml_research_token.get_secret_value() if settings.game_ml_research_token else ""
    # Match the export endpoint's trimming rule when preventing key reuse.
    export = settings.game_collection_export_key.get_secret_value().strip() if settings.game_collection_export_key else ""
    if len(expected) < 32 or expected.strip() != expected or (export and secrets.compare_digest(expected.encode(), export.encode())):
        raise unavailable()
    if credentials is None or not secrets.compare_digest(credentials.credentials.encode(), expected.encode()):
        raise HTTPException(401, "Research authentication required.", headers={**HEADERS, "WWW-Authenticate": "Bearer"})
    try:
        path, pin = settings.game_ml_session_manifest, settings.game_ml_manifest_sha256
        if path is None or pin is None or not re.fullmatch(r"[a-f0-9]{64}", pin):
            raise ValueError("Missing approval configuration")
        if not path.is_absolute() or path.stat().st_size > 1_000_000:
            raise ValueError("Invalid manifest path/size")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != pin:
            raise ValueError("Manifest approval checksum mismatch")
        manifest = ApprovalManifest.model_validate_json(data)
        excluded = KNOWN_EXCLUDED | frozenset(manifest.excluded_session_ids) | frozenset(manifest.quarantined_session_ids)
        matches = [entry for entry in manifest.approved_sessions if entry.game_session_id == game_session_id]
        if game_session_id in excluded or len(matches) != 1:
            raise not_available()
        for configured in (settings.game_ml_python, settings.game_ml_model_archive):
            if configured is None or not configured.is_absolute() or not configured.is_file():
                raise ValueError("Missing trusted local runtime/artifact")
        return ResearchAccess(settings, matches[0], excluded)
    except HTTPException:
        raise
    except (OSError, ValueError, TypeError):
        raise unavailable() from None
