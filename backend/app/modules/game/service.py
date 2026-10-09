"""Game business logic: sessions, event/attempt persistence.

calculate_session_features() and create_game_result() are deliberately not
here yet — they're Milestone 3 Batch 4 (Steps 15-17), which documents each
rate formula properly rather than guessing it here.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.game.models import GameplayEvent as GameplayEventModel
from app.modules.game.models import GameResult as GameResultModel
from app.modules.game.models import GameSession as GameSessionModel
from app.modules.game.models import GameTaskAttempt as GameTaskAttemptModel
from app.modules.game.schemas import (
    CreateGameSessionRequest,
    GameplayEventRequest,
    GameplayEventResponse,
    GameResultResponse,
    GameSessionResponse,
    GameSessionStatus,
    GameTaskAttemptRequest,
    GameTaskAttemptResponse,
)


class GameSessionNotFoundError(ValueError):
    pass


class GameResultNotFoundError(ValueError):
    pass


def create_game_session(
    request: CreateGameSessionRequest, database: Session
) -> GameSessionResponse:
    session = GameSessionModel(
        game_session_id=str(uuid.uuid4()),
        student_id=request.student_id,
        concept_id=request.concept_id,
        learning_cycle_id=request.learning_cycle_id,
        assessment_phase=request.assessment_phase.value,
        status=GameSessionStatus.IN_PROGRESS.value,
    )
    database.add(session)
    database.commit()
    database.refresh(session)
    return _to_session_response(session)


def record_game_event(
    request: GameplayEventRequest, database: Session
) -> GameplayEventResponse:
    _get_session_or_raise(request.game_session_id, database)

    event = GameplayEventModel(
        game_session_id=request.game_session_id,
        task_id=request.task_id,
        event_type=request.event_type.value,
        event_timestamp=request.event_timestamp,
        event_payload=request.event_payload,
    )
    database.add(event)
    database.commit()
    database.refresh(event)
    return _to_event_response(event)


def save_task_attempt(
    request: GameTaskAttemptRequest, database: Session
) -> GameTaskAttemptResponse:
    _get_session_or_raise(request.game_session_id, database)

    attempt = GameTaskAttemptModel(
        game_session_id=request.game_session_id,
        task_id=request.task_id,
        attempt_number=request.attempt_number,
        attempts_count=request.attempts_count,
        wrong_attempts=request.wrong_attempts,
        hints_used=request.hints_used,
        skipped_steps=request.skipped_steps,
        time_taken_sec=request.time_taken_sec,
        is_completed=request.is_completed,
        is_successful=request.is_successful,
        score=request.score,
        activity_id=request.activity_id,
        variant_id=request.variant_id,
        difficulty_level=request.difficulty_level.value if request.difficulty_level else None,
    )
    database.add(attempt)
    database.commit()
    database.refresh(attempt)
    return _to_attempt_response(attempt)


def complete_game_session(game_session_id: str, database: Session) -> GameSessionResponse:
    session = _get_session_or_raise(game_session_id, database)
    session.status = GameSessionStatus.COMPLETED.value
    session.completed_at = datetime.now(UTC)
    database.commit()
    database.refresh(session)
    return _to_session_response(session)


def get_variant_usage_counts(
    student_id: str, concept_id: str, database: Session
) -> dict[str, int]:
    """Count completed task attempts per variant_id for this student and
    concept, across every session (not just the current one). The frontend
    excludes any variant at or above 2 before picking the next assessment's
    6 tasks (Milestone 3 Step 13). Joins through GameSession because
    GameTaskAttempt itself has no student_id/concept_id of its own."""

    rows = database.execute(
        select(GameTaskAttemptModel.variant_id, func.count(GameTaskAttemptModel.id))
        .join(
            GameSessionModel,
            GameSessionModel.game_session_id == GameTaskAttemptModel.game_session_id,
        )
        .where(
            GameSessionModel.student_id == student_id,
            GameSessionModel.concept_id == concept_id,
            GameTaskAttemptModel.variant_id.is_not(None),
        )
        .group_by(GameTaskAttemptModel.variant_id)
    ).all()
    return {variant_id: count for variant_id, count in rows}


def get_game_result(game_session_id: str, database: Session) -> GameResultResponse:
    result = database.scalar(
        select(GameResultModel).where(GameResultModel.game_session_id == game_session_id)
    )
    if result is None:
        raise GameResultNotFoundError(
            f"No game_results row for game_session_id={game_session_id!r}"
        )
    return _to_result_response(result)


def _get_session_or_raise(game_session_id: str, database: Session) -> GameSessionModel:
    session = database.scalar(
        select(GameSessionModel).where(GameSessionModel.game_session_id == game_session_id)
    )
    if session is None:
        raise GameSessionNotFoundError(
            f"No game_sessions row for game_session_id={game_session_id!r}"
        )
    return session


def _to_session_response(session: GameSessionModel) -> GameSessionResponse:
    return GameSessionResponse(
        game_session_id=session.game_session_id,
        student_id=session.student_id,
        concept_id=session.concept_id,
        learning_cycle_id=session.learning_cycle_id,
        assessment_phase=session.assessment_phase,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
    )


def _to_event_response(event: GameplayEventModel) -> GameplayEventResponse:
    return GameplayEventResponse(
        id=event.id,
        game_session_id=event.game_session_id,
        task_id=event.task_id,
        event_type=event.event_type,
        event_timestamp=event.event_timestamp,
        event_payload=event.event_payload,
    )


def _to_attempt_response(attempt: GameTaskAttemptModel) -> GameTaskAttemptResponse:
    return GameTaskAttemptResponse(
        id=attempt.id,
        game_session_id=attempt.game_session_id,
        task_id=attempt.task_id,
        attempt_number=attempt.attempt_number,
        attempts_count=attempt.attempts_count,
        wrong_attempts=attempt.wrong_attempts,
        hints_used=attempt.hints_used,
        skipped_steps=attempt.skipped_steps,
        time_taken_sec=attempt.time_taken_sec,
        is_completed=attempt.is_completed,
        is_successful=attempt.is_successful,
        score=attempt.score,
        activity_id=attempt.activity_id,
        variant_id=attempt.variant_id,
        difficulty_level=attempt.difficulty_level,
    )


def _to_result_response(result: GameResultModel) -> GameResultResponse:
    return GameResultResponse(
        game_session_id=result.game_session_id,
        student_id=result.student_id,
        concept_id=result.concept_id,
        learning_cycle_id=result.learning_cycle_id,
        assessment_phase=result.assessment_phase,
        tasks_total=result.tasks_total,
        tasks_attempted=result.tasks_attempted,
        tasks_completed=result.tasks_completed,
        successful_tasks=result.successful_tasks,
        game_success_rate=result.game_success_rate,
        game_completion_rate=result.game_completion_rate,
        game_avg_attempts_per_task=result.game_avg_attempts_per_task,
        game_hint_rate=result.game_hint_rate,
        game_difficulty_level=result.game_difficulty_level,
        game_active_time_sec=result.game_active_time_sec,
        wrong_attempt_count=result.wrong_attempt_count,
        retry_count=result.retry_count,
        total_hint_count=result.total_hint_count,
        skipped_step_count=result.skipped_step_count,
        engagement_level=result.engagement_level,
        behavioral_difficulty=result.behavioral_difficulty,
        hint_dependency=result.hint_dependency,
        game_mastery_score=result.game_mastery_score,
        game_mastery_level=result.game_mastery_level,
        game_engagement_level=result.game_engagement_level,
        hint_dependency_level=result.hint_dependency_level,
        model_version=result.model_version,
        completed_at=result.completed_at,
    )
