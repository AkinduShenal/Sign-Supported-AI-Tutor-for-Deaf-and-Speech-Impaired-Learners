"""Audited session aggregation and predeclared paired research feature sets."""

from dataclasses import dataclass

from .dataset import FeatureExtraction
from .research_schema import IndependentLabel, ObservationContext, ResearchObservation
from .schema import TaskRecord, validate_dataset

BEHAVIOUR_FEATURES = (
    "wrong_attempts",
    "wrong_attempts_per_step",
    "retry_count",
    "retries_per_step",
    "hint_count",
    "hint_usage_rate",
    "completion_rate",
    "task_completed",
    "skipped_steps",
    "skipped_steps_per_step",
    "task_duration_seconds",
    "duration_per_step",
)
COMMON_CONTEXT = ("concept", "game_type", "assessment_phase")


@dataclass(frozen=True)
class FeatureSet:
    name: str
    numeric: tuple[str, ...]
    categorical: tuple[str, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return self.numeric + self.categorical


def feature_set(name: str, common_context: tuple[str, ...] = ()) -> FeatureSet:
    if len(set(common_context)) != len(common_context) or set(common_context) - set(
        COMMON_CONTEXT
    ):
        raise ValueError(
            "Common context must be a unique subset of concept/game_type/assessment_phase"
        )
    if name not in ("score_only", "score_plus_behaviour"):
        raise ValueError("Unknown research feature set")
    numeric = ("gameplay_score",) + (
        BEHAVIOUR_FEATURES if name == "score_plus_behaviour" else ()
    )
    return FeatureSet(name, numeric, common_context)


def extract_research_features(row: ResearchObservation) -> FeatureExtraction:
    def per_step(value: int | float | None) -> float | None:
        return (
            None
            if value is None or row.total_steps is None
            else value / row.total_steps
        )

    hints = row.hint_count if row.hint_observation_complete else None
    hinted_steps = row.steps_with_hints if row.hint_observation_complete else None
    duration = row.task_duration_seconds if row.task_duration_reliable else None
    values = {
        "gameplay_score": row.gameplay_score,
        "wrong_attempts": row.wrong_attempts,
        "wrong_attempts_per_step": per_step(row.wrong_attempts),
        "retry_count": row.retry_count,
        "retries_per_step": per_step(row.retry_count),
        "hint_count": hints,
        "hint_usage_rate": per_step(hinted_steps),
        "completion_rate": None
        if row.tasks_completed is None
        else row.tasks_completed / row.tasks_total,
        "task_completed": None
        if row.task_completed is None
        else int(row.task_completed),
        "skipped_steps": row.skipped_steps,
        "skipped_steps_per_step": per_step(row.skipped_steps),
        "task_duration_seconds": duration,
        "duration_per_step": per_step(duration),
        "concept": row.concept,
        "game_type": row.game_type,
        "assessment_phase": row.assessment_phase,
    }
    unavailable = {
        name: "audited metric/denominator unavailable"
        for name, value in values.items()
        if value is None
    }
    if not row.hint_observation_complete:
        for name in ("hint_count", "hint_usage_rate"):
            unavailable[name] = "whole-window hint coverage is unverified"
    if not row.task_duration_reliable:
        for name in ("task_duration_seconds", "duration_per_step"):
            unavailable[name] = "task duration reliability is unverified"
    return FeatureExtraction(values, unavailable)


def aggregate_observation(
    tasks: list[TaskRecord | dict],
    *,
    context: ObservationContext,
    difficulty_label: IndependentLabel | None,
    mastery_label: IndependentLabel | None = None,
    first_attempt_observation_complete: bool = False,
    skipped_steps_by_task: dict[str, int] | None = None,
) -> ResearchObservation:
    """Aggregate a complete audited task roster; never sum only available counts.

    Caller must verify that the roster contains every task in the declared window,
    including abandoned tasks, and freeze inputs at the cutoff. TaskRecord has no
    timestamps or first-submission coverage evidence, so those are explicit inputs.
    """
    records = validate_dataset(tasks)
    if not records:
        raise ValueError("A research observation needs at least one observed task")
    for row in records:
        if (row.student_code, row.session_id, row.concept, row.game_type) != (
            context.student_code,
            context.session_id,
            context.concept,
            context.game_type,
        ):
            raise ValueError(
                "All tasks must match the learner/session/concept/mode observation context"
            )

    def total(name: str) -> int | float | None:
        values = [getattr(row, name) for row in records]
        return None if any(value is None for value in values) else sum(values)

    skipped = None
    if skipped_steps_by_task is not None:
        if set(skipped_steps_by_task) != {row.task_id for row in records}:
            raise ValueError(
                "Skipped-step evidence must cover exactly the observed task roster"
            )
        for row in records:
            count = skipped_steps_by_task[row.task_id]
            if (
                type(count) is not int
                or count < 0
                or (row.total_steps is not None and count > row.total_steps)
            ):
                raise ValueError(
                    "Skipped-step counts must be nonnegative integers within planned steps"
                )
        skipped = sum(skipped_steps_by_task.values())
    completions = [row.task_completed for row in records]
    completed_count = None if None in completions else sum(completions)
    completed = (
        False if False in completions else (None if None in completions else True)
    )
    reliable_duration = all(row.task_duration_reliable for row in records)
    return ResearchObservation(
        **context.model_dump(),
        total_steps=total("total_steps"),
        first_attempt_correct_steps=total("first_attempt_correct_steps"),
        first_attempt_observation_complete=first_attempt_observation_complete,
        wrong_attempts=total("wrong_attempts"),
        retry_count=total("retry_count"),
        hint_count=total("hint_requests"),
        steps_with_hints=total("steps_with_hints"),
        hint_observation_complete=all(row.hint_observation_complete for row in records),
        tasks_total=len(records),
        tasks_completed=completed_count,
        task_completed=completed,
        skipped_steps=skipped,
        task_duration_seconds=total("task_duration_seconds")
        if reliable_duration
        else None,
        task_duration_reliable=reliable_duration,
        difficulty_label=difficulty_label,
        mastery_label=mastery_label,
    )
