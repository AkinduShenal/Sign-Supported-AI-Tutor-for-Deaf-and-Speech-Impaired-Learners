"""Add Game-owned activity and variant content without altering learner history.

Revision ID: 20261011_0007
Revises: 20261011_0006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261011_0007"
down_revision = "20261011_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_activity_bank",
        sa.Column("activity_id", sa.String(100), nullable=False),
        sa.Column("curriculum_concept_id", sa.Uuid(), nullable=False),
        sa.Column("difficulty_level", sa.String(20), nullable=False),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("title_en", sa.String(255), nullable=False),
        sa.Column("title_si", sa.String(255), nullable=True),
        sa.Column("instruction_en", sa.Text(), nullable=False),
        sa.Column("instruction_si", sa.Text(), nullable=True),
        sa.Column(
            "activity_config",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "activity_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(20), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("activity_id", name=op.f("pk_game_activity_bank")),
        sa.ForeignKeyConstraint(
            ["curriculum_concept_id"],
            ["curriculum_concepts.id"],
            ondelete="RESTRICT",
            name=op.f(
                "fk_game_activity_bank_curriculum_concept_id_curriculum_concepts"
            ),
        ),
        sa.CheckConstraint(
            "difficulty_level IN ('easy', 'medium', 'hard')",
            name=op.f("ck_game_activity_bank_difficulty_level_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'reviewed', 'approved', 'archived')",
            name=op.f("ck_game_activity_bank_status_valid"),
        ),
        sa.CheckConstraint(
            "activity_version > 0",
            name=op.f("ck_game_activity_bank_activity_version_positive"),
        ),
    )
    for column in ("curriculum_concept_id", "difficulty_level", "status"):
        op.create_index(
            f"ix_game_activity_bank_{column}", "game_activity_bank", [column]
        )
    op.create_table(
        "game_activity_variants",
        sa.Column("variant_id", sa.String(100), nullable=False),
        sa.Column("activity_id", sa.String(100), nullable=False),
        sa.Column(
            "variant_version", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("prompt_en", sa.Text(), nullable=False),
        sa.Column("prompt_si", sa.Text(), nullable=True),
        sa.Column(
            "question_config",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "answer_key",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("source_page_start", sa.Integer(), nullable=True),
        sa.Column("source_page_end", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(20), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("variant_id", name=op.f("pk_game_activity_variants")),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["game_activity_bank.activity_id"],
            ondelete="RESTRICT",
            name=op.f("fk_game_activity_variants_activity_id_game_activity_bank"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["curriculum_documents.id"],
            ondelete="SET NULL",
            name=op.f(
                "fk_game_activity_variants_source_document_id_curriculum_documents"
            ),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'reviewed', 'approved', 'archived')",
            name=op.f("ck_game_activity_variants_status_valid"),
        ),
        sa.CheckConstraint(
            "variant_version > 0",
            name=op.f("ck_game_activity_variants_variant_version_positive"),
        ),
        sa.CheckConstraint(
            "source_page_start IS NULL OR source_page_start > 0",
            name=op.f("ck_game_activity_variants_source_page_start_positive"),
        ),
        sa.CheckConstraint(
            "source_page_end IS NULL OR source_page_end > 0",
            name=op.f("ck_game_activity_variants_source_page_end_positive"),
        ),
        sa.CheckConstraint(
            "source_page_start IS NULL OR source_page_end IS NULL OR source_page_end >= source_page_start",
            name=op.f("ck_game_activity_variants_source_page_range_valid"),
        ),
    )
    for column in ("activity_id", "source_document_id", "status"):
        op.create_index(
            f"ix_game_activity_variants_{column}", "game_activity_variants", [column]
        )


def downgrade() -> None:
    # Local rollback only: removing these tables destroys bank content.
    op.drop_table("game_activity_variants")
    op.drop_table("game_activity_bank")
