"""Research bundles use the existing protected local artifact lifecycle."""

import json
from pathlib import Path

from .artifacts import load_artifact, save_artifact
from .research_schema import RESEARCH_DATASET_VERSION, RESEARCH_FEATURE_VERSION
from .research_training import (
    ClassifierName,
    ResearchComparison,
    TargetName,
    research_model_version,
)
from .training import TrainingRun


def save_comparison(comparison: ResearchComparison, destination: str | Path) -> Path:
    if set(comparison.models) != {"score_only", "score_plus_behaviour"}:
        raise ValueError(
            "A paired comparison must contain exactly the two declared feature sets"
        )
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, run in comparison.models.items():
        save_artifact(run, destination / name)
    with (destination / "comparison.json").open("x", encoding="utf-8") as stream:
        json.dump(comparison.report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return destination


def load_research_artifact(
    source: str | Path,
    *,
    target: TargetName,
    classifier: ClassifierName,
    trusted_local_artifact: bool = False,
) -> TrainingRun:
    # Label names are loaded from the trusted model metadata, not presumed binary.
    expected = research_model_version(target, classifier)
    run = load_artifact(
        source,
        trusted_local_artifact=trusted_local_artifact,
        expected_model_version=expected,
        expected_feature_schema_version=RESEARCH_FEATURE_VERSION,
    )
    if (
        run.metadata.get("dataset_schema_version") != RESEARCH_DATASET_VERSION
        or run.metadata.get("target") != target
        or run.metadata.get("classifier") != classifier
    ):
        raise ValueError(
            "Research artifact target/classifier/dataset contract does not match"
        )
    return run
