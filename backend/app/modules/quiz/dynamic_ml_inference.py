"""Misconception prediction from a completed dynamic Quiz's saved first answers.

Never import or deserialize the model on normal app startup. Predictions run
for the released bank when QUIZ_ML_ENABLED=true, or in the isolated demo SQLite
file with its two development flags. Prediction only reads saved evidence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE, settings
from app.modules.quiz.dynamic_ml_features import (
    DynamicFeatureError, FEATURE_BANK_VERSIONS, FEATURE_NAMES, FEATURE_SCHEMA_VERSION,
    SUPPORTED_BANK_VERSION, extract_dynamic_features_for_session,
)
from app.modules.quiz.models import QuizSession
from app.modules.quiz.service import QuizNotFoundError


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEMO_DATABASE_PATH = PROJECT_ROOT / "tmp" / "quiz_dynamic_demo.sqlite"
ARTIFACT_DIR = PROJECT_ROOT / "local_ml_artifacts" / "quiz_dynamic_62_demo"
MANIFEST_NAME = "quiz_dynamic_62_SYNTHETIC_DEMO_manifest.json"
MODEL_NAME = "quiz_dynamic_62_SYNTHETIC_DEMO.joblib"
TARGET_COLUMNS = ("target_M1", "target_M2", "target_M3", "target_M4")
LABELS = ("M1", "M2", "M3", "M4")
ORIGIN = "SYNTHETIC_ENGINEERING_DEMO_ONLY"
# The exported manifest still carries the status from before review. The subject
# teacher verified the M1–M4 category definitions on 2026-10-15 (evidence held by
# the Quiz owner). This covers the categories, not the model's training labels.
TAXONOMY_VERSION = "m3a-taxonomy-v1-proposed"
TAXONOMY_TEACHER_VERIFIED_ON = "2026-10-15"


class ArtifactMissingError(ValueError):
    pass


class ArtifactIncompatibleError(ValueError):
    pass


def isolated_demo_enabled(database: Session) -> bool:
    """Require both flags and the exact local SQLite demo file, not any DB URL."""
    if not (settings.quiz_dynamic_dev_enabled and settings.quiz_dynamic_ml_demo_enabled):
        return False
    bind = database.get_bind()
    url = make_url(str(bind.url if hasattr(bind, "url") else bind.engine.url))
    return (url.get_backend_name() == "sqlite" and url.database not in (None, ":memory:")
            and Path(url.database).resolve() == DEMO_DATABASE_PATH.resolve())


class QuizMLSettings(BaseSettings):
    quiz_ml_enabled: bool = False
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


def prediction_enabled(database: Session) -> bool:
    return QuizMLSettings().quiz_ml_enabled or isolated_demo_enabled(database)


def _unavailable(session_id: str, reason: str) -> dict:
    return {
        "quiz_session_id": session_id,
        "status": "unavailable",
        "reason": reason,
        "research_validated": False,
        "predictions": [],
    }


def _load_verified_model():
    manifest_path = ARTIFACT_DIR / MANIFEST_NAME
    if not manifest_path.is_file() or not (ARTIFACT_DIR / MODEL_NAME).is_file():
        raise ArtifactMissingError("Demo model or manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIncompatibleError("Manifest is unreadable") from error
    if not isinstance(manifest, dict):
        raise ArtifactIncompatibleError("Manifest is invalid")
    if (manifest.get("model_file") != MODEL_NAME or
            manifest.get("feature_schema_version") != FEATURE_SCHEMA_VERSION or
            manifest.get("bank_version") != SUPPORTED_BANK_VERSION or
            manifest.get("feature_names") != list(FEATURE_NAMES) or
            manifest.get("target_columns") != list(TARGET_COLUMNS) or
            manifest.get("thresholds") != dict.fromkeys(LABELS, 0.5) or
            manifest.get("training_data_origin") != ORIGIN or
            manifest.get("research_validated") is not False or
            manifest.get("target_taxonomy_status") !=
                "PROPOSED_NOT_INDEPENDENTLY_TEACHER_VERIFIED" or
            not isinstance(manifest.get("model_version"), str) or
            not manifest["model_version"]):
        raise ArtifactIncompatibleError("Manifest does not match the demo contract")
    expected_hash = manifest.get("model_sha256")
    if (not isinstance(expected_hash, str) or len(expected_hash) != 64 or
            any(letter not in "0123456789abcdef" for letter in expected_hash)):
        raise ArtifactIncompatibleError("Invalid model checksum")
    model_path = ARTIFACT_DIR / MODEL_NAME
    try:
        actual_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    except OSError as error:
        raise ArtifactMissingError("Model file is unreadable") from error
    if not hmac.compare_digest(expected_hash, actual_hash):
        raise ArtifactIncompatibleError("Model checksum does not match manifest")

    # joblib uses pickle. Deserialize only after all local-path and manifest
    # gates above; this directory contains the user-supplied Colab artifact.
    try:
        import joblib
        model = joblib.load(model_path)
        estimator = model.named_steps["estimator"]
        if (getattr(model, "n_features_in_", None) != len(FEATURE_NAMES) or
                list(getattr(model, "feature_names_in_", [])) != list(FEATURE_NAMES) or
                getattr(estimator, "multilabel_", None) is not True or
                list(getattr(estimator, "classes_", [])) != list(range(4)) or
                len(getattr(estimator, "estimators_", [])) != 4):
            raise ArtifactIncompatibleError("Fitted model has incompatible inputs or outputs")
    except Exception as error:
        if isinstance(error, ArtifactIncompatibleError):
            raise
        raise ArtifactIncompatibleError("Fitted model cannot be loaded or verified") from error
    return model, manifest


def predict_completed_dynamic_session(database: Session, session_id: str) -> dict:
    session = database.scalar(select(QuizSession).where(QuizSession.quiz_session_id == session_id))
    if session is None:
        raise QuizNotFoundError("Quiz session was not found")
    if session.bank_version not in FEATURE_BANK_VERSIONS or session.status != "completed":
        return _unavailable(session_id, "session_incomplete")
    try:
        vector = extract_dynamic_features_for_session(database, session_id)
    except DynamicFeatureError:
        return _unavailable(session_id, "session_incomplete")
    try:
        model, manifest = _load_verified_model()
    except ArtifactMissingError:
        return _unavailable(session_id, "artifact_missing")
    except ArtifactIncompatibleError as error:
        logger.warning("Dynamic ML artifact unavailable: %s", error)
        return _unavailable(session_id, "artifact_incompatible")
    if (vector["feature_schema_version"] != manifest["feature_schema_version"] or
            # The model was trained on the draft bank; the released bank has identical items.
            manifest["bank_version"] != SUPPORTED_BANK_VERSION or
            vector["bank_version"] not in FEATURE_BANK_VERSIONS or
            vector["feature_names"] != manifest["feature_names"] or
            list(vector["features"]) != manifest["feature_names"]):
        return _unavailable(session_id, "artifact_incompatible")
    try:
        import pandas as pd
        frame = pd.DataFrame([[vector["features"][name] for name in FEATURE_NAMES]],
                             columns=FEATURE_NAMES)
        probabilities = model.predict_proba(frame).tolist()
        if (len(probabilities) != 1 or len(probabilities[0]) != 4 or
                any(not isinstance(value, (int, float)) or not math.isfinite(value)
                    or not 0 <= value <= 1 for value in probabilities[0])):
            raise ValueError("Model returned invalid probabilities")
    except Exception as error:
        logger.warning("Dynamic ML prediction failed: %s", type(error).__name__)
        return _unavailable(session_id, "prediction_failed")
    return {
        "quiz_session_id": session_id,
        "status": "available",
        "model_version": manifest["model_version"],
        "feature_schema_version": vector["feature_schema_version"],
        "bank_version": vector["bank_version"],
        "training_data_origin": ORIGIN,
        "research_validated": False,
        "taxonomy_version": TAXONOMY_VERSION,
        "taxonomy_teacher_verified_on": TAXONOMY_TEACHER_VERIFIED_ON,
        "predictions": [
            {"label": label, "probability": float(probability),
             "threshold": 0.5, "flagged": probability >= 0.5}
            for label, probability in zip(LABELS, probabilities[0])
        ],
    }
