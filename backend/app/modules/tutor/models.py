import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TutorStrategyPrediction(Base):
    __tablename__ = "tutor_strategy_predictions"
    __table_args__ = (
        CheckConstraint(
            "recommended_strategy IN ('step_by_step', 'worked_example_based', "
            "'conceptual_explanation', 'progressive_hints', 'advanced_challenge')",
            name="recommended_strategy_valid",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        CheckConstraint(
            "preferred_mode IN ('visual', 'text', 'mixed')",
            name="preferred_mode_valid",
        ),
        Index(
            "ix_tutor_predictions_student_concept",
            "student_id",
            "concept_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[str] = mapped_column(String(100), index=True)
    concept_id: Mapped[str] = mapped_column(String(100), index=True)
    quiz_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quiz_results.id", ondelete="RESTRICT"),
        index=True,
    )
    game_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_results.id", ondelete="RESTRICT"),
        index=True,
    )
    recommended_strategy: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(100))
    preferred_mode: Mapped[str] = mapped_column(String(20))
    sign_support_required: Mapped[bool] = mapped_column(Boolean)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
