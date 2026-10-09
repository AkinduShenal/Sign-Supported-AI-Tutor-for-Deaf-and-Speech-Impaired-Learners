"""Pydantic request/response models for the Game API.

The game result handed to the AI Tutor is defined separately, by the
Tutor's contract: ``GameResult`` in ``app/modules/tutor/schemas.py``.
These schemas are for this module's own ``/api/v1/game`` routes.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AssessmentPhase(StrEnum):
    PRE_TUTOR = "pre_tutor"
    POST_TUTOR = "post_tutor"


class GameSessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DifficultyLevel(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GameplayEventType(StrEnum):
    GAME_STARTED = "GAME_STARTED"
    GAME_COMPLETED = "GAME_COMPLETED"
    SESSION_ENDED = "SESSION_ENDED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    QUESTION_SHOWN = "QUESTION_SHOWN"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"
    ANSWER_CORRECT = "ANSWER_CORRECT"
    ANSWER_INCORRECT = "ANSWER_INCORRECT"
    HINT_REQUESTED = "HINT_REQUESTED"
    RETRY_STARTED = "RETRY_STARTED"
    STEP_SKIPPED = "STEP_SKIPPED"


class CreateGameSessionRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=100)
    concept_id: str = Field(min_length=1, max_length=100)
    learning_cycle_id: uuid.UUID
    assessment_phase: AssessmentPhase = AssessmentPhase.PRE_TUTOR


class GameSessionResponse(BaseModel):
    game_session_id: str
    student_id: str
    concept_id: str
    learning_cycle_id: uuid.UUID
    assessment_phase: AssessmentPhase
    status: GameSessionStatus
    started_at: datetime
    completed_at: datetime | None = None


class GameplayEventRequest(BaseModel):
    game_session_id: str = Field(min_length=1)
    task_id: str | None = None
    event_type: GameplayEventType
    event_timestamp: datetime
    event_payload: dict[str, Any] = Field(default_factory=dict)


class GameplayEventResponse(BaseModel):
    id: uuid.UUID
    game_session_id: str
    task_id: str | None
    event_type: GameplayEventType
    event_timestamp: datetime
    event_payload: dict[str, Any]


class GameTaskAttemptRequest(BaseModel):
    game_session_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    # One row is written per attempt (see GameTaskAttempt in models.py) —
    # attempt_number distinguishes repeated attempts at the same task_id.
    attempt_number: int = Field(default=1, gt=0)
    attempts_count: int = Field(default=1, ge=0)
    wrong_attempts: int = Field(default=0, ge=0)
    hints_used: int = Field(default=0, ge=0)
    skipped_steps: int = Field(default=0, ge=0)
    time_taken_sec: float = Field(default=0, ge=0)
    is_completed: bool = False
    is_successful: bool = False
    score: float | None = Field(default=None, ge=0, le=1)
    # Which Easy/Medium/Hard variant this attempt was (Milestone 3 Steps
    # 11-13). Optional because older rows and other task types predate it.
    activity_id: str | None = None
    variant_id: str | None = None
    difficulty_level: DifficultyLevel | None = None


class GameTaskAttemptResponse(BaseModel):
    id: uuid.UUID
    game_session_id: str
    task_id: str
    attempt_number: int
    attempts_count: int
    wrong_attempts: int
    hints_used: int
    skipped_steps: int
    time_taken_sec: float
    is_completed: bool
    is_successful: bool
    score: float | None
    activity_id: str | None
    variant_id: str | None
    difficulty_level: DifficultyLevel | None


class VariantUsageResponse(BaseModel):
    """How many completed task attempts this student already has for each
    variant of one concept — what the frontend's "maximum two uses" rule
    (Milestone 3 Step 13) filters on before picking the next assessment's
    6 tasks. A variant_id absent from this map has never been attempted."""

    usage_counts: dict[str, int]


class GameResultResponse(BaseModel):
    """The calculated Game Analytics result. The frontend never computes
    any of these rates itself — they always come from here."""

    game_session_id: str
    student_id: str
    concept_id: str
    learning_cycle_id: uuid.UUID | None
    assessment_phase: AssessmentPhase | None
    tasks_total: int
    tasks_attempted: int
    tasks_completed: int
    successful_tasks: int
    game_success_rate: float
    game_completion_rate: float
    game_avg_attempts_per_task: float
    game_hint_rate: float
    game_difficulty_level: str
    game_active_time_sec: int
    wrong_attempt_count: int
    retry_count: int
    total_hint_count: int
    skipped_step_count: int
    engagement_level: str
    behavioral_difficulty: str
    hint_dependency: float
    game_mastery_score: float
    # Categorical low/medium/high research outputs — prototype values, not
    # validated ML predictions (see Milestone 3 Step 17).
    game_mastery_level: str | None
    game_engagement_level: str | None
    hint_dependency_level: str | None
    model_version: str | None
    completed_at: datetime
