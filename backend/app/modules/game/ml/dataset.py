"""Pure feature extraction and next-observed-task target alignment."""

from dataclasses import dataclass

from .schema import TaskRecord, validate_dataset

NUMERIC_FEATURES = (
    "first_attempt_accuracy",
    "wrong_attempts_per_step",
    "retry_count",
    "hint_requests",
    "share_steps_with_hints",
    "task_completed",
    "task_duration_seconds",
)
CATEGORICAL_FEATURES = (
    "game_type",
    "concept",
    "difficulty",
    "previous_task_difficulty",
    "next_task_difficulty",
)
FEATURE_NAMES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass(frozen=True)
class FeatureExtraction:
    values: dict[str, float | str | None]
    unavailable: dict[str, str]


def extract_features(
    current: TaskRecord,
    previous: TaskRecord | None = None,
) -> FeatureExtraction:
    """Prediction cutoff is the end/closure of current, before the next task starts.

    No future task record is accepted. Unreliable durations are masked, not repaired.
    """
    if previous is not None:
        if (
            previous.session_id != current.session_id
            or previous.student_code != current.student_code
            or previous.task_order >= current.task_order
        ):
            raise ValueError(
                "previous task must precede current in the same learner session"
            )

    def per_step(value: int | None) -> float | None:
        if value is None or current.total_steps is None:
            return None
        return value / current.total_steps

    values = {
        "first_attempt_accuracy": per_step(current.first_attempt_correct_steps),
        "wrong_attempts_per_step": per_step(current.wrong_attempts),
        "retry_count": current.retry_count,
        "hint_requests": current.hint_requests,
        "share_steps_with_hints": per_step(current.steps_with_hints),
        "task_completed": (
            None if current.task_completed is None else int(current.task_completed)
        ),
        "task_duration_seconds": (
            current.task_duration_seconds if current.task_duration_reliable else None
        ),
        "game_type": current.game_type,
        "concept": current.concept,
        "difficulty": current.difficulty,
        "previous_task_difficulty": previous.difficulty if previous else None,
        "next_task_difficulty": current.next_task_difficulty,
    }
    unavailable = {
        name: "source metric missing or not verified at prediction cutoff"
        for name, value in values.items()
        if value is None
    }
    if not current.task_duration_reliable:
        unavailable["task_duration_seconds"] = (
            "duration reliability has not been verified"
        )
    if previous is None:
        unavailable["previous_task_difficulty"] = (
            "no previous observed task in this session"
        )
    if current.next_task_difficulty is None:
        unavailable["next_task_difficulty"] = (
            "no scheduled difficulty known before prediction"
        )
    return FeatureExtraction(values, unavailable)


@dataclass(frozen=True)
class TaskExample:
    current: TaskRecord
    next_task_id: str | None
    features: FeatureExtraction
    label: int | None
    exclusion_reason: str | None


def next_task_label(next_task: TaskRecord | None) -> tuple[int | None, str | None]:
    if next_task is None:
        return None, "final_task_no_next_observation"
    if next_task.task_completed is not True:
        return None, "next_task_incomplete_or_completion_unknown"
    if next_task.hint_requests is None:
        return None, "next_task_hint_count_unavailable"
    if next_task.hint_requests > 0:
        return 1, None
    if not next_task.hint_observation_complete:
        return None, "next_task_zero_hints_unverified"
    return 0, None


def build_examples(rows: list[TaskRecord | dict]) -> list[TaskExample]:
    records = validate_dataset(rows)
    examples = []
    for index, current in enumerate(records):
        previous = records[index - 1] if index else None
        following = records[index + 1] if index + 1 < len(records) else None
        if previous is not None and previous.session_id != current.session_id:
            previous = None
        if following is not None and following.session_id != current.session_id:
            following = None
        label, reason = next_task_label(following)
        supplied = current.next_task_hint_used_label
        if supplied is not None and supplied != label:
            raise ValueError(
                f"supplied next-task label conflicts with derived target for "
                f"{current.session_id}/{current.task_id}"
            )
        examples.append(
            TaskExample(
                current=current,
                next_task_id=following.task_id if following else None,
                features=extract_features(current, previous),
                label=label,
                exclusion_reason=reason,
            )
        )
    return examples
