"""Reproducible, learner-separated offline development training and evaluation."""

import hashlib
import json
import platform
import warnings
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .dataset import (
    CATEGORICAL_FEATURES,
    FEATURE_NAMES,
    NUMERIC_FEATURES,
    TaskExample,
    build_examples,
)
from .schema import (
    DATASET_SCHEMA_VERSION,
    FEATURE_SCHEMA_VERSION,
    MODEL_VERSION,
    TARGET_DEFINITION,
    TaskRecord,
)


class TrainingDataError(ValueError):
    """Insufficient or unsuitable observations for honest held-out evaluation."""


@dataclass(frozen=True)
class TrainingRun:
    model: Pipeline
    metadata: dict


def runtime_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "scikit-learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
    }


def feature_frame(values: list[dict]) -> pd.DataFrame:
    """Explicit allowlist; identifiers, labels and future outcomes cannot enter X."""
    frame = pd.DataFrame(values, columns=FEATURE_NAMES)
    for column in NUMERIC_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
    for column in CATEGORICAL_FEATURES:
        frame[column] = (
            frame[column].astype(object).where(frame[column].notna(), np.nan)
        )
    return frame


def make_pipeline(random_state: int = 42) -> Pipeline:
    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(
                    strategy="median", add_indicator=True, keep_empty_features=True
                ),
            ),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            (
                "impute",
                SimpleImputer(
                    strategy="constant",
                    fill_value="__missing__",
                    keep_empty_features=True,
                ),
            ),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    [
                        ("numeric", numeric, list(NUMERIC_FEATURES)),
                        ("categorical", categorical, list(CATEGORICAL_FEATURES)),
                    ],
                    remainder="drop",
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    solver="lbfgs", max_iter=2000, random_state=random_state
                ),
            ),
        ]
    )


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[0, 1],
        zero_division=0,
    )
    return {
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "confusion_matrix_labels": [0, 1],
        "confusion_matrix_axes": "rows=actual, columns=predicted",
        "per_class": {
            str(label): {
                "precision": float(precision[label]),
                "recall": float(recall[label]),
                "f1": float(f1[label]),
                "support": int(support[label]),
            }
            for label in (0, 1)
        },
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=[0, 1], average="macro", zero_division=0)
        ),
        "balanced_accuracy": (
            float(balanced_accuracy_score(y_true, y_pred))
            if len(np.unique(y_true)) == 2
            else None
        ),
        "undefined_precision_recall_policy": "report 0 with support; zero_division=0",
    }


def _distribution(labels: np.ndarray) -> dict[str, int]:
    return {str(label): int(np.sum(labels == label)) for label in (0, 1)}


def split_by_learner(
    examples: list[TaskExample],
    *,
    random_state: int = 42,
    test_size: float = 0.25,
) -> tuple[np.ndarray, np.ndarray]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    groups = np.array([example.current.student_code for example in examples])
    labels = np.array([example.label for example in examples])
    if len(np.unique(groups)) < 2:
        raise TrainingDataError(
            "Need at least two distinct learners for a group-aware split"
        )
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=test_size, random_state=random_state
    )
    train, test = next(splitter.split(np.zeros(len(examples)), labels, groups))
    for name, indices in (("training", train), ("test", test)):
        if len(np.unique(labels[indices])) != 2:
            raise TrainingDataError(
                f"Fixed learner-separated {name} partition has only one target class. "
                "Collect more learners with both outcomes; no score-driven split search is performed."
            )
    return train, test


def train(
    rows: list[TaskRecord | dict],
    *,
    provenance: str,
    data_kind: Literal["synthetic_development", "real_collected"],
    random_state: int = 42,
    test_size: float = 0.25,
) -> TrainingRun:
    if not provenance.strip():
        raise ValueError("An explicit training data source/provenance is required")
    if data_kind not in ("synthetic_development", "real_collected"):
        raise ValueError("data_kind must be synthetic_development or real_collected")
    all_examples = build_examples(rows)
    examples = [example for example in all_examples if example.label is not None]
    labels = np.array([example.label for example in examples], dtype=int)
    if len(np.unique(labels)) < 2:
        raise TrainingDataError(
            f"Need both target classes; found {_distribution(labels)} among {len(examples)} valid examples. "
            "Final tasks, incomplete targets and unverified zero-hint outcomes are excluded."
        )
    learners = {example.current.student_code for example in examples}
    # Engineering smoke-test guardrails, not a statistical power calculation.
    if len(examples) < 20 or len(learners) < 6:
        raise TrainingDataError(
            f"Dataset too small: {len(examples)} valid examples from {len(learners)} learners; "
            "require at least 20 examples and 6 learners for development evaluation. "
            "These thresholds do not establish research adequacy."
        )
    train_indices, test_indices = split_by_learner(
        examples,
        random_state=random_state,
        test_size=test_size,
    )
    frame = feature_frame([example.features.values for example in examples])
    model = make_pipeline(random_state)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        try:
            model.fit(frame.iloc[train_indices], labels[train_indices])
        except ConvergenceWarning as error:
            raise TrainingDataError(
                "Logistic Regression did not converge; no artifact was produced"
            ) from error
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(np.zeros((len(train_indices), 1)), labels[train_indices])

    def partition(indices: np.ndarray) -> dict:
        return {
            "examples": len(indices),
            "learners": len({examples[i].current.student_code for i in indices}),
            "sessions": len({examples[i].current.session_id for i in indices}),
            "label_distribution": _distribution(labels[indices]),
            "example_indices": indices.tolist(),
        }

    canonical = json.dumps(
        [example.current.model_dump(mode="json") for example in all_examples],
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    metadata = {
        "model_version": MODEL_VERSION,
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "trained_at_utc": datetime.now(UTC).isoformat(),
        "training_data": {
            "source": provenance,
            "kind": data_kind,
            "canonical_dataset_sha256": hashlib.sha256(canonical).hexdigest(),
        },
        "status": "offline_development_only_not_research_validated",
        "target_definition": TARGET_DEFINITION,
        "prediction_cutoff": "after current task closure, before next task starts",
        "feature_names": list(FEATURE_NAMES),
        "transformed_feature_names": model.named_steps["preprocess"]
        .get_feature_names_out()
        .tolist(),
        "runtime_versions": runtime_versions(),
        "counts": {
            "distinct_learners": len({e.current.student_code for e in all_examples}),
            "sessions": len({e.current.session_id for e in all_examples}),
            "task_rows": len(all_examples),
            "valid_training_examples": len(examples),
            "learners_with_valid_examples": len(learners),
            "sessions_with_valid_examples": len(
                {e.current.session_id for e in examples}
            ),
            "label_distribution": _distribution(labels),
            "exclusions": dict(
                Counter(e.exclusion_reason for e in all_examples if e.label is None)
            ),
        },
        "missing_feature_counts": {
            name: sum(e.features.values[name] is None for e in examples)
            for name in FEATURE_NAMES
        },
        "split": {
            "method": "GroupShuffleSplit",
            "group": "student_code",
            "random_state": random_state,
            "test_size_fraction_of_learners": test_size,
            "train_test_learner_overlap": 0,
            "number_of_splits": 1,
            "train": partition(train_indices),
            "test": partition(test_indices),
        },
        "evaluation": {
            "logistic_regression": evaluate(
                labels[test_indices], model.predict(frame.iloc[test_indices])
            ),
            "majority_class_baseline": evaluate(
                labels[test_indices],
                baseline.predict(np.zeros((len(test_indices), 1))),
            ),
        },
        "classifier_parameters": model.named_steps["classifier"].get_params(),
        "limitations": [
            "One learner-separated holdout; no final full-dataset refit or research validation.",
            "Probabilities are uncalibrated behaviour estimates, not mathematical ability scores.",
            "Numeric median imputation is fitted on training rows only; entirely missing columns "
            "use sklearn's zero fallback plus missing indicators. Raw observations remain null.",
            "Browser identity must be reconciled to stable learner identity before real-data validation.",
        ],
    }
    return TrainingRun(model=model, metadata=metadata)
