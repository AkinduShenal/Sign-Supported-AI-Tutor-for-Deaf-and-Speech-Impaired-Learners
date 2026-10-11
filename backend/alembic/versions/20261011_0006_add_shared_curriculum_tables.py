"""Create the six shared curriculum tables, without seed data.

Revision ID: 20261011_0006
Revises: 20261009_0005

Only new curriculum objects are created. Existing component tables and
concept_id contracts are intentionally untouched. Apply with upgrade, not stamp,
after checking the live revision and confirming these tables do not exist.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261011_0006"
down_revision = "20261009_0005"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "curriculum_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_code", sa.String(100), nullable=False),
        sa.Column("version_name", sa.String(255), nullable=False),
        sa.Column(
            "grade_level", sa.Integer(), nullable=False, server_default=sa.text("10")
        ),
        sa.Column(
            "subject_code",
            sa.String(100),
            nullable=False,
            server_default=sa.text("'mathematics'"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'draft'")
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_versions")),
        sa.UniqueConstraint(
            "version_code", name=op.f("uq_curriculum_versions_version_code")
        ),
        sa.CheckConstraint(
            "grade_level > 0", name=op.f("ck_curriculum_versions_grade_level_positive")
        ),
        sa.CheckConstraint(
            "start_year IS NULL OR end_year IS NULL OR end_year >= start_year",
            name=op.f("ck_curriculum_versions_year_range_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name=op.f("ck_curriculum_versions_status_valid"),
        ),
    )
    op.create_table(
        "curriculum_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.String(100), nullable=False),
        sa.Column("unit_name_en", sa.String(255), nullable=True),
        sa.Column("unit_name_si", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'active'")
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_units")),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            name=op.f("fk_curriculum_units_curriculum_version_id_curriculum_versions"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "curriculum_version_id",
            "unit_code",
            name="uq_curriculum_units_version_unit_code",
        ),
        sa.UniqueConstraint(
            "curriculum_version_id", "id", name="uq_curriculum_units_version_id"
        ),
        sa.CheckConstraint(
            "sequence_order >= 0",
            name=op.f("ck_curriculum_units_sequence_order_non_negative"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name=op.f("ck_curriculum_units_status_valid"),
        ),
    )
    op.create_table(
        "math_concepts",
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(255), nullable=False),
        sa.Column("name_si", sa.String(255), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_si", sa.Text(), nullable=True),
        sa.Column("concept_type", sa.String(20), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'active'")
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("concept_id", name=op.f("pk_math_concepts")),
        sa.CheckConstraint(
            "concept_type IN ('topic', 'subtopic', 'skill', 'prerequisite')",
            name=op.f("ck_math_concepts_concept_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name=op.f("ck_math_concepts_status_valid"),
        ),
    )
    op.create_table(
        "curriculum_concepts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.String(100), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("learning_objective", sa.Text(), nullable=True),
        sa.Column(
            "is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'active'")
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_concepts")),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            name=op.f(
                "fk_curriculum_concepts_curriculum_version_id_curriculum_versions"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id", "unit_id"],
            ["curriculum_units.curriculum_version_id", "curriculum_units.id"],
            name="fk_curriculum_concepts_version_unit",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["math_concepts.concept_id"],
            name=op.f("fk_curriculum_concepts_concept_id_math_concepts"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "curriculum_version_id",
            "unit_id",
            "concept_id",
            name="uq_curriculum_concepts_version_unit_concept",
        ),
        sa.CheckConstraint(
            "sequence_order >= 0",
            name=op.f("ck_curriculum_concepts_sequence_order_non_negative"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name=op.f("ck_curriculum_concepts_status_valid"),
        ),
    )
    op.create_index(
        "ix_curriculum_concepts_unit_id", "curriculum_concepts", ["unit_id"]
    )
    op.create_index(
        "ix_curriculum_concepts_concept_id", "curriculum_concepts", ["concept_id"]
    )
    op.create_table(
        "curriculum_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("document_code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("language_code", sa.String(2), nullable=False),
        sa.Column("document_type", sa.String(20), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'active'")
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_curriculum_documents")),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["curriculum_versions.id"],
            name=op.f(
                "fk_curriculum_documents_curriculum_version_id_curriculum_versions"
            ),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "curriculum_version_id",
            "document_code",
            "language_code",
            name="uq_curriculum_documents_version_code_language",
        ),
        sa.CheckConstraint(
            "language_code IN ('si', 'en')",
            name=op.f("ck_curriculum_documents_language_code_valid"),
        ),
        sa.CheckConstraint(
            "document_type IN ('textbook', 'syllabus', 'teacher_guide', 'lesson_pdf', 'other')",
            name=op.f("ck_curriculum_documents_document_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name=op.f("ck_curriculum_documents_status_valid"),
        ),
    )
    op.create_index(
        "ix_curriculum_documents_language_code",
        "curriculum_documents",
        ["language_code"],
    )
    op.create_table(
        "concept_content",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("curriculum_concept_id", sa.Uuid(), nullable=False),
        sa.Column("language_code", sa.String(2), nullable=False),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("source_page_start", sa.Integer(), nullable=True),
        sa.Column("source_page_end", sa.Integer(), nullable=True),
        sa.Column(
            "content_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'draft'")
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_concept_content")),
        sa.ForeignKeyConstraint(
            ["curriculum_concept_id"],
            ["curriculum_concepts.id"],
            name=op.f("fk_concept_content_curriculum_concept_id_curriculum_concepts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["curriculum_documents.id"],
            name=op.f("fk_concept_content_source_document_id_curriculum_documents"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "language_code IN ('si', 'en')",
            name=op.f("ck_concept_content_language_code_valid"),
        ),
        sa.CheckConstraint(
            "content_type IN ('definition', 'explanation', 'worked_example', 'formula', "
            "'misconception', 'hint', 'summary', 'learning_objective', 'other')",
            name=op.f("ck_concept_content_content_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'reviewed', 'approved', 'archived')",
            name=op.f("ck_concept_content_status_valid"),
        ),
        sa.CheckConstraint(
            "source_page_start IS NULL OR source_page_start > 0",
            name=op.f("ck_concept_content_source_page_start_positive"),
        ),
        sa.CheckConstraint(
            "source_page_end IS NULL OR source_page_end > 0",
            name=op.f("ck_concept_content_source_page_end_positive"),
        ),
        sa.CheckConstraint(
            "source_page_start IS NULL OR source_page_end IS NULL OR source_page_end >= source_page_start",
            name=op.f("ck_concept_content_source_page_range_valid"),
        ),
        sa.CheckConstraint(
            "content_version > 0",
            name=op.f("ck_concept_content_content_version_positive"),
        ),
    )
    op.create_index(
        "ix_concept_content_curriculum_concept_id",
        "concept_content",
        ["curriculum_concept_id"],
    )
    op.create_index(
        "ix_concept_content_language_code", "concept_content", ["language_code"]
    )
    op.create_index(
        "ix_concept_content_content_type", "concept_content", ["content_type"]
    )
    op.create_index("ix_concept_content_status", "concept_content", ["status"])
    op.create_index(
        "ix_concept_content_source_document_id",
        "concept_content",
        ["source_document_id"],
    )


def downgrade() -> None:
    # Reverse dependencies; never remove an existing component's tables.
    op.drop_table("concept_content")
    op.drop_table("curriculum_documents")
    op.drop_table("curriculum_concepts")
    op.drop_table("math_concepts")
    op.drop_table("curriculum_units")
    op.drop_table("curriculum_versions")
