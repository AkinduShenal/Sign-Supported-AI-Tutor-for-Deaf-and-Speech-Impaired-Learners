"""Game business logic: sessions, event/attempt persistence, and the
Milestone 3 Batch 4 feature engineering that turns raw gameplay into one
game_results row (Steps 15-17)."""

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


# Milestone 3's assessment blueprint (Step 10): a pre-tutor assessment is
# always 2 Easy + 2 Medium + 2 Hard diagnostic tasks, 6 total. Fixed here
# rather than derived from however many tasks happen to have rows, so a
# session abandoned early is correctly seen as incomplete rather than
# "complete with 3 tasks."
EASY_TASKS_REQUIRED = 2
MEDIUM_TASKS_REQUIRED = 2
HARD_TASKS_REQUIRED = 2
ASSESSMENT_TASKS_TOTAL = EASY_TASKS_REQUIRED + MEDIUM_TASKS_REQUIRED + HARD_TASKS_REQUIRED


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

    # Milestone 3 Step 16: completion is backend-decided, not a frontend
    # "questionNumber === 6" check. If this session actually reached the
    # 2+2+2 blueprint, calculate and persist its game_results row now
    # (Step 17) — idempotent, so completing an already-completed session
    # again (e.g. a retried network call) never creates a duplicate.
    if is_assessment_complete(game_session_id, database):
        create_game_result(game_session_id, database)

    return _to_session_response(session)


def is_assessment_complete(game_session_id: str, database: Session) -> bool:
    """True once at least 2 Easy, 2 Medium and 2 Hard tasks have been
    *processed* for this session — a wrong or skipped task still counts,
    only success does not (Milestone 3 Step 16). Counts distinct task_id
    rows per difficulty_level, so a task that somehow got two attempt rows
    isn't double-counted."""

    rows = database.execute(
        select(
            GameTaskAttemptModel.difficulty_level,
            func.count(func.distinct(GameTaskAttemptModel.task_id)),
        )
        .where(GameTaskAttemptModel.game_session_id == game_session_id)
        .group_by(GameTaskAttemptModel.difficulty_level)
    ).all()
    counts = {difficulty: count for difficulty, count in rows}

    return (
        counts.get("easy", 0) >= EASY_TASKS_REQUIRED
        and counts.get("medium", 0) >= MEDIUM_TASKS_REQUIRED
        and counts.get("hard", 0) >= HARD_TASKS_REQUIRED
    )


def calculate_session_features(game_session_id: str, database: Session) -> dict[str, float | int]:
    """Milestone 3 Step 15. Every rate is defined once, here, and nothing
    else in the codebase is allowed to compute these numbers independently
    (the frontend never calculates a rate itself — see schemas.py). All
    divisions guard their denominator and return 0.0 rather than raising.

    tasks_total              fixed at ASSESSMENT_TASKS_TOTAL (6) — the
                              blueprint size, not however many rows exist.
    tasks_attempted          attempt rows where attempts_count > 0 (a task
                              that was shown but never actually tried
                              doesn't count as "attempted").
    tasks_completed          attempt rows with is_completed = true.
    successful_tasks         attempt rows with is_successful = true.
    game_success_rate        successful_tasks / tasks_attempted.
    game_completion_rate     tasks_completed / tasks_total.
    game_avg_attempts_per_task
                              sum(attempts_count) / tasks_attempted — the
                              average number of tries per task actually
                              attempted (unattempted tasks don't dilute it).
    game_hint_rate           (tasks where hints_used > 0) / tasks_total —
                              the share of the assessment's tasks where a
                              hint was used at all. Deliberately a share of
                              *tasks*, not "hints / tasks" (which has no
                              upper bound once a task gets more than one
                              hint) — game_results.game_hint_rate has a
                              database-enforced 0-1 range, same as every
                              other *_rate column. total_hint_count below
                              is the raw, unbounded count for anyone who
                              needs it. This definition must not change
                              silently later (Step 15).
    game_active_time_sec     sum(time_taken_sec) across attempt rows,
                              rounded to a whole second.
    wrong_attempt_count      sum(wrong_attempts) across attempt rows.
    retry_count               count of RETRY_STARTED gameplay_events for
                              this session (attempt rows have no retry
                              field of their own).
    total_hint_count         sum(hints_used) across attempt rows.
    skipped_step_count       sum(skipped_steps) across attempt rows.
    """

    attempts = database.execute(
        select(GameTaskAttemptModel).where(
            GameTaskAttemptModel.game_session_id == game_session_id
        )
    ).scalars().all()

    tasks_attempted = sum(1 for a in attempts if a.attempts_count > 0)
    tasks_completed = sum(1 for a in attempts if a.is_completed)
    successful_tasks = sum(1 for a in attempts if a.is_successful)
    tasks_with_hint_used = sum(1 for a in attempts if a.hints_used > 0)
    total_hint_count = sum(a.hints_used for a in attempts)
    wrong_attempt_count = sum(a.wrong_attempts for a in attempts)
    skipped_step_count = sum(a.skipped_steps for a in attempts)
    game_active_time_sec = round(sum(a.time_taken_sec for a in attempts))
    sum_attempts_count = sum(a.attempts_count for a in attempts)

    retry_count = database.scalar(
        select(func.count(GameplayEventModel.id)).where(
            GameplayEventModel.game_session_id == game_session_id,
            GameplayEventModel.event_type == "RETRY_STARTED",
        )
    ) or 0

    return {
        "tasks_total": ASSESSMENT_TASKS_TOTAL,
        "tasks_attempted": tasks_attempted,
        "tasks_completed": tasks_completed,
        "successful_tasks": successful_tasks,
        # min(1.0, ...) guards game_results' database-enforced 0-1 range on
        # every *_rate column — only reachable with malformed attempt data
        # (e.g. is_successful=true with attempts_count=0) that the real
        # game flow never sends, but a 500 from a bad rate is worse than a
        # clamped one.
        "game_success_rate": min(1.0, successful_tasks / tasks_attempted)
        if tasks_attempted
        else 0.0,
        "game_completion_rate": min(1.0, tasks_completed / ASSESSMENT_TASKS_TOTAL)
        if ASSESSMENT_TASKS_TOTAL
        else 0.0,
        "game_avg_attempts_per_task": (sum_attempts_count / tasks_attempted)
        if tasks_attempted
        else 0.0,
        "game_hint_rate": min(1.0, tasks_with_hint_used / ASSESSMENT_TASKS_TOTAL)
        if ASSESSMENT_TASKS_TOTAL
        else 0.0,
        "game_active_time_sec": game_active_time_sec,
        "wrong_attempt_count": wrong_attempt_count,
        "retry_count": retry_count,
        "total_hint_count": total_hint_count,
        "skipped_step_count": skipped_step_count,
    }


# Milestone 3 Step 17: behavioral_difficulty / game_mastery_score /
# engagement_level (and the newer low/medium/high variants added this
# milestone) are NOT NULL columns on the pre-existing, Tutor-shared
# GameResult table — the schema doesn't permit leaving them out. Rather
# than silently leaving them at some arbitrary default, they're filled by
# a small, transparent, deterministic set of thresholds on the features
# above. This is NOT a trained model — same rule as the Tutor's
# "rule-based-v2" strategy model (see strategy_model.py): a heuristic
# placeholder, clearly labelled via model_version, until real ML lands.
PROTOTYPE_MODEL_VERSION = "game-heuristic-v1"


def _derive_prototype_indicators(
    game_success_rate: float, game_avg_attempts_per_task: float, game_hint_rate: float
) -> dict[str, str | float]:
    if game_success_rate >= 0.8 and game_avg_attempts_per_task <= 1.5:
        mastery_level = "high"
        game_difficulty_level = "advanced"
        behavioral_difficulty = "low"
    elif game_success_rate >= 0.5:
        mastery_level = "medium"
        game_difficulty_level = "intermediate"
        behavioral_difficulty = "medium"
    else:
        mastery_level = "low"
        game_difficulty_level = "beginner"
        behavioral_difficulty = "high"

    if game_hint_rate >= 0.5:
        hint_dependency_level = "high"
    elif game_hint_rate >= 0.2:
        hint_dependency_level = "medium"
    else:
        hint_dependency_level = "low"

    # Engagement mirrors completion/success directly for this milestone —
    # there's no separate signal (e.g. time-on-task vs. expected time) to
    # derive it from yet.
    engagement_level = mastery_level

    return {
        "engagement_level": engagement_level,
        "behavioral_difficulty": behavioral_difficulty,
        "hint_dependency": game_hint_rate,
        "game_mastery_score": game_success_rate,
        "game_difficulty_level": game_difficulty_level,
        "game_mastery_level": mastery_level,
        "game_engagement_level": engagement_level,
        "hint_dependency_level": hint_dependency_level,
    }


def create_game_result(game_session_id: str, database: Session) -> GameResultResponse:
    """Idempotent: if a game_results row already exists for this session
    (its game_session_id is unique), that row is returned as-is rather
    than recalculated — this milestone's features are deterministic from
    already-persisted data, so there's nothing to refresh."""

    existing = database.scalar(
        select(GameResultModel).where(GameResultModel.game_session_id == game_session_id)
    )
    if existing is not None:
        return _to_result_response(existing)

    session = _get_session_or_raise(game_session_id, database)
    features = calculate_session_features(game_session_id, database)
    indicators = _derive_prototype_indicators(
        game_success_rate=features["game_success_rate"],
        game_avg_attempts_per_task=features["game_avg_attempts_per_task"],
        game_hint_rate=features["game_hint_rate"],
    )

    result = GameResultModel(
        game_session_id=session.game_session_id,
        student_id=session.student_id,
        concept_id=session.concept_id,
        learning_cycle_id=session.learning_cycle_id,
        assessment_phase=session.assessment_phase,
        completed_at=datetime.now(UTC),
        model_version=PROTOTYPE_MODEL_VERSION,
        **features,
        **indicators,
    )
    database.add(result)
    database.commit()
    database.refresh(result)
    return _to_result_response(result)


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
