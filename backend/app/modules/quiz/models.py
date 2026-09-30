import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuizResult(Base):
    __tablename__ = "quiz_results"
    __table_args__ = (
        CheckConstraint(
            "questions_total > 0",
            name="questions_total_positive",
        ),
        CheckConstraint(
            "questions_attempted > 0 AND questions_attempted <= questions_total",
            name="questions_attempted_valid",
        ),
        CheckConstraint(
            "correct_answers >= 0 AND correct_answers <= questions_attempted",
            name="correct_answers_valid",
        ),
        CheckConstraint(
            "quiz_accuracy >= 0 AND quiz_accuracy <= 1",
            name="quiz_accuracy_range",
        ),
        CheckConstraint(
            "quiz_mastery_score >= 0 AND quiz_mastery_score <= 1",
            name="quiz_mastery_score_range",
        ),
        CheckConstraint(
            "recommended_support_level IN ('low', 'medium', 'high')",
            name="recommended_support_level_valid",
        ),
        CheckConstraint(
            "quiz_avg_response_time_sec >= 0",
            name="quiz_response_time_non_negative",
        ),
        CheckConstraint(
            "quiz_hint_rate >= 0 AND quiz_hint_rate <= 1",
            name="quiz_hint_rate_range",
        ),
        CheckConstraint(
            "misconception_code IN ('none', 'inverse_operation', 'sign_error', "
            "'arithmetic_error', 'concept_confusion', 'other')",
            name="misconception_code_valid",
        ),
        CheckConstraint(
            "quiz_difficulty_level IN ('beginner', 'intermediate', 'advanced')",
            name="quiz_difficulty_level_valid",
        ),
        CheckConstraint(
            "quiz_attempt_count > 0",
            name="quiz_attempt_count_positive",
        ),
        Index("ix_quiz_results_student_concept", "student_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quiz_session_id: Mapped[str] = mapped_column(String(100), unique=True)
    student_id: Mapped[str] = mapped_column(String(100), index=True)
    concept_id: Mapped[str] = mapped_column(String(100), index=True)
    weak_concept: Mapped[str] = mapped_column(String(100))
    quiz_mastery_score: Mapped[float] = mapped_column(Float)
    recommended_support_level: Mapped[str] = mapped_column(String(20))
    questions_total: Mapped[int] = mapped_column(Integer)
    questions_attempted: Mapped[int] = mapped_column(Integer)
    correct_answers: Mapped[int] = mapped_column(Integer)
    quiz_accuracy: Mapped[float] = mapped_column(Float)
    quiz_avg_response_time_sec: Mapped[float] = mapped_column(Float)
    quiz_hint_rate: Mapped[float] = mapped_column(Float)
    misconception_code: Mapped[str] = mapped_column(String(50))
    quiz_difficulty_level: Mapped[str] = mapped_column(String(20))
    quiz_attempt_count: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
