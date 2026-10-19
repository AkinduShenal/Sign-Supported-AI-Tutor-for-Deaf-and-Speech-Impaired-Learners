"""Independent-label, learner–concept–assessment-session research contract."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import Count, NonEmpty

RESEARCH_DATASET_VERSION = "game-research-observation-v1"
RESEARCH_FEATURE_VERSION = "game-research-features-v1"
SCORE_DEFINITION = "first_attempt_correctness_v1"
TARGET_DEFINITIONS = {
    "difficulty": "Independent teacher/quiz/test learner mathematical difficulty classification for this concept and assessment session.",
    "mastery": "Independent teacher/quiz/test concept mastery classification for this concept and assessment session.",
}
UnitRate = Annotated[float, Field(ge=0, le=1)]
# Accept ISO timestamps in local JSON exports while requiring timezone evidence.
Timestamp = Annotated[datetime, Field(strict=False)]


class IndependentLabel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    student_code: NonEmpty
    session_id: NonEmpty
    concept: NonEmpty
    assessment_phase: Literal["pre_tutor", "post_tutor"]
    value: NonEmpty
    source: Literal["teacher", "quiz", "test"]
    source_reference: NonEmpty
    assessed_at: Timestamp | None = None
    assessed_on: Annotated[date, Field(strict=False)] | None = None
    assessment_timing: Literal["before_gameplay", "after_gameplay"] | None = None
    revision_before_assessment: bool | None = None
    revision_description: NonEmpty | None = None
    # Audit-only assessment evidence; feature selection never reads these fields.
    assessment_score: Count | None = None
    assessment_max_score: Annotated[int, Field(gt=0)] | None = None
    rubric_version: NonEmpty
    gameplay_independent: bool

    @model_validator(mode="after")
    def independent_and_dated(self) -> "IndependentLabel":
        if not self.gameplay_independent:
            raise ValueError(
                "Labels must be assessed independently of gameplay heuristics/features"
            )
        if self.assessed_at is None and self.assessed_on is None:
            raise ValueError("Label needs an assessment timestamp or recorded date")
        if self.assessed_at is not None:
            if self.assessed_at.tzinfo is None or self.assessed_at.utcoffset() is None:
                raise ValueError("Label assessment timestamp must include a timezone")
            if (
                self.assessed_on is not None
                and self.assessed_on != self.assessed_at.date()
            ):
                raise ValueError("Assessment date contradicts the timestamp")
        if (self.assessment_score is None) != (self.assessment_max_score is None):
            raise ValueError("Assessment score and maximum must be supplied together")
        if (
            self.assessment_score is not None
            and self.assessment_score > self.assessment_max_score
        ):
            raise ValueError("Assessment score exceeds maximum")
        if (
            self.revision_before_assessment is True
            and self.revision_description is None
        ):
            raise ValueError("Revision provenance requires a description")
        return self


class ObservationContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    student_code: NonEmpty
    session_id: NonEmpty
    concept: NonEmpty
    game_type: NonEmpty | None
    activity_ids: Annotated[list[NonEmpty], Field(min_length=1)]
    assessment_phase: Literal["pre_tutor", "post_tutor"]
    observation_started_at: Timestamp
    observation_ended_at: Timestamp

    @model_validator(mode="after")
    def valid_window(self) -> "ObservationContext":
        for value in (self.observation_started_at, self.observation_ended_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Observation timestamps must include a timezone")
        if self.observation_ended_at <= self.observation_started_at:
            raise ValueError("Observation end must be after start")
        if len(set(self.activity_ids)) != len(self.activity_ids):
            raise ValueError("activity_ids must contain distinct activity identifiers")
        return self


class ResearchObservation(ObservationContext):
    """One aggregate per learner–concept–assessment session, frozen at window end.

    Supplied metrics are audited whole-window totals. None means unavailable;
    absence of events never implies a measured zero. Question difficulty is not a
    learner label and is deliberately not an input field in this version.
    """

    total_steps: Annotated[int, Field(gt=0)] | None
    first_attempt_correct_steps: Count | None
    first_attempt_observation_complete: bool = False
    score_definition: Literal["first_attempt_correctness_v1"] = SCORE_DEFINITION
    gameplay_score: UnitRate | None = None
    wrong_attempts: Count | None
    retry_count: Count | None
    hint_count: Count | None
    steps_with_hints: Count | None
    hint_observation_complete: bool = False
    tasks_total: Annotated[int, Field(gt=0)]
    tasks_completed: Count | None
    task_completed: bool | None
    skipped_steps: Count | None
    task_duration_seconds: Annotated[float, Field(ge=0)] | None
    task_duration_reliable: bool = False
    difficulty_label: IndependentLabel | None
    mastery_label: IndependentLabel | None = None

    @model_validator(mode="after")
    def valid_totals_and_score(self) -> "ResearchObservation":
        for target in ("difficulty", "mastery"):
            label = getattr(self, f"{target}_label")
            if label is not None:
                for key in (
                    "student_code",
                    "session_id",
                    "concept",
                    "assessment_phase",
                ):
                    if getattr(label, key) != getattr(self, key):
                        raise ValueError(
                            f"{target} label {key} does not match the observation"
                        )
        for name in (
            "first_attempt_correct_steps",
            "steps_with_hints",
            "skipped_steps",
        ):
            value = getattr(self, name)
            if (
                value is not None
                and self.total_steps is not None
                and value > self.total_steps
            ):
                raise ValueError(f"{name} cannot exceed total_steps")
        if self.tasks_completed is not None:
            if self.tasks_completed > self.tasks_total:
                raise ValueError("tasks_completed cannot exceed tasks_total")
            if self.task_completed is not None and self.task_completed != (
                self.tasks_completed == self.tasks_total
            ):
                raise ValueError(
                    "task_completed contradicts tasks_completed/tasks_total"
                )
        if self.hint_count is not None and self.steps_with_hints is not None:
            if self.steps_with_hints > self.hint_count:
                raise ValueError("steps_with_hints cannot exceed hint_count")
        if self.hint_observation_complete and self.hint_count is None:
            raise ValueError("Complete hint observation requires hint_count")
        score_known = (
            self.first_attempt_observation_complete
            and self.total_steps is not None
            and self.first_attempt_correct_steps is not None
        )
        derived = (
            self.first_attempt_correct_steps / self.total_steps if score_known else None
        )
        if self.gameplay_score is not None:
            if derived is None or abs(self.gameplay_score - derived) > 1e-12:
                raise ValueError(
                    "gameplay_score must equal audited first-attempt correct / planned steps"
                )
        self.gameplay_score = derived
        if self.task_duration_reliable:
            if self.task_duration_seconds is None:
                raise ValueError("Reliable duration requires task_duration_seconds")
            window = (
                self.observation_ended_at - self.observation_started_at
            ).total_seconds()
            if self.task_duration_seconds > window:
                raise ValueError(
                    "Aggregated task duration cannot exceed the observation window"
                )
        return self

    @property
    def first_attempt_accuracy(self) -> float | None:
        return self.gameplay_score


def validate_research_dataset(
    rows: list[ResearchObservation | dict],
) -> list[ResearchObservation]:
    records = [ResearchObservation.model_validate(row) for row in rows]
    units: set[tuple] = set()
    session_owners: dict[str, tuple] = {}
    for row in records:
        key = (row.session_id, row.concept, row.assessment_phase)
        if key in units:
            raise ValueError(
                "Duplicate learner–concept–assessment session; aggregate its tasks first"
            )
        units.add(key)
        owner = (row.student_code, row.assessment_phase, row.game_type)
        if row.session_id in session_owners and session_owners[row.session_id] != owner:
            raise ValueError(
                "A game session must have one learner, phase and game type"
            )
        session_owners[row.session_id] = owner
    return sorted(
        records, key=lambda row: (row.session_id, row.concept, row.assessment_phase)
    )
