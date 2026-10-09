import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GameResult(Base):
    __tablename__ = "game_results"
    __table_args__ = (
        CheckConstraint("tasks_total > 0", name="tasks_total_positive"),
        CheckConstraint(
            "tasks_attempted > 0 AND tasks_attempted <= tasks_total",
            name="tasks_attempted_valid",
        ),
        CheckConstraint(
            "tasks_completed >= 0 AND tasks_completed <= tasks_attempted",
            name="tasks_completed_valid",
        ),
        CheckConstraint(
            "successful_tasks >= 0 AND successful_tasks <= tasks_completed",
            name="successful_tasks_valid",
        ),
        CheckConstraint(
            "game_success_rate >= 0 AND game_success_rate <= 1",
            name="game_success_rate_range",
        ),
        CheckConstraint(
            "game_mastery_score >= 0 AND game_mastery_score <= 1",
            name="game_mastery_score_range",
        ),
        CheckConstraint(
            "hint_dependency >= 0 AND hint_dependency <= 1",
            name="hint_dependency_range",
        ),
        CheckConstraint(
            "engagement_level IN ('low', 'medium', 'high')",
            name="engagement_level_valid",
        ),
        CheckConstraint(
            "behavioral_difficulty IN ('low', 'medium', 'high')",
            name="behavioral_difficulty_valid",
        ),
        CheckConstraint(
            "game_completion_rate >= 0 AND game_completion_rate <= 1",
            name="game_completion_rate_range",
        ),
        CheckConstraint(
            "game_avg_attempts_per_task >= 0",
            name="game_avg_attempts_non_negative",
        ),
        CheckConstraint(
            "game_hint_rate >= 0 AND game_hint_rate <= 1",
            name="game_hint_rate_range",
        ),
        CheckConstraint(
            "game_difficulty_level IN ('beginner', 'intermediate', 'advanced')",
            name="game_difficulty_level_valid",
        ),
        CheckConstraint(
            "game_active_time_sec >= 0",
            name="game_active_time_non_negative",
        ),
        CheckConstraint(
            "assessment_phase IS NULL OR assessment_phase IN ('pre_tutor', 'post_tutor')",
            name="assessment_phase_valid",
        ),
        CheckConstraint(
            "game_mastery_level IS NULL OR game_mastery_level IN ('low', 'medium', 'high')",
            name="game_mastery_level_valid",
        ),
        CheckConstraint(
            "game_engagement_level IS NULL OR game_engagement_level IN ('low', 'medium', 'high')",
            name="game_engagement_level_valid",
        ),
        CheckConstraint(
            "hint_dependency_level IS NULL OR hint_dependency_level IN ('low', 'medium', 'high')",
            name="hint_dependency_level_valid",
        ),
        Index("ix_game_results_student_concept", "student_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.game_session_id"), unique=True
    )
    student_id: Mapped[str] = mapped_column(String(100), index=True)
    concept_id: Mapped[str] = mapped_column(String(100), index=True)
    engagement_level: Mapped[str] = mapped_column(String(20))
    behavioral_difficulty: Mapped[str] = mapped_column(String(20))
    hint_dependency: Mapped[float] = mapped_column(Float)
    game_mastery_score: Mapped[float] = mapped_column(Float)
    tasks_total: Mapped[int] = mapped_column(Integer)
    tasks_attempted: Mapped[int] = mapped_column(Integer)
    tasks_completed: Mapped[int] = mapped_column(Integer)
    successful_tasks: Mapped[int] = mapped_column(Integer)
    game_success_rate: Mapped[float] = mapped_column(Float)
    game_completion_rate: Mapped[float] = mapped_column(Float)
    game_avg_attempts_per_task: Mapped[float] = mapped_column(Float)
    game_hint_rate: Mapped[float] = mapped_column(Float)
    game_difficulty_level: Mapped[str] = mapped_column(String(20))
    game_active_time_sec: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # --- Milestone 3 additions. Renaming/removing any *existing* column
    # above would break the Tutor's contract; these are new and additive
    # only, matching the columns that already exist on the shared database
    # (added outside this repo's Alembic history — see Step 3 notes).
    learning_cycle_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    assessment_phase: Mapped[str | None] = mapped_column(String(20), nullable=True)
    wrong_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    total_hint_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_step_count: Mapped[int] = mapped_column(Integer, default=0)
    # Categorical low/medium/high research outputs, separate from the
    # numeric game_mastery_score / hint_dependency above. Prototype-only —
    # must not be presented as validated ML predictions (see Step 17).
    game_mastery_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    game_engagement_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hint_dependency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)


class GameSession(Base):
    """One pre- or post-tutor assessment attempt. Parent of GameplayEvent,
    GameTaskAttempt, and GameResult rows (via game_session_id)."""

    __tablename__ = "game_sessions"
    __table_args__ = (
        CheckConstraint(
            "assessment_phase IN ('pre_tutor', 'post_tutor')",
            name="assessment_phase_valid",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="status_valid",
        ),
        Index("ix_game_sessions_student_concept", "student_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_session_id: Mapped[str] = mapped_column(String(100), unique=True)
    student_id: Mapped[str] = mapped_column(String(100), index=True)
    concept_id: Mapped[str] = mapped_column(String(100), index=True)
    learning_cycle_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    assessment_phase: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class GameplayEvent(Base):
    """Raw, immutable gameplay events for one session. task_id scopes an
    event to a specific diagnostic task within the session.
    """

    __tablename__ = "gameplay_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'GAME_STARTED', 'GAME_COMPLETED', 'SESSION_ENDED', "
            "'TASK_STARTED', 'TASK_COMPLETED', 'QUESTION_SHOWN', "
            "'ANSWER_SUBMITTED', 'ANSWER_CORRECT', 'ANSWER_INCORRECT', "
            "'HINT_REQUESTED', 'RETRY_STARTED', 'STEP_SKIPPED')",
            name="event_type_valid",
        ),
        Index("ix_gameplay_events_session_task", "game_session_id", "task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.game_session_id", ondelete="CASCADE"),
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50))
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class GameTaskAttempt(Base):
    """One row per attempt at a diagnostic task within a session
    (attempt_number distinguishes repeated attempts at the same task_id) —
    the bridge between raw gameplay_events and the session-level
    game_results row.

    activity_id/variant_id/difficulty_level (added via the Milestone 3
    Steps 10-13 migration) are nullable because older rows predate the
    Easy/Medium/Hard variant system and never had them.
    """

    __tablename__ = "game_task_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
        CheckConstraint("attempts_count >= 0", name="attempts_count_non_negative"),
        CheckConstraint("wrong_attempts >= 0", name="wrong_attempts_non_negative"),
        CheckConstraint("hints_used >= 0", name="hints_used_non_negative"),
        CheckConstraint("skipped_steps >= 0", name="skipped_steps_non_negative"),
        CheckConstraint("time_taken_sec >= 0", name="time_taken_sec_non_negative"),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)", name="score_range"
        ),
        CheckConstraint(
            "difficulty_level IS NULL OR difficulty_level IN ('easy', 'medium', 'hard')",
            name="difficulty_level_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.game_session_id", ondelete="CASCADE"),
        index=True,
    )
    task_id: Mapped[str] = mapped_column(String(100))
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    attempts_count: Mapped[int] = mapped_column(Integer, default=1)
    wrong_attempts: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    skipped_steps: Mapped[int] = mapped_column(Integer, default=0)
    time_taken_sec: Mapped[float] = mapped_column(Float, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_successful: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    difficulty_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
