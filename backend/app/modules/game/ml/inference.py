"""Offline inference for pipeline validation; no production route or DB writes."""

from .dataset import extract_features
from .schema import FEATURE_SCHEMA_VERSION, MODEL_VERSION, TaskRecord
from .training import TrainingRun, feature_frame


def predict_next_hint(
    run: TrainingRun,
    current: TaskRecord,
    previous: TaskRecord | None = None,
) -> dict:
    extraction = extract_features(current, previous)
    frame = feature_frame([extraction.values])
    class_index = list(run.model.classes_).index(1)
    probability = float(run.model.predict_proba(frame)[0, class_index])
    return {
        "next_task_hint_used_prediction": int(probability >= 0.5),
        "next_task_hint_probability": probability,
        "decision_threshold": 0.5,
        "model_version": MODEL_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "unavailable_features": extraction.unavailable,
        "status": "offline_development_only_not_research_validated",
    }
