import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssessmentPhase(StrEnum):
    PRE_TUTOR = "pre_tutor"
    POST_TUTOR = "post_tutor"


class DisplayLanguage(StrEnum):
    EN = "en"
    SI = "si"
    BILINGUAL = "bilingual"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuizSessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QuizQuestionOptionResponse(BaseModel):
    id: uuid.UUID
    option_code: str
    option_text_en: str
    option_text_si: str


class QuizQuestionResponse(BaseModel):
    id: uuid.UUID
    question_code: str
    concept_id: str
    subconcept_code: str
    question_type: str
    question_text_en: str
    question_text_si: str
    difficulty_level: Literal["easy", "medium", "hard"]
    options: list[QuizQuestionOptionResponse]


class QuizSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=100)
    concept_id: Literal["linear_equations"] = "linear_equations"
    assessment_phase: AssessmentPhase = AssessmentPhase.PRE_TUTOR
    learning_cycle_id: uuid.UUID | None = None
    quiz_attempt_number: int = Field(default=1, gt=0)
    display_language: DisplayLanguage = DisplayLanguage.BILINGUAL


class QuizSessionResponse(BaseModel):
    quiz_session_id: str
    concept_id: str
    learning_cycle_id: uuid.UUID
    assessment_phase: AssessmentPhase
    quiz_attempt_number: int
    display_language: DisplayLanguage
    status: QuizSessionStatus
    started_at: datetime
    completed_at: datetime | None


class QuizSessionDetailResponse(QuizSessionResponse):
    responses_saved: int


class QuizAnswerSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: uuid.UUID
    selected_option_id: uuid.UUID
    response_time_sec: float = Field(ge=0, allow_inf_nan=False)
    confidence_level: ConfidenceLevel
    question_order: int = Field(gt=0)


class QuizAnswerSavedResponse(BaseModel):
    response_id: uuid.UUID
    quiz_session_id: str
    question_id: uuid.UUID
    question_order: int
    saved: Literal[True] = True
