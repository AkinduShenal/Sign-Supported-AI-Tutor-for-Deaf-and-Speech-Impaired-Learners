"""Milestone 4 Batch 1: curriculum metadata and bilingual content only.

Stable concept IDs remain strings compatible with existing component contracts.
No existing Game, Quiz or Tutor table gains a curriculum foreign key here.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CurriculumTimestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # ORM updates advance this value. Raw SQL writers must set it explicitly.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CurriculumVersion(CurriculumTimestamps, Base):
    __tablename__ = "curriculum_versions"
    __table_args__ = (
        CheckConstraint("grade_level > 0", name="grade_level_positive"),
        CheckConstraint(
            "start_year IS NULL OR end_year IS NULL OR end_year >= start_year",
            name="year_range_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')", name="status_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_code: Mapped[str] = mapped_column(String(100), unique=True)
    version_name: Mapped[str] = mapped_column(String(255))
    grade_level: Mapped[int] = mapped_column(
        Integer, default=10, server_default=text("10")
    )
    subject_code: Mapped[str] = mapped_column(
        String(100), default="mathematics", server_default=text("'mathematics'")
    )
    description: Mapped[str | None] = mapped_column(Text)
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default=text("'draft'")
    )


class CurriculumUnit(CurriculumTimestamps, Base):
    __tablename__ = "curriculum_units"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_version_id",
            "unit_code",
            name="uq_curriculum_units_version_unit_code",
        ),
        # Referenced by the mapping's composite FK: a unit cannot be used
        # under a different curriculum version, even if both IDs exist.
        UniqueConstraint(
            "curriculum_version_id", "id", name="uq_curriculum_units_version_id"
        ),
        CheckConstraint("sequence_order >= 0", name="sequence_order_non_negative"),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')", name="status_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT")
    )
    unit_code: Mapped[str] = mapped_column(String(100))
    unit_name_en: Mapped[str | None] = mapped_column(String(255))
    unit_name_si: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    sequence_order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'")
    )


class MathConcept(CurriculumTimestamps, Base):
    __tablename__ = "math_concepts"
    __table_args__ = (
        CheckConstraint(
            "concept_type IN ('topic', 'subtopic', 'skill', 'prerequisite')",
            name="concept_type_valid",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')", name="status_valid"
        ),
    )

    concept_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(255))
    name_si: Mapped[str | None] = mapped_column(String(255))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_si: Mapped[str | None] = mapped_column(Text)
    concept_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'")
    )


class CurriculumConcept(CurriculumTimestamps, Base):
    __tablename__ = "curriculum_concepts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["curriculum_version_id", "unit_id"],
            ["curriculum_units.curriculum_version_id", "curriculum_units.id"],
            name="fk_curriculum_concepts_version_unit",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "curriculum_version_id",
            "unit_id",
            "concept_id",
            name="uq_curriculum_concepts_version_unit_concept",
        ),
        CheckConstraint("sequence_order >= 0", name="sequence_order_non_negative"),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')", name="status_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT")
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(index=True)
    concept_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("math_concepts.concept_id", ondelete="RESTRICT"),
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer)
    learning_objective: Mapped[str | None] = mapped_column(Text)
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'")
    )


class CurriculumDocument(CurriculumTimestamps, Base):
    __tablename__ = "curriculum_documents"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_version_id",
            "document_code",
            "language_code",
            name="uq_curriculum_documents_version_code_language",
        ),
        CheckConstraint("language_code IN ('si', 'en')", name="language_code_valid"),
        CheckConstraint(
            "document_type IN ('textbook', 'syllabus', 'teacher_guide', 'lesson_pdf', 'other')",
            name="document_type_valid",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')", name="status_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT")
    )
    document_code: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    language_code: Mapped[str] = mapped_column(String(2), index=True)
    document_type: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(255))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default=text("'active'")
    )


class ConceptContent(CurriculumTimestamps, Base):
    __tablename__ = "concept_content"
    __table_args__ = (
        CheckConstraint("language_code IN ('si', 'en')", name="language_code_valid"),
        CheckConstraint(
            "content_type IN ('definition', 'explanation', 'worked_example', 'formula', "
            "'misconception', 'hint', 'summary', 'learning_objective', 'other')",
            name="content_type_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'approved', 'archived')",
            name="status_valid",
        ),
        CheckConstraint(
            "source_page_start IS NULL OR source_page_start > 0",
            name="source_page_start_positive",
        ),
        CheckConstraint(
            "source_page_end IS NULL OR source_page_end > 0",
            name="source_page_end_positive",
        ),
        CheckConstraint(
            "source_page_start IS NULL OR source_page_end IS NULL "
            "OR source_page_end >= source_page_start",
            name="source_page_range_valid",
        ),
        CheckConstraint("content_version > 0", name="content_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    curriculum_concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_concepts.id", ondelete="RESTRICT"), index=True
    )
    language_code: Mapped[str] = mapped_column(String(2), index=True)
    content_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="SET NULL"), index=True
    )
    source_page_start: Mapped[int | None] = mapped_column(Integer)
    source_page_end: Mapped[int | None] = mapped_column(Integer)
    content_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1")
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default=text("'draft'"), index=True
    )
