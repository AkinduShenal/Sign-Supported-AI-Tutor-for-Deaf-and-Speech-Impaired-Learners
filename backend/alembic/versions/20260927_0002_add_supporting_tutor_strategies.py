"""Add supporting strategies to tutor predictions.

Revision ID: 20260927_0002
Revises: 20260927_0001
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260927_0002"
down_revision: str | None = "20260927_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tutor_strategy_predictions",
        sa.Column(
            "supporting_strategies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column(
        "tutor_strategy_predictions",
        "supporting_strategies",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "tutor_strategy_predictions",
        "supporting_strategies",
    )
