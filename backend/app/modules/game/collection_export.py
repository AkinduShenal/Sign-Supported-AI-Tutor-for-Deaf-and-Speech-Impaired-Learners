"""Researcher-authorized downloads using the existing read-only CSV exporter."""

import secrets
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE
from scripts.export_game_collection import export_game_data


class GameExportSettings(BaseSettings):
    game_collection_export_key: SecretStr | None = None
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


export_bearer = HTTPBearer(auto_error=False)


def require_export_access(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(export_bearer)],
) -> None:
    configured = GameExportSettings().game_collection_export_key
    expected = configured.get_secret_value().strip() if configured else ""
    if len(expected) < 16:
        raise HTTPException(503, "Researcher CSV download has not been configured.")
    if credentials is None:
        raise HTTPException(
            401,
            "A researcher export key is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(credentials.credentials.encode(), expected.encode()):
        raise HTTPException(403, "The researcher export key is incorrect.")


def collection_zip(database: Session) -> tuple[bytes, str]:
    # One consistent read-only PostgreSQL snapshot; never create or finish
    # sessions, and never manufacture independent assessment labels.
    if database.get_bind().dialect.name == "postgresql":
        database.connection().exec_driver_sql(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        )
    buffer = BytesIO()
    with TemporaryDirectory(prefix="game-csv-export-") as temporary:
        folder = Path(temporary)
        export_game_data(database, folder)
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            for name in (
                "game_sessions.csv",
                "student_answers.csv",
                "game_events.csv",
                "game_analytics.csv",
                "independent_assessment_labels.csv",
                "manifest.json",
            ):
                archive.writestr(name, (folder / name).read_bytes())
    filename = datetime.now(UTC).strftime("game-collection-%Y%m%dT%H%M%SZ.zip")
    return buffer.getvalue(), filename
