"""Pinned, local Milestone 2.4 experiment; never imports application/DB settings.

Only the approved 2.3.4 retrospective cohort may be fitted. All six settings are
declared before fitting; the shared held-out group never chooses a winner.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .assessment_preparation import (
    ASSESSMENT_FIELDS,
    prepare_datasets,
    read_sheet,
    readiness,
    validate_assessments,
)
from .collection_research import CLASSES, CollectionReview, read_export
from .research_artifacts import load_research_artifact, save_comparison
from .research_dataset import feature_set
from .research_inference import predict_research
from .research_training import (
    ExperimentConfig,
    evaluate_research,
    learner_split,
    make_research_pipeline,
    prepare_cohort,
    research_frame,
    run_comparison,
)
from .session_verification import FIELDS, import_decisions, save_json
from .training import runtime_versions

APPROVED_MANIFEST_SHA256 = (
    "cea05e3aaa8b4d3eac79b10011935aed816c1099a1874a73379db78aa4b2f4ff"
)
FLAGS = (
    "REAL_COLLECTED",
    "RETROSPECTIVE",
    "PRELIMINARY_EXPERIMENTAL",
    "NOT_APPROVED_FOR_PRODUCTION",
)
STATUS = "_".join(FLAGS)
PARAMETERS = {
    "logistic_regression": {"C": 1.0, "solver": "lbfgs", "max_iter": 2000},
    "decision_tree": {"max_depth": 5, "min_samples_leaf": 2, "criterion": "gini"},
    "random_forest": {
        "n_estimators": 100,
        "max_depth": 6,
        "min_samples_leaf": 2,
        "criterion": "gini",
    },
}
SHORT = {"logistic_regression": "lr", "decision_tree": "dt", "random_forest": "rf"}
LEARNER_AGGREGATION = "Majority of session predictions; ties use rubric class order: beginner, intermediate, advanced. One vote per learner in evaluation."


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_inputs(snapshot: Path) -> dict:
    """Pin the approval itself as well as every member and original source hash."""
    manifest_path = snapshot / "snapshot_manifest.json"
    if sha(manifest_path) != APPROVED_MANIFEST_SHA256:
        raise ValueError("Approved snapshot manifest changed; stop before fitting")
    manifest = read_json(manifest_path)
    if (
        not manifest["complete"]
        or manifest["milestone"] != "2.3.4"
        or manifest["models_trained"]
    ):
        raise ValueError("Not the approved preparation-only 2.3.4 snapshot")
    actual = {
        path.relative_to(snapshot).as_posix()
        for path in snapshot.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != set(manifest["files_sha256"]):
        raise ValueError("Snapshot members changed")
    for name, expected in manifest["files_sha256"].items():
        path = snapshot / name
        if (
            not path.resolve().is_relative_to(snapshot.resolve())
            or sha(path) != expected
        ):
            raise ValueError(f"Snapshot member changed: {name}")
    report = read_json(snapshot / "preparation_report.json")
    if report["data_kind"] != "real_collected" or report["completed_evidence_failures"]:
        raise ValueError("Real-data/evidence gate no longer passes")
    if (
        report["readiness"]["retrospective"]["mechanical_evaluation_status"]
        != "FEASIBLE_PRELIMINARY_ONLY"
    ):
        raise ValueError("Retrospective readiness is blocked")
    if report["readiness"]["prospective"]["mechanical_evaluation_status"] != "BLOCKED":
        raise ValueError("Unexpected prospective status; this run cannot change scope")
    for value in report["source_evidence"].values():
        if sha(Path(value["path"])) != value["sha256"]:
            raise ValueError("Original source evidence changed; stop before fitting")
    for name, expected in report["implementation_sha256"].items():
        if sha(Path(__file__).with_name(name)) != expected:
            raise ValueError(f"Approved preparation implementation changed: {name}")
    return report


def validate_snapshot(snapshot: Path) -> dict:
    """Re-run unchanged review, assessment, evidence and fixed-split guards."""
    snapshot = snapshot.resolve()
    report = check_inputs(snapshot)
    source = report["source_evidence"]
    tables, provenance = read_export(Path(source["export"]["path"]))
    frozen = read_json(Path(source["review_snapshot"]["path"]))
    baseline = CollectionReview.model_validate_json(
        Path(source["review_baseline"]["path"]).read_text(encoding="utf-8")
    )
    reviewed, _ = import_decisions(
        snapshot / "session_review_sheet.IMPORT_COMPATIBLE.csv",
        frozen,
        tables,
        provenance,
        baseline,
    )
    if reviewed.model_dump(mode="json") != read_json(
        snapshot / "imported_session_verification.json"
    ):
        raise ValueError("Verification decisions differ from approved snapshot")
    edited = read_sheet(Path(source["review_sheet"]["path"]), FIELDS)
    assessment_rows = read_sheet(
        Path(source["assessment_csv"]["path"]), (*FIELDS, *ASSESSMENT_FIELDS)
    )
    records = read_json(snapshot / "independent_assessments.input.json")["records"]
    resolutions = {
        r["student_code"]: r["score_level_resolution_reference"]
        for r in records
        if r["score_level_resolution_reference"]
    }
    assessments, _ = validate_assessments(
        assessment_rows,
        edited,
        frozen,
        source["assessment_csv"]["sha256"],
        baseline,
        resolutions,
    )
    if [item.model_dump(mode="json") for item in assessments.values()] != records:
        raise ValueError("Independent assessments/provenance changed")
    datasets, integrity, (decisions, _) = prepare_datasets(
        tables,
        provenance,
        reviewed,
        assessments,
        {r["game_session_id"] for r in edited},
    )
    if integrity["quarantine"] != read_json(snapshot / "integrity_quarantine.json"):
        raise ValueError("Integrity quarantines changed")
    config = ExperimentConfig.model_validate_json(json.dumps(report["configuration"]))
    for purpose, dataset in datasets.items():
        if dataset["observations"] != read_json(
            snapshot / purpose / "cleaned_observations.json"
        ):
            raise ValueError(f"{purpose} observations cannot be reproduced")
        for name, rows in dataset["features"].items():
            if rows != read_json(snapshot / purpose / f"{name}_features.json"):
                raise ValueError("Model A/B feature evidence changed")
        if (
            readiness(dataset, config, integrity, decisions)
            != report["readiness"][purpose]
        ):
            raise ValueError("Preparation readiness changed")
    # Train only rows loaded from the approved retrospective file, never a
    # rebuilt/relabeled cohort or the blocked prospective data.
    rows = read_json(snapshot / "retrospective/cleaned_observations.json")
    cohort = prepare_cohort(rows, config)
    split = learner_split(cohort, config)
    if (
        len(cohort.rows) != 30
        or len({r.student_code for r in cohort.rows}) != 16
        or cohort.exclusions
    ):
        raise ValueError("Approved retrospective cohort changed")
    if split.details != report["readiness"]["retrospective"]["fixed_grouped_split"]:
        raise ValueError("Fixed learner-grouped split changed")
    for partition in (split.train, split.test):
        labels_by_learner = defaultdict(set)
        for i in partition:
            labels_by_learner[cohort.rows[i].student_code].add(str(cohort.labels[i]))
        if any(len(values) != 1 for values in labels_by_learner.values()):
            raise ValueError(
                "Learner-level summaries need one independent target per learner"
            )
    return {
        "snapshot": snapshot,
        "report": report,
        "rows": rows,
        "config": config,
        "cohort": cohort,
        "split": split,
    }


def settings(base: ExperimentConfig) -> dict:
    result = {}
    for algorithm, parameters in PARAMETERS.items():
        value = base.model_dump(mode="json")
        value.update(classifier=algorithm, classifier_parameters=parameters)
        result[algorithm] = ExperimentConfig.model_validate_json(json.dumps(value))
    return result


def learner_summary(predictions: list[dict]) -> dict:
    grouped = defaultdict(list)
    for row in predictions:
        grouped[row["student_code"]].append(row)
    records = []
    for code, sessions in sorted(grouped.items()):
        actual = {row["actual"] for row in sessions}
        if len(actual) != 1:
            raise ValueError("Conflicting independent target classes for one learner")
        votes = Counter(row["predicted"] for row in sessions)
        if set(votes) - set(CLASSES) or actual - set(CLASSES):
            raise ValueError("Unknown proficiency class")
        prediction = max(CLASSES, key=lambda label: votes[label])
        records.append(
            {
                "student_code": code,
                "actual": actual.pop(),
                "predicted": prediction,
                "session_count": len(sessions),
                "session_predictions": sessions,
                "vote_counts": dict(votes),
            }
        )
    return {
        "aggregation": LEARNER_AGGREGATION,
        "independent_learners": len(records),
        "metrics": evaluate_research(
            np.asarray([r["actual"] for r in records]),
            np.asarray([r["predicted"] for r in records]),
            CLASSES,
        ),
        "predictions": records,
    }


def check_train_only_preprocessing(run, cohort, split) -> dict:
    spec = feature_set(run.metadata["feature_set"]["name"])
    train = research_frame(cohort.rows, spec).iloc[list(split.train)]
    expected = train.median().fillna(0).to_numpy()
    numeric = run.model.named_steps["preprocess"].named_transformers_["numeric"]
    imputer = numeric.named_steps["impute"]
    if not np.allclose(imputer.statistics_, expected):
        raise ValueError("Imputation statistics are not the training-only medians")
    scaler = numeric.named_steps.get("scale")
    if scaler is not None:
        imputed = imputer.transform(train)
        if not np.allclose(
            scaler.mean_, np.mean(imputed, axis=0)
        ) or scaler.n_samples_seen_ != len(split.train):
            raise ValueError("Scaling statistics are not training-only")
    return {
        "passed": True,
        "training_observations": len(train),
        "imputer_statistics": imputer.statistics_.tolist(),
        "entirely_missing_training_features": [
            key for key in train if train[key].isna().all()
        ],
        "numeric_preprocessing_steps": list(numeric.named_steps),
        "scaler_training_rows": int(scaler.n_samples_seen_)
        if scaler is not None
        else None,
    }


def load_real_artifact(
    path: Path, *, classifier: str, trusted_local_artifact: bool = False
):
    """Reject accidental synthetic/production bundles before pickle deserialization."""
    if not trusted_local_artifact:
        raise ValueError(
            "Explicit trust in this locally generated artifact is required"
        )
    metadata = read_json(path / "metadata.json")
    if (
        metadata.get("training_data", {}).get("kind") != "real_collected"
        or metadata.get("analysis_purpose") != "retrospective"
    ):
        raise ValueError("Only REAL_COLLECTED RETROSPECTIVE artifacts are accepted")
    if (
        metadata.get("status_flags") != list(FLAGS)
        or metadata.get("production_approved") is not False
    ):
        raise ValueError(
            "Required preliminary/non-production artifact flags are absent"
        )
    if metadata.get("approved_snapshot_manifest_sha256") != APPROVED_MANIFEST_SHA256:
        raise ValueError("Artifact was not trained from the approved snapshot")
    return load_research_artifact(
        path, target="mastery", classifier=classifier, trusted_local_artifact=True
    )


def offline_checks(path: Path, algorithm: str, cohort, split, run) -> dict:
    loaded = load_real_artifact(path, classifier=algorithm, trusted_local_artifact=True)
    predictions = []
    for index in split.test:
        row = cohort.rows[index].model_dump(mode="json")
        labeled = predict_research(loaded, row)
        row["mastery_label"] = row["difficulty_label"] = None
        result = predict_research(loaded, row)
        if result != labeled or result != predict_research(run, row):
            raise ValueError("Reload/label removal changed an offline prediction")
        if result["prediction"] not in CLASSES or set(
            result["class_probabilities"]
        ) != set(CLASSES):
            raise ValueError("Artifact returned unexpected class labels")
        if not np.isclose(sum(result["class_probabilities"].values()), 1):
            raise ValueError("Class probabilities do not sum to one")
        predictions.append(
            {
                "student_code": cohort.rows[index].student_code,
                "session_id": cohort.rows[index].session_id,
                "actual": str(cohort.labels[index]),
                "predicted": result["prediction"],
                "class_probabilities": result["class_probabilities"],
                "model_version": result["model_version"],
                "experiment_version": loaded.metadata["experiment_version"],
            }
        )
    invalid = cohort.rows[split.test[0]].model_dump(mode="json")
    invalid["teacher_score"] = 10  # invalid input probe, never an evaluation record
    try:
        predict_research(loaded, invalid)
    except ValueError:
        rejected = True
    else:
        raise ValueError("Input schema accepted an unapproved teacher-score feature")
    recorded = run.metadata["heldout_predictions"]
    if [r["predicted"] for r in predictions] != [r["predicted"] for r in recorded]:
        raise ValueError("Reloaded predictions differ from held-out evaluation")
    return {
        "status": "PASSED",
        "model_version": loaded.metadata["model_version"],
        "experiment_version": loaded.metadata["experiment_version"],
        "label_free_predictions_unchanged": True,
        "invalid_input_rejected": rejected,
        "feature_order": loaded.metadata["feature_names"],
        "missing_values_handled": loaded.metadata["missing_feature_counts"],
        "session_predictions": predictions,
        "learner_summary": learner_summary(predictions),
    }


def train(snapshot: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Experiment folder exists; choose a fresh version")
    if any(flag not in output.name for flag in FLAGS):
        raise ValueError(
            "Experiment directory must clearly contain all four status flags"
        )
    approved = validate_snapshot(snapshot)
    snapshot, cohort, split = (
        approved["snapshot"],
        approved["cohort"],
        approved["split"],
    )
    configs = settings(approved["config"])
    report = approved["report"]
    plan = {
        "experiment_version": output.name,
        "milestone": "2.4",
        "status_flags": list(FLAGS),
        "production_approved": False,
        "analysis_purpose": "retrospective",
        "declared_at_utc": datetime.now(UTC).isoformat(),
        "snapshot": str(snapshot),
        "snapshot_manifest_sha256": APPROVED_MANIFEST_SHA256,
        "observation_file_sha256": sha(
            snapshot / "retrospective/cleaned_observations.json"
        ),
        "canonical_dataset_sha256": cohort.dataset_sha256,
        "runner_sha256": sha(Path(__file__)),
        "runtime_versions": runtime_versions(),
        "configurations": {
            name: value.model_dump(mode="json") for name, value in configs.items()
        },
        "effective_parameters": {
            name: make_research_pipeline(value, feature_set("score_only"))
            .named_steps["classifier"]
            .get_params()
            for name, value in configs.items()
        },
        "feature_schemas": read_json(
            snapshot / "retrospective/feature_definitions.json"
        ),
        "fixed_split": split.details,
        "learner_aggregation": LEARNER_AGGREGATION,
        "selection_policy": "All six configurations reported. No winner, test-based tuning, seed search or full-cohort refit.",
        "missing_values": "Training-only median imputation with missing indicators; all-missing columns use existing zero fallback. LR additionally uses training-only standard scaling.",
    }
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / "experiment_plan.BEFORE_FITTING.json", plan)
    save_json(output / "approved_input_provenance.json", report)
    outcomes, baseline = {}, None
    for algorithm, config in configs.items():
        check_inputs(snapshot)
        comparison = run_comparison(
            approved["rows"],
            config,
            provenance=f"{STATUS}; approved snapshot {snapshot}; manifest SHA256={APPROVED_MANIFEST_SHA256}",
            data_kind="real_collected",
        )
        if comparison.report["split"] != split.details:
            raise ValueError("Training changed the fixed split")
        majority = Counter(cohort.labels[list(split.train)]).most_common(1)[0][0]
        baseline_predictions = [
            {
                "student_code": cohort.rows[i].student_code,
                "session_id": cohort.rows[i].session_id,
                "actual": str(cohort.labels[i]),
                "predicted": str(majority),
            }
            for i in split.test
        ]
        current_baseline = {
            "strategy": "most_frequent training-session class",
            "predicted_class": str(majority),
            "session_weighted": comparison.report["majority_class_baseline"],
            "learner_level": learner_summary(baseline_predictions),
        }
        if baseline is not None and baseline != current_baseline:
            raise ValueError("Shared baseline changed between algorithms")
        baseline = current_baseline
        for name, run in comparison.models.items():
            run.metadata.update(
                {
                    "status": STATUS,
                    "status_flags": list(FLAGS),
                    "analysis_purpose": "retrospective",
                    "production_approved": False,
                    "experiment_version": output.name,
                    "approved_snapshot_manifest_sha256": APPROVED_MANIFEST_SHA256,
                    "approved_observation_file_sha256": plan["observation_file_sha256"],
                    "preparation_snapshot": str(snapshot),
                    "source_evidence": report["source_evidence"],
                    "actual_assessment_timing": report[
                        "assessment_timing_eligible_retrospective"
                    ],
                    "target_interpretation": "Separate teacher-assessed mathematics proficiency, not Game/Quiz heuristics",
                    "prediction_cutoff": "Recorded gameplay window; retrospective association includes before/same-day/after teacher assessments. No prospective ordering guarantee.",
                    "preprocessing_audit": check_train_only_preprocessing(
                        run, cohort, split
                    ),
                }
            )
            if run.metadata["feature_names"] != list(feature_set(name).names):
                raise ValueError("Feature order changed")
            if set(run.model.classes_) != set(CLASSES):
                raise ValueError("Fitted model does not contain all three classes")
        comparison.report.update(
            status=STATUS,
            analysis_purpose="retrospective",
            production_approved=False,
            selection_policy=plan["selection_policy"],
        )
        destination = output / SHORT[algorithm]
        save_comparison(comparison, destination)
        outcomes[algorithm] = {}
        for name, run in comparison.models.items():
            checks = offline_checks(destination / name, algorithm, cohort, split, run)
            outcomes[algorithm][name] = {
                "artifact_path": str((destination / name).resolve()),
                "session_weighted": run.metadata["evaluation"],
                "offline_inference": checks,
                "preprocessing_audit": run.metadata["preprocessing_audit"],
            }
    check_inputs(snapshot)
    result = {
        "milestone": "2.4",
        "experiment_version": output.name,
        "status_flags": list(FLAGS),
        "training_status": "COMPLETED",
        "software_artifact_validation": "PASSED",
        "research_validation": "NOT_ESTABLISHED",
        "production_approved": False,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "models_trained": 6,
        "data_kind": "real_collected",
        "analysis_purpose": "retrospective",
        "approved_snapshot_manifest_sha256": APPROVED_MANIFEST_SHA256,
        "split": split.details,
        "baseline": baseline,
        "models": outcomes,
        "learner_class_distribution": report["readiness"]["retrospective"][
            "learner_class_distribution"
        ],
        "prospective_status": "BLOCKED_NOT_TRAINED",
        "selection_policy": plan["selection_policy"],
        "model_b_minus_a": {
            algorithm: {
                "session_macro_f1": results["score_plus_behaviour"]["session_weighted"][
                    "macro_f1"
                ]
                - results["score_only"]["session_weighted"]["macro_f1"],
                "learner_macro_f1": results["score_plus_behaviour"][
                    "offline_inference"
                ]["learner_summary"]["metrics"]["macro_f1"]
                - results["score_only"]["offline_inference"]["learner_summary"][
                    "metrics"
                ]["macro_f1"],
            }
            for algorithm, results in outcomes.items()
        },
    }
    save_json(output / "experiment_results.json", result)
    (output / "EXPERIMENT_REPORT.md").write_text(
        render_report(result, plan), encoding="utf-8"
    )
    with (output / "metrics.csv").open("x", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "algorithm",
                "feature_set",
                "aggregation",
                "macro_f1",
                "balanced_accuracy",
            ],
        )
        writer.writeheader()
        for algorithm, results in outcomes.items():
            for name, value in results.items():
                for aggregation, metrics in [
                    ("session_weighted", value["session_weighted"]),
                    (
                        "learner_level",
                        value["offline_inference"]["learner_summary"]["metrics"],
                    ),
                ]:
                    writer.writerow(
                        {
                            "algorithm": algorithm,
                            "feature_set": name,
                            "aggregation": aggregation,
                            **{
                                key: metrics[key]
                                for key in ("macro_f1", "balanced_accuracy")
                            },
                        }
                    )
    save_json(
        output / "experiment_manifest.json",
        {
            "complete": True,
            "status_flags": list(FLAGS),
            "production_approved": False,
            "files_sha256": {
                path.relative_to(output).as_posix(): sha(path)
                for path in sorted(output.rglob("*"))
                if path.is_file()
            },
            "hash_scope": "All experiment files except this manifest; trusted-local artifacts only, not a digital signature.",
        },
    )
    return result


def render_report(result: dict, plan: dict) -> str:
    lines = [
        "# Milestone 2.4 — REAL_COLLECTED RETROSPECTIVE preliminary experiment",
        "",
        "PRELIMINARY_EXPERIMENTAL — NOT_APPROVED_FOR_PRODUCTION",
        "",
        "Training completed for six configurations. Software/artifact checks passed. Research validity is not established.",
        "",
        f"Approved snapshot: `{plan['snapshot']}`.",
        f"Manifest SHA256: `{APPROVED_MANIFEST_SHA256}`.",
        "30 observations / 16 independent learners; unchanged seed-42 learner-grouped split.",
        "Train: 22 sessions / 12 learners (1 Beginner, 8 Intermediate, 3 Advanced learners).",
        "Test: 8 sessions / 4 learners (1 Beginner, 2 Intermediate, 1 Advanced learner).",
        "",
        "Model A uses audited first-attempt score only. Model B adds the existing 12 behaviour features; cohorts and targets are identical.",
        "Training-only median imputation; missing indicators/zero fallback for entirely missing columns; LR uses training-only standard scaling.",
        "LR: C=1, lbfgs, max_iter=2000. DT: max_depth=5, min_samples_leaf=2. RF: 100 trees, max_depth=6, min_samples_leaf=2, n_jobs=1. All seeds=42.",
        "",
        plan["selection_policy"],
        "",
        "## Metrics",
        "",
        "| Algorithm | Model | Session macro F1 | Session balanced accuracy | Learner macro F1 | Learner balanced accuracy |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for algorithm, models in result["models"].items():
        for name, item in models.items():
            a = item["session_weighted"]
            b = item["offline_inference"]["learner_summary"]["metrics"]
            lines.append(
                f"| {algorithm} | {'A' if name == 'score_only' else 'B'} | {a['macro_f1']:.4f} | {a['balanced_accuracy']:.4f} | {b['macro_f1']:.4f} | {b['balanced_accuracy']:.4f} |"
            )
    a = result["baseline"]["session_weighted"]
    b = result["baseline"]["learner_level"]["metrics"]
    lines += [
        f"| Majority training class | Baseline | {a['macro_f1']:.4f} | {a['balanced_accuracy']:.4f} | {b['macro_f1']:.4f} | {b['balanced_accuracy']:.4f} |",
        "",
        "Learner metrics give each held-out learner one vote. " + LEARNER_AGGREGATION,
        "Per-class precision/recall/F1/support, all session predictions, learner summaries and probabilities are in `experiment_results.json` and individual artifact metadata.",
        "",
        "## Model B minus A",
        "",
    ]
    for algorithm, delta in result["model_b_minus_a"].items():
        lines.append(
            f"- {algorithm}: session macro F1 {delta['session_macro_f1']:+.4f}; learner macro F1 {delta['learner_macro_f1']:+.4f}."
        )
    lines += [
        "",
        "## Confusion matrices",
        "",
        "Order: Beginner, Intermediate, Advanced. Rows are actual; columns predicted.",
        "",
    ]
    for algorithm, models in result["models"].items():
        for name, item in models.items():
            for kind, metrics in [
                ("session-weighted", item["session_weighted"]),
                (
                    "learner-level",
                    item["offline_inference"]["learner_summary"]["metrics"],
                ),
            ]:
                lines += [
                    f"### {algorithm} / {name} / {kind}",
                    "",
                    "```text",
                    *[" ".join(map(str, row)) for row in metrics["confusion_matrix"]],
                    "```",
                    "",
                ]
    for kind, metrics in [
        ("session-weighted", result["baseline"]["session_weighted"]),
        ("learner-level", result["baseline"]["learner_level"]["metrics"]),
    ]:
        lines += [
            f"### Majority baseline / {kind}",
            "",
            "```text",
            *[" ".join(map(str, row)) for row in metrics["confusion_matrix"]],
            "```",
            "",
        ]
    lines += [
        "## Per-held-out-learner predictions",
        "",
        "| Algorithm | Model | Learner | Actual | Sessions | Aggregated prediction |",
        "|---|---|---|---|---:|---|",
    ]
    for algorithm, models in result["models"].items():
        for name, item in models.items():
            for learner in item["offline_inference"]["learner_summary"]["predictions"]:
                lines.append(
                    f"| {algorithm} | {'A' if name == 'score_only' else 'B'} | {learner['student_code']} | {learner['actual']} | {learner['session_count']} | {learner['predicted']} |"
                )
    lines += ["", "## Saved artifacts and offline validation", ""]
    for algorithm, models in result["models"].items():
        for name, item in models.items():
            lines.append(
                f"- {algorithm} / {name}: `{item['artifact_path']}`; trusted-local reload, feature order, schema rejection, class/probability outputs, missing values and label-free predictions passed."
            )
    lines += [
        "",
        "## Interpretation and limitations",
        "",
        "These are exploratory comparisons on one shared test group. No algorithm or feature set is selected as a winner. Differences describe this split and cannot establish model superiority or statistical reliability.",
        "Only one independent Beginner learner appears in training, with one training session; the fitted three-class boundary has almost no independent Beginner coverage. Test observations repeat four learners, so eight sessions are not eight students.",
        "The retrospective set contains 9 before-assessment, 20 same-day-order-unknown and 1 after-assessment sessions. Results cannot establish prospective prediction or an AI Tutor treatment effect. Actual recorded phases and independent score provenance are preserved.",
        "Teacher sheets, exact assessment times, historical client/content builds, complete original payloads and reliable active durations remain unavailable. Recorded logical tie order is accepted under the audited policy; physical within-millisecond order and intentional distinct actions are not proven.",
        "The duration columns remain null and are imputed using the declared training-only fallback. Some behaviour predictors are constant or redundant in this complete-session cohort. Probabilities are uncalibrated.",
        "More independently labelled learners and an untouched external validation cohort are necessary. Synthetic observations were not used. Prospective training remains blocked and was not run.",
        "",
        "## Recommendation for Milestone 2.5",
        "",
        "Implement and test a local research-only FastAPI wrapper around the trusted-local loader and strict observation schema. Keep experimental inference disabled in deployed environments, require explicit approved researcher access, expose provenance/status/version, and keep research predictions separate from scoring and adaptive decisions. Use a separately declared configuration; do not choose a production model from this shared test set. Do not activate Railway inference or integrate student-facing predictions without separate review and validation.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = train(args.snapshot, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "training_status": result["training_status"],
                "models_trained": result["models_trained"],
                "production_approved": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
