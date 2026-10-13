"""Validated, versioned input contract for independently audited task exports."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DATASET_SCHEMA_VERSION = "game-task-dataset-v1"
FEATURE_SCHEMA_VERSION = "game-next-hint-features-v1"
MODEL_VERSION = "game-next-hint-logreg-v1"
TARGET_DEFINITION = (
    "At the end of task t, predict whether the next observed task by explicit "
    "task_order in the same learner session requests at least one hint. "
    "Only completed next tasks are supervised: 1 for observed positive hints; "
    "0 for verified complete hint observation with zero hints; otherwise unknown."
)

NonEmpty = Annotated[str, Field(min_length=1, pattern=r"\S")]
Count = Annotated[int, Field(ge=0)]
Difficulty = Literal["easy", "medium", "hard"]


class TaskRecord(BaseModel):
    """One task occurrence, aggregated across its steps and retries.

    Required nullable fields must be explicitly supplied as null when unavailable.
    IDs are for audit/grouping only. No ORM defaults imply verified observations.
    """

    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    student_code: NonEmpty
    session_id: NonEmpty
    learning_cycle_id: NonEmpty
    game_type: NonEmpty | None
    task_id: NonEmpty
    task_order: Annotated[int, Field(ge=1)]
    difficulty: Difficulty | None
    concept: NonEmpty | None
    total_steps: Annotated[int, Field(gt=0)] | None
    first_attempt_correct_steps: Count | None
    wrong_attempts: Count | None
    retry_count: Count | None
    hint_requests: Count | None
    steps_with_hints: Count | None
    task_duration_seconds: Annotated[float, Field(ge=0)] | None
    task_completed: bool | None
    next_task_hint_used_label: Annotated[int, Field(ge=0, le=1)] | None = None

    # Extra evidence gates, deliberately conservative for historical rows.
    hint_observation_complete: bool = False
    task_duration_reliable: bool = False
    # Scheduled information captured at task t's prediction cutoff, never t+1's row.
    next_task_difficulty: Difficulty | None = None

    @model_validator(mode="after")
    def consistent_counts(self) -> "TaskRecord":
        for field in ("first_attempt_correct_steps", "steps_with_hints"):
            value = getattr(self, field)
            if value is not None and self.total_steps is not None:
                if value > self.total_steps:
                    raise ValueError(f"{field} cannot exceed total_steps")
        if self.steps_with_hints is not None and self.hint_requests is not None:
            if self.steps_with_hints > self.hint_requests:
                raise ValueError("steps_with_hints cannot exceed hint_requests")
        if self.hint_observation_complete and self.hint_requests is None:
            raise ValueError(
                "complete hint observation requires a known hint_requests count"
            )
        if self.task_duration_reliable and self.task_duration_seconds is None:
            raise ValueError("reliable duration requires task_duration_seconds")
        return self


def validate_dataset(rows: list[TaskRecord | dict]) -> list[TaskRecord]:
    """Reject ambiguous identity/order; canonicalize without database insertion order."""
    records = [TaskRecord.model_validate(row) for row in rows]
    sessions: dict[str, tuple] = {}
    positions: set[tuple[str, int]] = set()
    tasks: set[tuple[str, str]] = set()
    for row in records:
        owner = (row.student_code, row.learning_cycle_id, row.game_type)
        if row.session_id in sessions and sessions[row.session_id] != owner:
            raise ValueError(
                "session_id must have one learner, learning cycle and game type"
            )
        sessions[row.session_id] = owner
        position = (row.session_id, row.task_order)
        task = (row.session_id, row.task_id)
        if position in positions:
            raise ValueError(f"duplicate task_order within session: {position}")
        if task in tasks:
            raise ValueError(
                f"duplicate task_id within session: {task}; aggregate retries first"
            )
        positions.add(position)
        tasks.add(task)
    return sorted(records, key=lambda row: (row.session_id, row.task_order))
