"""Game-owned reusable content; separate from learner evidence and API models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.curriculum import models as curriculum_models  # noqa: F401


class ContentTimestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # As with curriculum content, raw SQL writers must set updated_at themselves.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GameActivity(ContentTimestamps, Base):
    __tablename__ = "game_activity_bank"
    __table_args__ = (
        CheckConstraint(
            "difficulty_level IN ('easy', 'medium', 'hard')",
            name="difficulty_level_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'approved', 'archived')",
            name="status_valid",
        ),
        CheckConstraint("activity_version > 0", name="activity_version_positive"),
    )

    activity_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    curriculum_concept_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("curriculum_concepts.id", ondelete="RESTRICT"), index=True
    )
    difficulty_level: Mapped[str] = mapped_column(String(20), index=True)
    activity_type: Mapped[str] = mapped_column(String(50))
    title_en: Mapped[str] = mapped_column(String(255))
    title_si: Mapped[str | None] = mapped_column(String(255))
    instruction_en: Mapped[str] = mapped_column(Text)
    instruction_si: Mapped[str | None] = mapped_column(Text)
    activity_config: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        default=dict,
        server_default=text("'{}'"),
    )
    activity_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1")
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default=text("'draft'"), index=True
    )


class GameActivityVariant(ContentTimestamps, Base):
    __tablename__ = "game_activity_variants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'reviewed', 'approved', 'archived')",
            name="status_valid",
        ),
        CheckConstraint("variant_version > 0", name="variant_version_positive"),
        CheckConstraint(
            "source_page_start IS NULL OR source_page_start > 0",
            name="source_page_start_positive",
        ),
        CheckConstraint(
            "source_page_end IS NULL OR source_page_end > 0",
            name="source_page_end_positive",
        ),
        CheckConstraint(
            "source_page_start IS NULL OR source_page_end IS NULL OR source_page_end >= source_page_start",
            name="source_page_range_valid",
        ),
    )

    variant_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    activity_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("game_activity_bank.activity_id", ondelete="RESTRICT"),
        index=True,
    )
    variant_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1")
    )
    prompt_en: Mapped[str] = mapped_column(Text)
    prompt_si: Mapped[str | None] = mapped_column(Text)
    question_config: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )
    answer_key: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="SET NULL"), index=True
    )
    source_page_start: Mapped[int | None] = mapped_column(Integer)
    source_page_end: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default=text("'draft'"), index=True
    )
