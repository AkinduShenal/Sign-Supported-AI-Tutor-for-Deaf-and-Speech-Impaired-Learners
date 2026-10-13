"""Configurable independent-label training with one shared paired cohort/split."""

import hashlib
import json
import warnings
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
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
from sklearn.tree import DecisionTreeClassifier

from .research_dataset import FeatureSet, extract_research_features, feature_set
from .research_schema import (
    RESEARCH_DATASET_VERSION,
    RESEARCH_FEATURE_VERSION,
    TARGET_DEFINITIONS,
    ResearchObservation,
    validate_research_dataset,
)
from .schema import NonEmpty
from .training import TrainingDataError, TrainingRun, runtime_versions

ClassifierName = Literal["logistic_regression", "decision_tree", "random_forest"]
TargetName = Literal["difficulty", "mastery"]
DataKind = Literal["synthetic_development", "real_collected"]


class EvaluationConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)
    primary_metric: Literal["macro_f1"] = "macro_f1"
    random_state: Annotated[int, Field(ge=0, le=2**32 - 1)] = 42
    test_size: Annotated[float, Field(gt=0, lt=1)] = 0.25
    min_examples: Annotated[int, Field(ge=4)] = 20
    min_learners: Annotated[int, Field(ge=2)] = 6
    require_all_classes_in_partitions: bool = True


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)
    target: TargetName = "difficulty"
    class_labels: Annotated[tuple[NonEmpty, ...], Field(min_length=2)]
    classifier: ClassifierName = "logistic_regression"
    classifier_parameters: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
    common_context: tuple[str, ...] = ()
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    @model_validator(mode="after")
    def valid_specification(self) -> "ExperimentConfig":
        if len(set(self.class_labels)) != len(self.class_labels):
            raise ValueError("Class labels must be distinct and explicitly ordered")
        feature_set("score_only", self.common_context)
        if {"random_state", "n_jobs"} & self.classifier_parameters.keys():
            raise ValueError(
                "Use evaluation.random_state; n_jobs is fixed to 1 for Random Forest"
            )
        return self


def research_model_version(target: TargetName, classifier: ClassifierName) -> str:
    if target not in TARGET_DEFINITIONS or classifier not in (
        "logistic_regression",
        "decision_tree",
        "random_forest",
    ):
        raise ValueError("Unknown research target/classifier")
    return f"game-research-{target}-{classifier}-v1"


def _digest(value) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def unit_digest(row: ResearchObservation) -> str:
    return _digest(
        [row.student_code, row.session_id, row.concept, row.assessment_phase]
    )


def distribution(labels: np.ndarray, classes: tuple[str, ...]) -> dict[str, int]:
    return {label: int(np.sum(labels == label)) for label in classes}


@dataclass(frozen=True)
class ResearchCohort:
    rows: tuple[ResearchObservation, ...]
    labels: np.ndarray
    exclusions: dict[str, int]
    input_rows: int
    dataset_sha256: str
    target: str
    class_labels: tuple[str, ...]


def prepare_cohort(
    rows: list[ResearchObservation | dict], config: ExperimentConfig
) -> ResearchCohort:
    records = validate_research_dataset(rows)
    selected, labels, exclusions = [], [], Counter()
    for row in records:
        label = getattr(row, f"{config.target}_label")
        if label is not None and label.value not in config.class_labels:
            raise TrainingDataError(
                f"Unknown {config.target} label {label.value!r}; not in configured class labels"
            )
        if label is None:
            exclusions["independent_target_label_unavailable"] += 1
        elif row.gameplay_score is None:
            exclusions["audited_gameplay_score_unavailable"] += 1
        else:
            selected.append(row)
            labels.append(label.value)
    return ResearchCohort(
        tuple(selected),
        np.asarray(labels, dtype=str),
        dict(exclusions),
        len(records),
        _digest([row.model_dump(mode="json") for row in records]),
        config.target,
        config.class_labels,
    )


@dataclass(frozen=True)
class ResearchSplit:
    train: tuple[int, ...]
    test: tuple[int, ...]
    details: dict


def learner_split(cohort: ResearchCohort, config: ExperimentConfig) -> ResearchSplit:
    groups = np.asarray([row.student_code for row in cohort.rows])
    labels, settings = cohort.labels, config.evaluation
    if len(np.unique(labels)) < 2:
        raise TrainingDataError(
            f"Need at least two independent target classes; found {distribution(labels, config.class_labels)}"
        )
    if len(labels) < settings.min_examples or len(set(groups)) < settings.min_learners:
        raise TrainingDataError(
            f"Dataset too small: {len(labels)} eligible observations / {len(set(groups))} learners; "
            f"need {settings.min_examples} / {settings.min_learners}. These are development guardrails, not research power."
        )
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=settings.test_size, random_state=settings.random_state
    )
    train, test = next(splitter.split(np.zeros(len(labels)), labels, groups))
    overlap = set(groups[train]) & set(groups[test])
    if overlap:
        raise TrainingDataError("Learner overlap detected; refusing training")
    if len(set(labels[train])) < 2:
        raise TrainingDataError(
            "Fixed training split has only one target class; collect more independently labelled learners"
        )
    for name, indices in (("train", train), ("test", test)):
        missing = set(config.class_labels) - set(labels[indices])
        if missing and settings.require_all_classes_in_partitions:
            raise TrainingDataError(
                f"Fixed {name} split is missing configured classes {sorted(missing)}; no score-driven seed search is performed"
            )

    def partition(indices) -> dict:
        return {
            "observations": len(indices),
            "learners": len(set(groups[indices])),
            "sessions": len({cohort.rows[i].session_id for i in indices}),
            "label_distribution": distribution(labels[indices], config.class_labels),
            "missing_classes": sorted(set(config.class_labels) - set(labels[indices])),
            "example_indices": [int(i) for i in indices],
            "unit_sha256": [unit_digest(cohort.rows[i]) for i in indices],
            "learner_sha256": sorted(
                _digest(str(code)) for code in set(groups[indices])
            ),
        }

    return ResearchSplit(
        tuple(map(int, train)),
        tuple(map(int, test)),
        {
            "method": "GroupShuffleSplit",
            "group": "student_code",
            "number_of_splits": 1,
            "random_state": settings.random_state,
            "test_fraction_of_learners": settings.test_size,
            "train_test_learner_overlap": len(overlap),
            "train": partition(train),
            "test": partition(test),
        },
    )


def research_frame(
    rows: tuple[ResearchObservation, ...], spec: FeatureSet
) -> pd.DataFrame:
    frame = pd.DataFrame(
        [extract_research_features(row).values for row in rows], columns=spec.names
    )
    for column in spec.numeric:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
    for column in spec.categorical:
        frame[column] = (
            frame[column].astype(object).where(frame[column].notna(), np.nan)
        )
    return frame


def make_research_pipeline(config: ExperimentConfig, spec: FeatureSet) -> Pipeline:
    seed = config.evaluation.random_state
    classifiers = {
        "logistic_regression": LogisticRegression(
            solver="lbfgs", max_iter=2000, random_state=seed
        ),
        "decision_tree": DecisionTreeClassifier(
            max_depth=5, min_samples_leaf=2, random_state=seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=2,
            n_jobs=1,
            random_state=seed,
        ),
    }
    classifier = classifiers[config.classifier]
    try:
        classifier.set_params(**config.classifier_parameters)
    except ValueError as error:
        raise ValueError(f"Invalid {config.classifier} parameters: {error}") from error
    numeric_steps = [
        (
            "impute",
            SimpleImputer(
                strategy="median", add_indicator=True, keep_empty_features=True
            ),
        )
    ]
    if config.classifier == "logistic_regression":
        numeric_steps.append(("scale", StandardScaler()))
    transformers = [("numeric", Pipeline(numeric_steps), list(spec.numeric))]
    if spec.categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "impute",
                            SimpleImputer(
                                strategy="constant",
                                fill_value="__missing__",
                                keep_empty_features=True,
                            ),
                        ),
                        (
                            "encode",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                list(spec.categorical),
            )
        )
    return Pipeline(
        [
            ("preprocess", ColumnTransformer(transformers, remainder="drop")),
            ("classifier", classifier),
        ]
    )


def evaluate_research(
    y_true: np.ndarray, y_pred: np.ndarray, classes: tuple[str, ...]
) -> dict:
    if not len(y_true) or len(y_true) != len(y_pred):
        raise ValueError(
            "Evaluation needs nonempty, equally sized truth and predictions"
        )
    if len(classes) < 2 or len(set(classes)) != len(classes):
        raise ValueError(
            "Evaluation class labels must be unique with at least two classes"
        )
    if (set(y_true) | set(y_pred)) - set(classes):
        raise ValueError(
            "Evaluation encountered labels outside the configured class set"
        )
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, zero_division=0
    )
    return {
        "primary_metric": "macro_f1",
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
        "confusion_matrix_labels": list(classes),
        "confusion_matrix_axes": "rows=actual, columns=predicted",
        "per_class": {
            label: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate(classes)
        },
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred))
        if len(set(y_true)) >= 2
        else None,
        "undefined_precision_recall_policy": "zero_division=0; macro averages over all configured rubric classes including absent classes",
    }


def fit_experiment(
    cohort: ResearchCohort,
    split: ResearchSplit,
    config: ExperimentConfig,
    feature_set_name: Literal["score_only", "score_plus_behaviour"],
    *,
    provenance: str,
    data_kind: DataKind,
) -> TrainingRun:
    if cohort.target != config.target or cohort.class_labels != config.class_labels:
        raise ValueError(
            "Cohort target and class order must match the experiment configuration"
        )
    if not provenance.strip() or data_kind not in (
        "synthetic_development",
        "real_collected",
    ):
        raise ValueError(
            "Explicit nonempty provenance and synthetic/real data kind are required"
        )
    # Refuse arbitrary manifests that overlap, drop observations, or split learners.
    if (
        set(split.train) & set(split.test)
        or set(split.train) | set(split.test) != set(range(len(cohort.rows)))
        or len(split.train) + len(split.test) != len(cohort.rows)
        or not split.train
        or not split.test
    ):
        raise ValueError("Split must partition every cohort observation exactly once")
    train_learners = {cohort.rows[i].student_code for i in split.train}
    test_learners = {cohort.rows[i].student_code for i in split.test}
    if train_learners & test_learners:
        raise ValueError("Split must keep learners separate")
    spec = feature_set(feature_set_name, config.common_context)
    frame = research_frame(cohort.rows, spec)
    model = make_research_pipeline(config, spec)
    train_indices, test_indices = list(split.train), list(split.test)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        try:
            model.fit(frame.iloc[train_indices], cohort.labels[train_indices])
        except ConvergenceWarning as error:
            raise TrainingDataError(
                "Classifier did not converge; no artifact produced"
            ) from error
    predictions = model.predict(frame.iloc[test_indices])
    label_records = []
    for row in cohort.rows:
        label = getattr(row, f"{config.target}_label")
        label_records.append(
            {
                "unit_sha256": unit_digest(row),
                **label.model_dump(
                    mode="json",
                    exclude={
                        "student_code",
                        "session_id",
                        "concept",
                        "assessment_phase",
                    },
                ),
            }
        )
    metadata = {
        "model_version": research_model_version(config.target, config.classifier),
        "dataset_schema_version": RESEARCH_DATASET_VERSION,
        "feature_schema_version": RESEARCH_FEATURE_VERSION,
        "trained_at_utc": datetime.now(UTC).isoformat(),
        "status": "offline_development_only_not_research_validated",
        "prediction_unit": "learner–concept–assessment session",
        "prediction_cutoff": "observation_ended_at; all gameplay metrics frozen before independent assessment outcomes are used as targets",
        "target": config.target,
        "target_definition": TARGET_DEFINITIONS[config.target],
        "class_labels": list(config.class_labels),
        "score_definition": "audited first-attempt correct steps / all planned steps; no success flags, stars or heuristics",
        "feature_set": {
            "name": spec.name,
            "numeric": list(spec.numeric),
            "categorical": list(spec.categorical),
        },
        "feature_names": list(spec.names),
        "transformed_feature_names": model.named_steps["preprocess"]
        .get_feature_names_out()
        .tolist(),
        "classifier": config.classifier,
        "classifier_parameters": model.named_steps["classifier"].get_params(),
        "training_data": {
            "source": provenance,
            "kind": data_kind,
            "canonical_dataset_sha256": cohort.dataset_sha256,
        },
        "label_provenance": label_records,
        "runtime_versions": runtime_versions(),
        "evaluation_configuration": config.evaluation.model_dump(),
        "counts": {
            "input_observations": cohort.input_rows,
            "eligible_observations": len(cohort.rows),
            "distinct_learners": len(train_learners | test_learners),
            "sessions": len({row.session_id for row in cohort.rows}),
            "label_distribution": distribution(cohort.labels, config.class_labels),
            "exclusions": cohort.exclusions,
        },
        "missing_feature_counts": {
            name: int(frame[name].isna().sum()) for name in spec.names
        },
        "split": split.details,
        "evaluation": evaluate_research(
            cohort.labels[test_indices], predictions, config.class_labels
        ),
        "heldout_predictions": [
            {
                "unit_sha256": unit_digest(cohort.rows[i]),
                "actual": str(cohort.labels[i]),
                "predicted": str(prediction),
            }
            for i, prediction in zip(test_indices, predictions)
        ],
        "limitations": [
            "Development validation only; no statistical significance or real-learner improvement claim.",
            "Label independence/roster completeness are exporter assertions requiring external quality review.",
            "Missing behavioural features are imputed on training rows; never filter Model B into a different cohort.",
            "Entirely missing numeric training columns use explicit sklearn zero fallback with missing indicators.",
            "No automatic production integration or final full-dataset refit.",
        ],
    }
    return TrainingRun(model, metadata)


@dataclass(frozen=True)
class ResearchComparison:
    models: dict[str, TrainingRun]
    report: dict


def run_comparison(
    rows: list[ResearchObservation | dict],
    config: ExperimentConfig,
    *,
    provenance: str,
    data_kind: DataKind,
) -> ResearchComparison:
    cohort = prepare_cohort(rows, config)
    split = learner_split(cohort, config)
    models = {
        name: fit_experiment(
            cohort, split, config, name, provenance=provenance, data_kind=data_kind
        )
        for name in ("score_only", "score_plus_behaviour")
    }
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(np.zeros((len(split.train), 1)), cohort.labels[list(split.train)])
    baseline_metrics = evaluate_research(
        cohort.labels[list(split.test)],
        baseline.predict(np.zeros((len(split.test), 1))),
        config.class_labels,
    )
    a, b = (models[name].metadata["evaluation"]["macro_f1"] for name in models)
    delta = b - a
    report = {
        "status": "offline_development_only_not_research_validated",
        "primary_metric": "macro_f1",
        "configuration": config.model_dump(mode="json"),
        "training_data": models["score_only"].metadata["training_data"],
        "counts": models["score_only"].metadata["counts"],
        "split": split.details,
        "models": {name: run.metadata["evaluation"] for name, run in models.items()},
        "majority_class_baseline": baseline_metrics,
        "macro_f1_model_a": a,
        "macro_f1_model_b": b,
        "macro_f1_difference_b_minus_a": delta,
        "behaviour_improved": delta > 0,
        "comparison_outcome": "improved"
        if delta > 0
        else ("no_change" if delta == 0 else "worse"),
        "interpretation": "Behaviour increased held-out macro-F1 in this run."
        if delta > 0
        else "Behaviour did not improve held-out macro-F1 in this run.",
        "statistical_significance": "not_assessed; no significance claim is made",
    }
    return ResearchComparison(models, report)
