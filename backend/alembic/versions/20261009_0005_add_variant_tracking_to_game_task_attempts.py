"""Add variant tracking columns to game_task_attempts

Milestone 3 Steps 11-13 need to know which of the 18 Easy/Medium/Hard
variants a task attempt was, so the "maximum two uses" selection rule can
query prior usage per student/concept/variant. These columns are new,
nullable and additive: existing rows (and any other component's code)
are unaffected.

Revision ID: 20261009_0005
Revises: 20261008_0004
Create Date: 2026-10-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261009_0005"
down_revision = "20261008_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "game_task_attempts", sa.Column("activity_id", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "game_task_attempts", sa.Column("variant_id", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "game_task_attempts",
        sa.Column("difficulty_level", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "difficulty_level_valid",
        "game_task_attempts",
        "difficulty_level IS NULL OR difficulty_level IN ('easy', 'medium', 'hard')",
    )
    op.create_index(
        "ix_game_task_attempts_variant", "game_task_attempts", ["variant_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_game_task_attempts_variant", table_name="game_task_attempts")
    op.drop_constraint("difficulty_level_valid", "game_task_attempts", type_="check")
    op.drop_column("game_task_attempts", "difficulty_level")
    op.drop_column("game_task_attempts", "variant_id")
    op.drop_column("game_task_attempts", "activity_id")
