"""Create quiz, game, and tutor strategy result tables.

Revision ID: 20260927_0001
Revises:
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260927_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quiz_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quiz_session_id", sa.String(length=100), nullable=False),
        sa.Column("student_id", sa.String(length=100), nullable=False),
        sa.Column("concept_id", sa.String(length=100), nullable=False),
        sa.Column("questions_total", sa.Integer(), nullable=False),
        sa.Column("questions_attempted", sa.Integer(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=False),
        sa.Column("quiz_accuracy", sa.Float(), nullable=False),
        sa.Column("quiz_avg_response_time_sec", sa.Float(), nullable=False),
        sa.Column("quiz_hint_rate", sa.Float(), nullable=False),
        sa.Column("misconception_code", sa.String(length=50), nullable=False),
        sa.Column("quiz_difficulty_level", sa.String(length=20), nullable=False),
        sa.Column("quiz_attempt_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "correct_answers >= 0 AND correct_answers <= questions_attempted",
            name=op.f("ck_quiz_results_correct_answers_valid"),
        ),
        sa.CheckConstraint(
            "misconception_code IN ('none', 'inverse_operation', 'sign_error', "
            "'arithmetic_error', 'concept_confusion', 'other')",
            name=op.f("ck_quiz_results_misconception_code_valid"),
        ),
        sa.CheckConstraint(
            "questions_attempted > 0 AND questions_attempted <= questions_total",
            name=op.f("ck_quiz_results_questions_attempted_valid"),
        ),
        sa.CheckConstraint(
            "questions_total > 0",
            name=op.f("ck_quiz_results_questions_total_positive"),
        ),
        sa.CheckConstraint(
            "quiz_accuracy >= 0 AND quiz_accuracy <= 1",
            name=op.f("ck_quiz_results_quiz_accuracy_range"),
        ),
        sa.CheckConstraint(
            "quiz_attempt_count > 0",
            name=op.f("ck_quiz_results_quiz_attempt_count_positive"),
        ),
        sa.CheckConstraint(
            "quiz_avg_response_time_sec >= 0",
            name=op.f("ck_quiz_results_quiz_response_time_non_negative"),
        ),
        sa.CheckConstraint(
            "quiz_difficulty_level IN ('beginner', 'intermediate', 'advanced')",
            name=op.f("ck_quiz_results_quiz_difficulty_level_valid"),
        ),
        sa.CheckConstraint(
            "quiz_hint_rate >= 0 AND quiz_hint_rate <= 1",
            name=op.f("ck_quiz_results_quiz_hint_rate_range"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_results")),
        sa.UniqueConstraint(
            "quiz_session_id",
            name=op.f("uq_quiz_results_quiz_session_id"),
        ),
    )
    op.create_index(
        "ix_quiz_results_concept_id",
        "quiz_results",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_quiz_results_student_concept",
        "quiz_results",
        ["student_id", "concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_quiz_results_student_id",
        "quiz_results",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "game_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("game_session_id", sa.String(length=100), nullable=False),
        sa.Column("student_id", sa.String(length=100), nullable=False),
        sa.Column("concept_id", sa.String(length=100), nullable=False),
        sa.Column("tasks_total", sa.Integer(), nullable=False),
        sa.Column("tasks_attempted", sa.Integer(), nullable=False),
        sa.Column("tasks_completed", sa.Integer(), nullable=False),
        sa.Column("successful_tasks", sa.Integer(), nullable=False),
        sa.Column("game_success_rate", sa.Float(), nullable=False),
        sa.Column("game_completion_rate", sa.Float(), nullable=False),
        sa.Column("game_avg_attempts_per_task", sa.Float(), nullable=False),
        sa.Column("game_hint_rate", sa.Float(), nullable=False),
        sa.Column("game_difficulty_level", sa.String(length=20), nullable=False),
        sa.Column("game_active_time_sec", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "game_active_time_sec >= 0",
            name=op.f("ck_game_results_game_active_time_non_negative"),
        ),
        sa.CheckConstraint(
            "game_avg_attempts_per_task >= 0",
            name=op.f("ck_game_results_game_avg_attempts_non_negative"),
        ),
        sa.CheckConstraint(
            "game_completion_rate >= 0 AND game_completion_rate <= 1",
            name=op.f("ck_game_results_game_completion_rate_range"),
        ),
        sa.CheckConstraint(
            "game_difficulty_level IN ('beginner', 'intermediate', 'advanced')",
            name=op.f("ck_game_results_game_difficulty_level_valid"),
        ),
        sa.CheckConstraint(
            "game_hint_rate >= 0 AND game_hint_rate <= 1",
            name=op.f("ck_game_results_game_hint_rate_range"),
        ),
        sa.CheckConstraint(
            "game_success_rate >= 0 AND game_success_rate <= 1",
            name=op.f("ck_game_results_game_success_rate_range"),
        ),
        sa.CheckConstraint(
            "successful_tasks >= 0 AND successful_tasks <= tasks_completed",
            name=op.f("ck_game_results_successful_tasks_valid"),
        ),
        sa.CheckConstraint(
            "tasks_attempted > 0 AND tasks_attempted <= tasks_total",
            name=op.f("ck_game_results_tasks_attempted_valid"),
        ),
        sa.CheckConstraint(
            "tasks_completed >= 0 AND tasks_completed <= tasks_attempted",
            name=op.f("ck_game_results_tasks_completed_valid"),
        ),
        sa.CheckConstraint(
            "tasks_total > 0",
            name=op.f("ck_game_results_tasks_total_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_results")),
        sa.UniqueConstraint(
            "game_session_id",
            name=op.f("uq_game_results_game_session_id"),
        ),
    )
    op.create_index(
        "ix_game_results_concept_id",
        "game_results",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_results_student_concept",
        "game_results",
        ["student_id", "concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_results_student_id",
        "game_results",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "tutor_strategy_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.String(length=100), nullable=False),
        sa.Column("concept_id", sa.String(length=100), nullable=False),
        sa.Column("quiz_result_id", sa.Uuid(), nullable=False),
        sa.Column("game_result_id", sa.Uuid(), nullable=False),
        sa.Column("recommended_strategy", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("preferred_mode", sa.String(length=20), nullable=False),
        sa.Column("sign_support_required", sa.Boolean(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_tutor_strategy_predictions_confidence_range"),
        ),
        sa.CheckConstraint(
            "preferred_mode IN ('visual', 'text', 'mixed')",
            name=op.f("ck_tutor_strategy_predictions_preferred_mode_valid"),
        ),
        sa.CheckConstraint(
            "recommended_strategy IN ('step_by_step', 'worked_example_based', "
            "'conceptual_explanation', 'progressive_hints', 'advanced_challenge')",
            name=op.f("ck_tutor_strategy_predictions_recommended_strategy_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["game_result_id"],
            ["game_results.id"],
            name=op.f("fk_tutor_strategy_predictions_game_result_id_game_results"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_result_id"],
            ["quiz_results.id"],
            name=op.f("fk_tutor_strategy_predictions_quiz_result_id_quiz_results"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tutor_strategy_predictions")),
    )
    op.create_index(
        "ix_tutor_predictions_student_concept",
        "tutor_strategy_predictions",
        ["student_id", "concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_tutor_strategy_predictions_concept_id",
        "tutor_strategy_predictions",
        ["concept_id"],
        unique=False,
    )
    op.create_index(
        "ix_tutor_strategy_predictions_game_result_id",
        "tutor_strategy_predictions",
        ["game_result_id"],
        unique=False,
    )
    op.create_index(
        "ix_tutor_strategy_predictions_quiz_result_id",
        "tutor_strategy_predictions",
        ["quiz_result_id"],
        unique=False,
    )
    op.create_index(
        "ix_tutor_strategy_predictions_student_id",
        "tutor_strategy_predictions",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tutor_strategy_predictions_student_id",
        table_name="tutor_strategy_predictions",
    )
    op.drop_index(
        "ix_tutor_strategy_predictions_quiz_result_id",
        table_name="tutor_strategy_predictions",
    )
    op.drop_index(
        "ix_tutor_strategy_predictions_game_result_id",
        table_name="tutor_strategy_predictions",
    )
    op.drop_index(
        "ix_tutor_strategy_predictions_concept_id",
        table_name="tutor_strategy_predictions",
    )
    op.drop_index(
        "ix_tutor_predictions_student_concept",
        table_name="tutor_strategy_predictions",
    )
    op.drop_table("tutor_strategy_predictions")

    op.drop_index("ix_game_results_student_id", table_name="game_results")
    op.drop_index("ix_game_results_student_concept", table_name="game_results")
    op.drop_index("ix_game_results_concept_id", table_name="game_results")
    op.drop_table("game_results")

    op.drop_index("ix_quiz_results_student_id", table_name="quiz_results")
    op.drop_index("ix_quiz_results_student_concept", table_name="quiz_results")
    op.drop_index("ix_quiz_results_concept_id", table_name="quiz_results")
    op.drop_table("quiz_results")
