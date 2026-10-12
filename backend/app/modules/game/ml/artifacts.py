"""Local artifact bundles; no overwrite and no implicit pickle deserialization."""

import hashlib
import json
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from .schema import FEATURE_SCHEMA_VERSION, MODEL_VERSION
from .training import TrainingRun, runtime_versions


def save_artifact(run: TrainingRun, destination: str | Path) -> Path:
    """Serialize only a locally fitted pipeline constructed by this training module.

    A fresh directory is required even if an existing directory is empty. Metadata
    is written last; a failed save leaves a non-loadable bundle for inspection.
    """
    if not isinstance(run.model, Pipeline):
        raise TypeError("Expected a locally fitted sklearn Pipeline")
    check_is_fitted(run.model.named_steps["classifier"])
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    model_path = destination / "model.joblib"
    with model_path.open("xb") as stream:
        joblib.dump(run.model, stream, compress=3)
    metadata = {
        **run.metadata,
        "artifact_format": "joblib_trusted_local_only",
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
    }
    with (destination / "metadata.json").open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return destination


def load_artifact(
    source: str | Path,
    *,
    trusted_local_artifact: bool = False,
    expected_model_version: str = MODEL_VERSION,
    expected_feature_schema_version: str = FEATURE_SCHEMA_VERSION,
) -> TrainingRun:
    """Explicit trust required: joblib can execute code. Hashes detect corruption only.

    Never enable this for uploaded/downloaded or otherwise untrusted bundles.
    """
    if not trusted_local_artifact:
        raise ValueError(
            "Loading joblib requires trusted_local_artifact=True for a trusted local bundle"
        )
    source = Path(source)
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    if (
        metadata.get("feature_schema_version") != expected_feature_schema_version
        or metadata.get("model_version") != expected_model_version
    ):
        raise ValueError(
            "Artifact schema/model version does not match this offline implementation"
        )
    if metadata.get("runtime_versions") != runtime_versions():
        raise ValueError(
            "Artifact runtime versions differ; recreate its pinned training environment"
        )
    model_path = source / "model.joblib"
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != metadata.get(
        "model_sha256"
    ):
        raise ValueError("Artifact checksum mismatch; refusing deserialization")
    model = joblib.load(model_path)
    if not isinstance(model, Pipeline):
        raise ValueError("Artifact is not a sklearn Pipeline")
    check_is_fitted(model.named_steps["classifier"])
    return TrainingRun(model=model, metadata=metadata)
