"""Strict saved-session portion of the verified legacy prototype. No CSV fallback."""

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ml_preview import read_ml_input_preview
from ..models import GameResult, GameSession
from ..service import GameResultNotFoundError, calculate_session_features
from .contract import FEATURE_ORDER


class EvidenceUnavailable(ValueError):
    pass


def project_legacy(values: dict, tasks_total: int) -> dict:
    """Independent legacy object; never mutate preview or saved coverage values."""
    if type(tasks_total) is not int or tasks_total != 6 or set(values) != set(FEATURE_ORDER):
        raise EvidenceUnavailable("Invalid six-task feature schema")
    for name, value in values.items():
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise EvidenceUnavailable("Invalid numerical evidence")
        if name.endswith("_count") or name == "game_active_time_sec":
            if type(value) is not int:
                raise EvidenceUnavailable("Integral saved counts/duration required")
        if name in ("first_attempt_accuracy", "game_success_rate", "game_hint_rate") and value > 1:
            raise EvidenceUnavailable("Invalid saved accuracy/coverage")
    result = {name: values[name] for name in FEATURE_ORDER}
    for name in ("first_attempt_accuracy", "game_success_rate", "game_avg_attempts_per_task"):
        result[name] = round(result[name], 3)
    result["game_hint_rate"] = round(values["total_hint_count"] / tasks_total, 3)
    return result


def matches_saved(saved_value, calculated) -> bool:
    """Counts must match exactly; floats only to storage precision (PostgreSQL may
    return 15 significant digits, e.g. 2.33333333333333 for 14/6)."""
    if isinstance(saved_value, float) or isinstance(calculated, float):
        return math.isclose(saved_value, calculated, rel_tol=1e-12, abs_tol=1e-12)
    return saved_value == calculated


def adapt_saved_session(session_id: str, database: Session) -> dict:
    """Caller must authorize manifest context first. No writes or imputation."""
    if database.new or database.dirty or database.deleted:
        raise EvidenceUnavailable("Pending mutations")
    with database.no_autoflush:
        session = database.scalar(select(GameSession).where(GameSession.game_session_id == session_id))
        if session is None or session.status != "completed" or session.completed_at is None:
            raise EvidenceUnavailable("Completed saved session required")
        try:
            preview = read_ml_input_preview(session_id, database)
        except GameResultNotFoundError as error:
            raise EvidenceUnavailable("Saved result missing") from error
        if not preview.all_features_available:
            raise EvidenceUnavailable("Strict preview evidence unavailable")
        saved = database.scalar(select(GameResult).where(GameResult.game_session_id == session_id))
        calculated = calculate_session_features(session_id, database)
        if saved is None or any(not matches_saved(getattr(saved, key), value) for key, value in calculated.items()):
            raise EvidenceUnavailable("Saved aggregates conflict with source evidence")
        if not saved.tasks_total == saved.tasks_attempted == saved.tasks_completed == 6:
            raise EvidenceUnavailable("Incomplete task roster")
        return project_legacy(preview.features.model_dump(), saved.tasks_total)
