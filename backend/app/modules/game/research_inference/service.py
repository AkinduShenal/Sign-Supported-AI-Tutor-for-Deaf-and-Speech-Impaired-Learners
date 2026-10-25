"""Approved saved-evidence projection and bounded isolated model execution."""

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..models import GameSession
from .access import HEADERS, ResearchAccess, ResearchMLSettings, not_available, unavailable
from .contract import CLASS_ORDER, CONTRACT, MODEL_SHA256, MODEL_STATUS, MODEL_VERSION
from .legacy_adapter import EvidenceUnavailable, adapt_saved_session


class PredictionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["experimental_prediction"] = "experimental_prediction"
    predicted_level: Literal["Beginner", "Intermediate", "Advanced"]
    probabilities: dict[str, float]
    model_name: str
    model_version: str = MODEL_VERSION
    model_status: Literal[MODEL_STATUS] = MODEL_STATUS
    teacher_verified: Literal[False] = False
    feature_source: Literal["validated_saved_game_session"] = "validated_saved_game_session"
    feature_contract: Literal[CONTRACT] = CONTRACT
    model_checksum: Literal[MODEL_SHA256] = MODEL_SHA256
    model_metadata: dict
    runtime: dict

    @model_validator(mode="after")
    def valid_probabilities(self):
        if (set(self.probabilities) != set(CLASS_ORDER)
                or any(not math.isfinite(p) or not 0 <= p <= 1 for p in self.probabilities.values())
                or abs(sum(self.probabilities.values()) - 1) > 1e-12):
            raise ValueError("Invalid probabilities")
        return self


def run_worker(settings: ResearchMLSettings, features: dict | None) -> dict:
    worker = Path(__file__).with_name("worker.py").resolve()
    # Do not give the isolated process API tokens, DB credentials or application env.
    environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP") if key in os.environ}
    environment.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1")
    try:
        completed = subprocess.run(
            [str(settings.game_ml_python), "-I", "-B", str(worker), str(settings.game_ml_model_archive)],
            input=json.dumps({"features": features}, allow_nan=False), text=True, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=worker.parent, env=environment,
            timeout=settings.game_ml_timeout_sec, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0 or len(completed.stdout) > 50_000:
            raise ValueError("Worker unavailable")
        result = json.loads(completed.stdout)
        if result.get("model_checksum") != MODEL_SHA256 or result.get("feature_contract") != CONTRACT:
            raise ValueError("Worker contract mismatch")
        if result["frozen_reproduction"]["records"] != 10:
            raise ValueError("Missing reproduction evidence")
        return result
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        raise unavailable() from None


def predict_saved_session(access: ResearchAccess, database) -> PredictionResponse:
    binding = access.binding
    try:
        session = database.scalar(select(GameSession).where(GameSession.game_session_id == binding.game_session_id))
        if session is None or any((
            session.student_id != binding.student_code,
            session.concept_id != binding.concept_id,
            session.learning_cycle_id != binding.learning_cycle_id,
            session.assessment_phase != binding.assessment_phase,
        )):
            raise not_available()
        features = adapt_saved_session(binding.game_session_id, database)
    except HTTPException:
        raise
    except (EvidenceUnavailable, ValueError, TypeError, KeyError, ArithmeticError, AttributeError):
        raise HTTPException(422, "Saved Game evidence is unavailable for experimental prediction.", headers=HEADERS) from None
    except SQLAlchemyError:
        raise unavailable() from None
    # Snapshot is complete; release the read transaction before subprocess work.
    database.rollback()
    result = run_worker(access.settings, features)
    try:
        return PredictionResponse(
            predicted_level=result["predicted_level"], probabilities=result["probabilities"],
            model_name=result["model_metadata"]["model_name"], model_metadata=result["model_metadata"],
            runtime=result["runtime"],
        )
    except (ValueError, TypeError, KeyError):
        raise unavailable() from None
