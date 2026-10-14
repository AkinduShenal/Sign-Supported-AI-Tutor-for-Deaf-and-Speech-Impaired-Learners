"""Add quiz and game diagnostic model outputs.

Revision ID: 20260930_0003
Revises: 20260927_0002
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260930_0003"
down_revision: str | None = "20260927_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quiz_results",
        sa.Column("weak_concept", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "quiz_results",
        sa.Column("quiz_mastery_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "quiz_results",
        sa.Column(
            "recommended_support_level",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE quiz_results
            SET weak_concept = concept_id,
                quiz_mastery_score = quiz_accuracy,
                recommended_support_level = CASE
                    WHEN quiz_accuracy < 0.5 THEN 'high'
                    WHEN quiz_accuracy < 0.8 THEN 'medium'
                    ELSE 'low'
                END
            """
        )
    )
    op.alter_column("quiz_results", "weak_concept", nullable=False)
    op.alter_column("quiz_results", "quiz_mastery_score", nullable=False)
    op.alter_column(
        "quiz_results",
        "recommended_support_level",
        nullable=False,
    )
    op.create_check_constraint(
        op.f("ck_quiz_results_quiz_mastery_score_range"),
        "quiz_results",
        "quiz_mastery_score >= 0 AND quiz_mastery_score <= 1",
    )
    op.create_check_constraint(
        op.f("ck_quiz_results_recommended_support_level_valid"),
        "quiz_results",
        "recommended_support_level IN ('low', 'medium', 'high')",
    )

    op.add_column(
        "game_results",
        sa.Column("engagement_level", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "game_results",
        sa.Column("behavioral_difficulty", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "game_results",
        sa.Column("hint_dependency", sa.Float(), nullable=True),
    )
    op.add_column(
        "game_results",
        sa.Column("game_mastery_score", sa.Float(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE game_results
            SET engagement_level = 'medium',
                behavioral_difficulty = CASE
                    WHEN game_success_rate < 0.5 THEN 'high'
                    WHEN game_success_rate < 0.8 THEN 'medium'
                    ELSE 'low'
                END,
                hint_dependency = game_hint_rate,
                game_mastery_score =
                    (game_success_rate + game_completion_rate) / 2.0
            """
        )
    )
    op.alter_column("game_results", "engagement_level", nullable=False)
    op.alter_column("game_results", "behavioral_difficulty", nullable=False)
    op.alter_column("game_results", "hint_dependency", nullable=False)
    op.alter_column("game_results", "game_mastery_score", nullable=False)
    op.create_check_constraint(
        op.f("ck_game_results_engagement_level_valid"),
        "game_results",
        "engagement_level IN ('low', 'medium', 'high')",
    )
    op.create_check_constraint(
        op.f("ck_game_results_behavioral_difficulty_valid"),
        "game_results",
        "behavioral_difficulty IN ('low', 'medium', 'high')",
    )
    op.create_check_constraint(
        op.f("ck_game_results_hint_dependency_range"),
        "game_results",
        "hint_dependency >= 0 AND hint_dependency <= 1",
    )
    op.create_check_constraint(
        op.f("ck_game_results_game_mastery_score_range"),
        "game_results",
        "game_mastery_score >= 0 AND game_mastery_score <= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_game_results_game_mastery_score_range"),
        "game_results",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_game_results_hint_dependency_range"),
        "game_results",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_game_results_behavioral_difficulty_valid"),
        "game_results",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_game_results_engagement_level_valid"),
        "game_results",
        type_="check",
    )
    op.drop_column("game_results", "game_mastery_score")
    op.drop_column("game_results", "hint_dependency")
    op.drop_column("game_results", "behavioral_difficulty")
    op.drop_column("game_results", "engagement_level")

    op.drop_constraint(
        op.f("ck_quiz_results_recommended_support_level_valid"),
        "quiz_results",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_quiz_results_quiz_mastery_score_range"),
        "quiz_results",
        type_="check",
    )
    op.drop_column("quiz_results", "recommended_support_level")
    op.drop_column("quiz_results", "quiz_mastery_score")
    op.drop_column("quiz_results", "weak_concept")
