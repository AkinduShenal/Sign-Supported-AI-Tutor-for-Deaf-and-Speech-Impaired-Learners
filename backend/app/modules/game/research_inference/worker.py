"""Standalone isolated interpreter worker. Only nine numerical features enter.

No application imports, network, model fitting, artifact extraction or writes.
Every process verifies the frozen bundle and ten fixtures before prediction.
"""

import hashlib
import importlib.metadata
import io
import json
import math
import platform
import sys
import warnings
from pathlib import Path
from zipfile import ZipFile

# -I excludes the script directory; add only this trusted, dedicated code folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import CLASS_ORDER, CONTRACT, DEPENDENCIES, FEATURE_ORDER, MEMBER_HASHES, MODEL_SHA256, MODEL_STATUS, VALIDATED_PYTHON


class WorkerUnavailable(ValueError):
    pass


def require(condition):
    if not condition:
        raise WorkerUnavailable("Frozen model verification failed")


def check_metadata(metadata):
    require(metadata["feature_names"] == list(FEATURE_ORDER) and metadata["feature_count"] == 9)
    require(metadata["classes"] == list(CLASS_ORDER))
    require(metadata["model_status"] == MODEL_STATUS and metadata["teacher_verified_prediction"] is False)
    require(metadata["dependencies"] == DEPENDENCIES)


def check_runtime(versions, python):
    require(versions == DEPENDENCIES and python == VALIDATED_PYTHON)


def check_features(features):
    require(isinstance(features, dict) and set(features) == set(FEATURE_ORDER))
    for name, value in features.items():
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0)
        if name in ("first_attempt_accuracy", "game_success_rate"):
            require(value <= 1)
        if name.endswith("_count") or name == "game_active_time_sec":
            # Colab fixtures serialize integral counts as floats; no fractional counts.
            require(float(value).is_integer())


def execute(archive_path, features):
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(len(names) == 4 and set(names) == set(MEMBER_HASHES))
        require(all(entry.file_size <= 1_000_000 for entry in archive.infolist()))
        members = {name: archive.read(name) for name in names}
    for name, expected in MEMBER_HASHES.items():
        require(hashlib.sha256(members[name]).hexdigest() == expected)
    metadata = json.loads(members["model_metadata.json"])
    verification = json.loads(members["verification_report.json"])
    fixtures = json.loads(members["frozen_predictions.json"])
    check_metadata(metadata)
    require(verification["status"] == "PASS" and verification["model_sha256"] == MODEL_SHA256)
    versions = {name: importlib.metadata.version(name) for name in DEPENDENCIES}
    check_runtime(versions, platform.python_version())
    require(fixtures["feature_order"] == list(FEATURE_ORDER) and fixtures["class_order"] == list(CLASS_ORDER))
    require(len(fixtures["records"]) == verification["tested_records"] == 10)
    for record in fixtures["records"]:
        check_features(record["features"])
    if features is not None:
        check_features(features)

    # Integrity/runtime checks precede deserialization of the trusted local pickle.
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = joblib.load(io.BytesIO(members["game_behaviour_model.joblib"]))
        require(isinstance(model, Pipeline))
        require([type(step) for _, step in model.steps] == [SimpleImputer, StandardScaler, LogisticRegression])
        require(list(model.feature_names_in_) == list(FEATURE_ORDER) and model.n_features_in_ == 9)
        require(list(model.classes_) == list(CLASS_ORDER))
        frame = pd.DataFrame([r["features"] for r in fixtures["records"]], columns=FEATURE_ORDER, dtype="float64")
        labels = model.predict(frame)
        probabilities = model.predict_proba(frame)
        expected = np.asarray([[r["expected_probabilities"][c] for c in CLASS_ORDER] for r in fixtures["records"]])
        require(list(labels) == [r["expected_prediction"] for r in fixtures["records"]])
        require(probabilities.shape == (10, 3) and np.isfinite(probabilities).all())
        require(np.allclose(probabilities, expected, atol=1e-12, rtol=0))
        output = {
            "model_metadata": metadata, "model_checksum": MODEL_SHA256,
            "feature_contract": CONTRACT, "runtime": {"python": platform.python_version(), "dependencies": versions},
            "frozen_reproduction": {"records": 10, "predictions": list(map(str, labels)),
                                    "probabilities": probabilities.tolist(),
                                    "maximum_probability_difference": float(np.abs(probabilities - expected).max())},
        }
        if features is not None:
            current = pd.DataFrame([features], columns=FEATURE_ORDER, dtype="float64")
            predicted = str(model.predict(current)[0])
            values = model.predict_proba(current)[0]
            require(predicted in CLASS_ORDER and len(values) == 3 and np.isfinite(values).all())
            require(((values >= 0) & (values <= 1)).all() and abs(float(values.sum()) - 1) <= 1e-12)
            output.update(predicted_level=predicted, probabilities=dict(zip(CLASS_ORDER, map(float, values))))
        require(not caught)
    return output


def deny_network(event, args):
    if event in ("socket.connect", "socket.bind", "socket.getaddrinfo"):
        raise WorkerUnavailable("Network disabled")


def main():
    sys.addaudithook(deny_network)
    try:
        require(len(sys.argv) == 2)
        request = json.loads(sys.stdin.read(16_384))
        require(set(request) == {"features"})
        output = execute(Path(sys.argv[1]), request["features"])
        print(json.dumps(output, allow_nan=False))
    except Exception:
        # Paths, pickle errors, warnings and stack traces never reach the API.
        print('{"error":"experimental_model_unavailable"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
