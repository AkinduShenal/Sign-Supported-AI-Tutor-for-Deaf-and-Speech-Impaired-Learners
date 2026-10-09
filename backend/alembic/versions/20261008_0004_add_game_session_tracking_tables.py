"""Add game session tracking tables

Records, for Alembic's own bookkeeping, the Game tables that already exist
live on the shared Supabase database (built directly there, outside this
repo's migration history, before this repo described them in SQLAlchemy):

    game_sessions
    gameplay_events
    game_task_attempts

and the Milestone 3 additive columns on the pre-existing ``game_results``
table. Applied with ``alembic stamp`` (bookmark-only), never ``upgrade`` —
every object below already exists; this file exists so `alembic history`
and the next migration have something real to chain onto.

Revision ID: 20261008_0004
Revises: 20260930_0003
Create Date: 2026-10-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261008_0004"
down_revision = "20260930_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("game_session_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("student_id", sa.String(length=100), nullable=False),
        sa.Column("concept_id", sa.String(length=100), nullable=False),
        sa.Column("learning_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_phase", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "assessment_phase IN ('pre_tutor', 'post_tutor')", name="assessment_phase_valid"
        ),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')", name="status_valid"
        ),
    )
    op.create_index(
        "ix_game_sessions_student_concept", "game_sessions", ["student_id", "concept_id"]
    )

    op.create_table(
        "gameplay_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "game_session_id",
            sa.String(length=100),
            sa.ForeignKey("game_sessions.game_session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "event_payload",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ("
            "'GAME_STARTED', 'GAME_COMPLETED', 'SESSION_ENDED', "
            "'TASK_STARTED', 'TASK_COMPLETED', 'QUESTION_SHOWN', "
            "'ANSWER_SUBMITTED', 'ANSWER_CORRECT', 'ANSWER_INCORRECT', "
            "'HINT_REQUESTED', 'RETRY_STARTED', 'STEP_SKIPPED')",
            name="event_type_valid",
        ),
    )
    op.create_index(
        "ix_gameplay_events_session_task", "gameplay_events", ["game_session_id", "task_id"]
    )

    op.create_table(
        "game_task_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "game_session_id",
            sa.String(length=100),
            sa.ForeignKey("game_sessions.game_session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", sa.String(length=100), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("wrong_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("time_taken_sec", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_successful", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
        sa.CheckConstraint("attempts_count >= 0", name="attempts_count_non_negative"),
        sa.CheckConstraint("wrong_attempts >= 0", name="wrong_attempts_non_negative"),
        sa.CheckConstraint("hints_used >= 0", name="hints_used_non_negative"),
        sa.CheckConstraint("skipped_steps >= 0", name="skipped_steps_non_negative"),
        sa.CheckConstraint("time_taken_sec >= 0", name="time_taken_sec_non_negative"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)", name="score_range"
        ),
    )
    op.create_index(
        "ix_game_task_attempts_session", "game_task_attempts", ["game_session_id"]
    )

    op.create_foreign_key(
        "game_results_game_session_id_fkey",
        "game_results",
        "game_sessions",
        ["game_session_id"],
        ["game_session_id"],
    )
    op.add_column(
        "game_results", sa.Column("learning_cycle_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "game_results", sa.Column("assessment_phase", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "game_results",
        sa.Column("wrong_attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_results",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_results",
        sa.Column("total_hint_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_results",
        sa.Column("skipped_step_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_results", sa.Column("game_mastery_level", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "game_results", sa.Column("game_engagement_level", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "game_results", sa.Column("hint_dependency_level", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "game_results", sa.Column("model_version", sa.String(length=100), nullable=True)
    )
    op.create_check_constraint(
        "assessment_phase_valid",
        "game_results",
        "assessment_phase IS NULL OR assessment_phase IN ('pre_tutor', 'post_tutor')",
    )
    op.create_check_constraint(
        "game_mastery_level_valid",
        "game_results",
        "game_mastery_level IS NULL OR game_mastery_level IN ('low', 'medium', 'high')",
    )
    op.create_check_constraint(
        "game_engagement_level_valid",
        "game_results",
        "game_engagement_level IS NULL OR game_engagement_level IN ('low', 'medium', 'high')",
    )
    op.create_check_constraint(
        "hint_dependency_level_valid",
        "game_results",
        "hint_dependency_level IS NULL OR hint_dependency_level IN ('low', 'medium', 'high')",
    )


def downgrade() -> None:
    op.drop_constraint("hint_dependency_level_valid", "game_results", type_="check")
    op.drop_constraint("game_engagement_level_valid", "game_results", type_="check")
    op.drop_constraint("game_mastery_level_valid", "game_results", type_="check")
    op.drop_constraint("assessment_phase_valid", "game_results", type_="check")
    op.drop_column("game_results", "model_version")
    op.drop_column("game_results", "hint_dependency_level")
    op.drop_column("game_results", "game_engagement_level")
    op.drop_column("game_results", "game_mastery_level")
    op.drop_column("game_results", "skipped_step_count")
    op.drop_column("game_results", "total_hint_count")
    op.drop_column("game_results", "retry_count")
    op.drop_column("game_results", "wrong_attempt_count")
    op.drop_column("game_results", "assessment_phase")
    op.drop_column("game_results", "learning_cycle_id")
    op.drop_constraint("game_results_game_session_id_fkey", "game_results", type_="foreignkey")

    op.drop_index("ix_game_task_attempts_session", table_name="game_task_attempts")
    op.drop_table("game_task_attempts")

    op.drop_index("ix_gameplay_events_session_task", table_name="gameplay_events")
    op.drop_table("gameplay_events")

    op.drop_index("ix_game_sessions_student_concept", table_name="game_sessions")
    op.drop_table("game_sessions")
