import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Index, Integer, String, func
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
        Index("ix_game_results_student_concept", "student_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    game_session_id: Mapped[str] = mapped_column(String(100), unique=True)
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
