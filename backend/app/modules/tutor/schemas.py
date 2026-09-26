import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DifficultyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MisconceptionCode(StrEnum):
    NONE = "none"
    INVERSE_OPERATION = "inverse_operation"
    SIGN_ERROR = "sign_error"
    ARITHMETIC_ERROR = "arithmetic_error"
    CONCEPT_CONFUSION = "concept_confusion"
    OTHER = "other"


class PreferredMode(StrEnum):
    VISUAL = "visual"
    TEXT = "text"
    MIXED = "mixed"


class TutoringStrategy(StrEnum):
    STEP_BY_STEP = "step_by_step"
    WORKED_EXAMPLE_BASED = "worked_example_based"
    CONCEPTUAL_EXPLANATION = "conceptual_explanation"
    PROGRESSIVE_HINTS = "progressive_hints"
    ADVANCED_CHALLENGE = "advanced_challenge"


class QuizResult(BaseModel):
    quiz_session_id: str = Field(min_length=1)
    questions_total: int = Field(gt=0)
    questions_attempted: int = Field(gt=0)
    correct_answers: int = Field(ge=0)
    quiz_accuracy: float = Field(ge=0, le=1)
    quiz_avg_response_time_sec: float = Field(ge=0)
    quiz_hint_rate: float = Field(ge=0, le=1)
    misconception_code: MisconceptionCode
    quiz_difficulty_level: DifficultyLevel
    quiz_attempt_count: int = Field(gt=0)
    completed_at: datetime

    @model_validator(mode="after")
    def validate_question_counts(self) -> "QuizResult":
        if self.questions_attempted > self.questions_total:
            raise ValueError("questions_attempted cannot exceed questions_total")
        if self.correct_answers > self.questions_attempted:
            raise ValueError("correct_answers cannot exceed questions_attempted")
        return self


class GameResult(BaseModel):
    game_session_id: str = Field(min_length=1)
    tasks_total: int = Field(gt=0)
    tasks_attempted: int = Field(gt=0)
    tasks_completed: int = Field(ge=0)
    successful_tasks: int = Field(ge=0)
    game_success_rate: float = Field(ge=0, le=1)
    game_completion_rate: float = Field(ge=0, le=1)
    game_avg_attempts_per_task: float = Field(ge=0)
    game_hint_rate: float = Field(ge=0, le=1)
    game_difficulty_level: DifficultyLevel
    game_active_time_sec: int = Field(ge=0)
    completed_at: datetime

    @model_validator(mode="after")
    def validate_task_counts(self) -> "GameResult":
        if self.tasks_attempted > self.tasks_total:
            raise ValueError("tasks_attempted cannot exceed tasks_total")
        if self.tasks_completed > self.tasks_attempted:
            raise ValueError("tasks_completed cannot exceed tasks_attempted")
        if self.successful_tasks > self.tasks_completed:
            raise ValueError("successful_tasks cannot exceed tasks_completed")
        return self


class LearnerProfile(BaseModel):
    prior_mastery_score: float = Field(ge=0, le=1)
    preferred_mode: PreferredMode
    sign_support_required: bool


class TutorStrategyRequest(BaseModel):
    student_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    quiz: QuizResult
    game: GameResult
    learner: LearnerProfile


class TutorStrategyResponse(BaseModel):
    prediction_id: uuid.UUID
    quiz_result_id: uuid.UUID
    game_result_id: uuid.UUID
    student_id: str
    concept_id: str
    recommended_strategy: TutoringStrategy
    confidence: float = Field(ge=0, le=1)
    preferred_mode: PreferredMode
    sign_support_required: bool
    model_version: str
