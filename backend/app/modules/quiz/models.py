import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

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
        CheckConstraint(
            "assessment_phase IS NULL OR assessment_phase IN ('pre_tutor', 'post_tutor')",
            name=conv("quiz_results_assessment_phase_check"),
        ),
        CheckConstraint(
            "mastery_level IS NULL OR mastery_level IN ('low', 'medium', 'high')",
            name=conv("quiz_results_mastery_level_check"),
        ),
        CheckConstraint(
            "repeated_error_count IS NULL OR repeated_error_count >= 0",
            name=conv("quiz_results_repeated_error_count_check"),
        ),
        Index("ix_quiz_results_student_concept", "student_id", "concept_id"),
        Index("idx_quiz_results_learning_cycle", "learning_cycle_id"),
        Index("idx_quiz_results_phase", "assessment_phase"),
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
    learning_cycle_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    assessment_phase: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weak_subconcept: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mastery_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    repeated_error_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommended_focus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diagnostic_evidence: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )


class MisconceptionMapping(Base):
    __tablename__ = "misconception_mappings"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("misconception_mappings_pkey")),
        UniqueConstraint(
            "misconception_code",
            name=conv("misconception_mappings_misconception_code_key"),
        ),
        CheckConstraint(
            "minimum_occurrences > 0",
            name=conv("misconception_mappings_minimum_occurrences_check"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[str] = mapped_column(String(100))
    subconcept_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    misconception_code: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(255))
    name_si: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimum_occurrences: Mapped[int] = mapped_column(Integer, default=2)
    teacher_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("quiz_questions_pkey")),
        UniqueConstraint(
            "question_code", name=conv("quiz_questions_question_code_key")
        ),
        CheckConstraint(
            "assessment_use IN ('pre', 'post', 'both')",
            name=conv("quiz_questions_assessment_use_check"),
        ),
        CheckConstraint(
            "difficulty_level IN ('easy', 'medium', 'hard')",
            name=conv("quiz_questions_difficulty_level_check"),
        ),
        CheckConstraint(
            "question_type IN ('multiple_choice', 'numeric', 'text')",
            name=conv("quiz_questions_question_type_check"),
        ),
        Index("idx_quiz_questions_assessment_use", "assessment_use"),
        Index("idx_quiz_questions_concept", "concept_id"),
        Index("idx_quiz_questions_difficulty", "difficulty_level"),
        Index("idx_quiz_questions_equivalence", "equivalence_group"),
        Index("idx_quiz_questions_subconcept", "subconcept_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_code: Mapped[str] = mapped_column(String(50))
    concept_id: Mapped[str] = mapped_column(String(100), default="linear_equations")
    subconcept_code: Mapped[str] = mapped_column(String(100))
    question_type: Mapped[str] = mapped_column(String(30), default="multiple_choice")
    question_text_en: Mapped[str] = mapped_column(Text)
    question_text_si: Mapped[str] = mapped_column(Text)
    difficulty_level: Mapped[str] = mapped_column(String(20))
    assessment_use: Mapped[str] = mapped_column(String(20), default="both")
    equivalence_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correct_answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_ref_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_ref_si: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuizQuestionOption(Base):
    __tablename__ = "quiz_question_options"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("quiz_question_options_pkey")),
        UniqueConstraint(
            "question_id",
            "option_code",
            name=conv("quiz_question_options_question_id_option_code_key"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "quiz_questions.id",
            ondelete="CASCADE",
            name=conv("quiz_question_options_question_id_fkey"),
        ),
    )
    option_code: Mapped[str] = mapped_column(String(10))
    option_text_en: Mapped[str] = mapped_column(Text)
    option_text_si: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    misconception_code: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey(
            "misconception_mappings.misconception_code",
            ondelete="SET NULL",
            name=conv("quiz_question_options_misconception_code_fkey"),
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("quiz_sessions_pkey")),
        UniqueConstraint(
            "quiz_session_id", name=conv("quiz_sessions_quiz_session_id_key")
        ),
        CheckConstraint(
            "assessment_phase IN ('pre_tutor', 'post_tutor')",
            name=conv("quiz_sessions_assessment_phase_check"),
        ),
        CheckConstraint(
            "display_language IN ('en', 'si', 'bilingual')",
            name=conv("quiz_sessions_display_language_check"),
        ),
        CheckConstraint(
            "quiz_attempt_number > 0",
            name=conv("quiz_sessions_quiz_attempt_number_check"),
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name=conv("quiz_sessions_status_check"),
        ),
        Index("idx_quiz_sessions_learning_cycle", "learning_cycle_id"),
        Index("idx_quiz_sessions_phase", "assessment_phase"),
        Index("idx_quiz_sessions_student", "student_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quiz_session_id: Mapped[str] = mapped_column(String(100))
    student_id: Mapped[str] = mapped_column(String(100))
    concept_id: Mapped[str] = mapped_column(String(100), default="linear_equations")
    learning_cycle_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    assessment_phase: Mapped[str] = mapped_column(String(20))
    quiz_attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    display_language: Mapped[str] = mapped_column(String(20), default="bilingual")
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuizResponse(Base):
    __tablename__ = "quiz_responses"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("quiz_responses_pkey")),
        UniqueConstraint(
            "quiz_session_id",
            "question_id",
            name=conv("quiz_responses_quiz_session_id_question_id_key"),
        ),
        CheckConstraint(
            "confidence_level IN ('low', 'medium', 'high')",
            name=conv("quiz_responses_confidence_level_check"),
        ),
        CheckConstraint(
            "question_order > 0",
            name=conv("quiz_responses_question_order_check"),
        ),
        CheckConstraint(
            "response_time_sec >= 0",
            name=conv("quiz_responses_response_time_sec_check"),
        ),
        Index("idx_quiz_responses_misconception", "misconception_code"),
        Index("idx_quiz_responses_question", "question_id"),
        Index("idx_quiz_responses_session", "quiz_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quiz_session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey(
            "quiz_sessions.quiz_session_id",
            ondelete="CASCADE",
            name=conv("quiz_responses_quiz_session_id_fkey"),
        ),
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "quiz_questions.id",
            ondelete="RESTRICT",
            name=conv("quiz_responses_question_id_fkey"),
        ),
    )
    selected_option_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "quiz_question_options.id",
            ondelete="SET NULL",
            name=conv("quiz_responses_selected_option_id_fkey"),
        ),
        nullable=True,
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    response_time_sec: Mapped[float] = mapped_column(Float)
    confidence_level: Mapped[str] = mapped_column(String(20))
    misconception_code: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey(
            "misconception_mappings.misconception_code",
            ondelete="SET NULL",
            name=conv("quiz_responses_misconception_code_fkey"),
        ),
        nullable=True,
    )
    question_order: Mapped[int] = mapped_column(Integer)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuizComparison(Base):
    __tablename__ = "quiz_comparisons"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("quiz_comparisons_pkey")),
        UniqueConstraint(
            "learning_cycle_id",
            "concept_id",
            name=conv("quiz_comparisons_learning_cycle_id_concept_id_key"),
        ),
        CheckConstraint(
            "improvement_status IN ('improved', 'not_improved')",
            name=conv("quiz_comparisons_improvement_status_check"),
        ),
        CheckConstraint(
            "pre_accuracy >= 0 AND pre_accuracy <= 1",
            name=conv("quiz_comparisons_pre_accuracy_check"),
        ),
        CheckConstraint(
            "post_accuracy >= 0 AND post_accuracy <= 1",
            name=conv("quiz_comparisons_post_accuracy_check"),
        ),
        CheckConstraint(
            "pre_mastery_score IS NULL OR (pre_mastery_score >= 0 AND pre_mastery_score <= 1)",
            name=conv("quiz_comparisons_pre_mastery_score_check"),
        ),
        CheckConstraint(
            "post_mastery_score IS NULL OR (post_mastery_score >= 0 AND post_mastery_score <= 1)",
            name=conv("quiz_comparisons_post_mastery_score_check"),
        ),
        CheckConstraint(
            "pre_mastery_level IS NULL OR pre_mastery_level IN ('low', 'medium', 'high')",
            name=conv("quiz_comparisons_pre_mastery_level_check"),
        ),
        CheckConstraint(
            "post_mastery_level IS NULL OR post_mastery_level IN ('low', 'medium', 'high')",
            name=conv("quiz_comparisons_post_mastery_level_check"),
        ),
        Index("idx_quiz_comparisons_learning_cycle", "learning_cycle_id"),
        Index("idx_quiz_comparisons_student", "student_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[str] = mapped_column(String(100))
    learning_cycle_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    concept_id: Mapped[str] = mapped_column(String(100), default="linear_equations")
    pre_quiz_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "quiz_results.id",
            ondelete="CASCADE",
            name=conv("quiz_comparisons_pre_quiz_result_id_fkey"),
        ),
    )
    post_quiz_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "quiz_results.id",
            ondelete="CASCADE",
            name=conv("quiz_comparisons_post_quiz_result_id_fkey"),
        ),
    )
    pre_accuracy: Mapped[float] = mapped_column(Float)
    post_accuracy: Mapped[float] = mapped_column(Float)
    accuracy_change: Mapped[float] = mapped_column(Float)
    pre_mastery_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_mastery_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mastery_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_mastery_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    post_mastery_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pre_misconception_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    post_misconception_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    misconception_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    improvement_status: Mapped[str] = mapped_column(String(30))
    unresolved_misconception_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
