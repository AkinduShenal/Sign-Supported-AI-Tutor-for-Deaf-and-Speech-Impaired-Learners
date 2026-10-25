"""Read-only session evidence preview; never fits models or changes saved results."""

import math
from collections import Counter, defaultdict
from datetime import UTC
from fractions import Fraction

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ml.collection_research import audit_attempt_chronology
from .models import GameResult, GameSession, GameTaskAttempt, GameplayEvent
from .service import GameResultNotFoundError, is_assessment_complete


class MLInputFeatures(BaseModel):
    first_attempt_accuracy: float | None = None
    game_success_rate: float | None = None
    wrong_attempt_count: int | None = None
    retry_count: int | None = None
    total_hint_count: int | None = None
    skipped_step_count: int | None = None
    game_active_time_sec: int | None = None
    game_hint_rate: float | None = None
    game_avg_attempts_per_task: float | None = None


class MLInputPreview(BaseModel):
    game_session_id: str
    features: MLInputFeatures
    unavailable_reasons: dict[str, str]
    all_features_available: bool
    ready_for_inference: bool = False
    model_compatibility: str = "unverified_nine_feature_colab_contract"


def _event_row(event: GameplayEvent, student_id: str) -> dict:
    payload = event.event_payload
    stamp = event.event_timestamp
    if stamp.tzinfo is None:  # SQLite tests drop timezone information.
        stamp = stamp.replace(tzinfo=UTC)
    return {
        "source_event_id": str(event.id),
        "client_event_id": payload.get("client_event_id") if isinstance(payload.get("client_event_id"), str) else "",
        "game_session_id": event.game_session_id,
        "student_id_recorded": student_id,
        "task_id": event.task_id,
        "step_index": str(payload.get("step_index", "")),
        "attempt_number": str(payload.get("attempt_number", "")),
        "event_type": event.event_type,
        "event_timestamp": stamp.isoformat(),
    }


def first_attempt_accuracy(
    session: GameSession, attempts: list[GameTaskAttempt], events: list[GameplayEvent]
) -> float:
    """ResearchObservation.first_attempt_accuracy: correct first / planned steps.

    The denominator comes from saved QUESTION_SHOWN step counts, never from
    eventual successes or only the steps with convenient outcome evidence.
    Hangman's recorded protocol has one final-value step per question.
    """
    starts = [event for event in events if event.event_type == "GAME_STARTED"]
    if len(starts) != 1 or starts[0].event_payload.get("recording_protocol") != "game-evidence-v1":
        raise ValueError("Audited game-evidence-v1 recording is missing.")
    mode = starts[0].event_payload.get("game_type")
    if mode not in ("drag_drop", "hangman"):
        raise ValueError("Recorded Game mode is unavailable.")
    task_ids = {attempt.task_id for attempt in attempts}
    if len(attempts) != 6 or len(task_ids) != 6:
        raise ValueError("The saved six-task roster is incomplete or ambiguous.")
    planned_counts: dict[str, int] = {}
    shown, completed = set(), []
    outcomes = defaultdict(list)
    projected = [_event_row(event, session.student_id) for event in events]
    for event, row in zip(events, projected):
        if event.event_type not in (
            "QUESTION_SHOWN", "TASK_COMPLETED", "ANSWER_CORRECT", "ANSWER_INCORRECT"
        ):
            continue
        payload = event.event_payload
        if event.task_id not in task_ids or payload.get("game_type") != mode:
            raise ValueError("Step evidence does not match the saved task/mode roster.")
        index = payload.get("step_index", 0 if mode == "hangman" else None)
        count = payload.get("step_count", 1 if mode == "hangman" else None)
        if (type(index) is not int or type(count) is not int
                or count < 1 or count > len(events) or not 0 <= index < count
                or (mode == "hangman" and (index != 0 or count != 1))):
            raise ValueError("Recorded planned step counts are missing or inconsistent.")
        prior = planned_counts.setdefault(event.task_id, count)
        if prior != count:
            raise ValueError("Recorded planned step counts disagree.")
        key = (event.task_id, index)
        if event.event_type == "QUESTION_SHOWN":
            shown.add(key)
        elif event.event_type == "TASK_COMPLETED":
            completed.append(key)
        else:
            number = payload.get("attempt_number")
            if type(number) is not int or number < 1 or not row["client_event_id"]:
                raise ValueError("Numbered first-attempt outcome evidence is missing.")
            expected = payload.get("expected_response")
            submitted = payload.get("submitted_value" if mode == "hangman" else "selected_choice")
            if not isinstance(expected, str) or not expected or not isinstance(submitted, str):
                raise ValueError("Recorded expected/submitted responses are missing.")
            correct = (Fraction(submitted) == Fraction(expected)) if mode == "hangman" else submitted == expected
            if correct != (event.event_type == "ANSWER_CORRECT"):
                raise ValueError("Recorded outcome contradicts the submitted response.")
            outcomes[key].append((row, expected))
    planned = {(task, index) for task, count in planned_counts.items() for index in range(count)}
    if (set(planned_counts) != task_ids or shown != planned or set(outcomes) != planned
            or Counter(completed) != Counter({key: 1 for key in planned})):
        raise ValueError("Planned, shown, completed and answered step coverage differs.")
    first_correct = 0
    for rows in outcomes.values():
        if len({expected for _, expected in rows}) != 1:
            raise ValueError("Expected responses disagree within a recorded step.")
        numbered = [row for row, _ in rows]
        audit_attempt_chronology(numbered, projected, mode)
        first_correct += next(row for row in numbered if row["attempt_number"] == "1")["event_type"] == "ANSWER_CORRECT"
    return first_correct / len(planned)


def read_ml_input_preview(game_session_id: str, database: Session) -> MLInputPreview:
    result = database.scalar(select(GameResult).where(GameResult.game_session_id == game_session_id))
    session = database.scalar(select(GameSession).where(GameSession.game_session_id == game_session_id))
    if result is None or session is None:
        raise GameResultNotFoundError("No saved Game result is available for this session.")
    values, reasons = {}, {}
    context_matches = session.status == "completed" and all(
        getattr(result, key) == getattr(session, key)
        for key in ("student_id", "concept_id", "learning_cycle_id", "assessment_phase")
    )
    rates = {"game_success_rate", "game_hint_rate"}
    floating = rates | {"game_avg_attempts_per_task"}
    for name in MLInputFeatures.model_fields:
        if name == "first_attempt_accuracy":
            continue
        value = getattr(result, name, None)
        valid = (type(value) in (int, float) and math.isfinite(value) and value >= 0
                 and (name not in rates or value <= 1)
                 and (name in floating or type(value) is int))
        values[name] = value if context_matches and valid else None
        if values[name] is None:
            reasons[name] = "Saved value is missing, invalid, or belongs to inconsistent session evidence."
    try:
        if not context_matches or not is_assessment_complete(game_session_id, database):
            raise ValueError("Saved assessment evidence is incomplete or inconsistent.")
        attempts = list(database.scalars(select(GameTaskAttempt).where(GameTaskAttempt.game_session_id == game_session_id)))
        events = list(database.scalars(select(GameplayEvent).where(GameplayEvent.game_session_id == game_session_id)))
        values["first_attempt_accuracy"] = first_attempt_accuracy(session, attempts, events)
    except (ValueError, TypeError, KeyError, ZeroDivisionError) as error:
        values["first_attempt_accuracy"] = None
        reasons["first_attempt_accuracy"] = str(error)
    return MLInputPreview(
        game_session_id=game_session_id,
        features=MLInputFeatures(**values),
        unavailable_reasons=reasons,
        all_features_available=not reasons,
    )
