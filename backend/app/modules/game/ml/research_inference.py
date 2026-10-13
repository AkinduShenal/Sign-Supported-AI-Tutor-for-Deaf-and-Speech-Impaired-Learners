"""Offline research inference; independent labels are never read as predictors."""

from .research_dataset import feature_set
from .research_schema import ResearchObservation
from .research_training import research_frame
from .training import TrainingRun


def predict_research(run: TrainingRun, observation: ResearchObservation | dict) -> dict:
    row = ResearchObservation.model_validate(observation)
    definition = run.metadata["feature_set"]
    spec = feature_set(definition["name"], tuple(definition["categorical"]))
    if list(spec.names) != run.metadata["feature_names"]:
        raise ValueError(
            "Research artifact feature definition does not match this implementation"
        )
    frame = research_frame((row,), spec)
    probabilities = run.model.predict_proba(frame)[0]
    by_class = dict(zip(run.model.classes_, map(float, probabilities)))
    return {
        "target": run.metadata["target"],
        "prediction": str(run.model.predict(frame)[0]),
        "class_probabilities": {
            label: by_class.get(label, 0.0) for label in run.metadata["class_labels"]
        },
        "model_version": run.metadata["model_version"],
        "feature_set": spec.name,
        "status": "offline_development_only_not_research_validated",
    }
