"""Milestone 2.4.1: pinned SYNTHETIC_DEVELOPMENT PP1 experiment, offline only.

The original archive is data, never executable input. No application settings,
real-data experiment or production inference route is imported here.
"""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .research_artifacts import load_research_artifact, save_comparison
from .research_dataset import feature_set
from .research_training import (
    EvaluationConfig,
    ExperimentConfig,
    ResearchComparison,
    evaluate_research,
    fit_experiment,
    prepare_cohort,
    research_frame,
)
from .synthetic_development import (
    CLASSES,
    CONFIGURATIONS,
    SyntheticDataset,
    predefined_split,
    predict_synthetic,
    read_synthetic_archive,
    require,
)
from .training import runtime_versions

ARCHIVE_SHA256 = "008171f3f1d5ae61762b9dd1997382bce2852ebebd7f05dc6bf6193123df49d4"
FLAGS = ("SYNTHETIC_DEVELOPMENT", "PP1_DEMO", "NOT_APPROVED_FOR_PRODUCTION")
STATUS = "_".join(FLAGS)
RESULT = "SYNTHETIC TEST RESULT"
SELECTION_NAMESPACE = "game-ml-2.4.1-pp1-90-v1|20261019"
FEATURE_SETS = ("score_only", "score_plus_behaviour")
VOTE_POLICY = "Majority of the two session predictions; ties use fixed class order beginner, intermediate, advanced. No label is used to break ties."


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def marked(**values):
    return {
        "designation": "SYNTHETIC_DEVELOPMENT",
        "data_kind": "synthetic_development",
        "status": STATUS,
        "status_flags": list(FLAGS),
        "production_approved": False,
        **values,
    }


def save_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def load_source(path):
    require(Path(path).is_file(), f"Required researcher archive missing: {path}")
    require(sha(path) == ARCHIVE_SHA256, "Researcher archive fingerprint changed")
    dataset = read_synthetic_archive(Path(path))
    require(
        dataset.validation["zip_sha256"] == ARCHIVE_SHA256,
        "Archive changed during validation",
    )
    return dataset


def audit_source(dataset):
    """Descriptive checks only; never fit a detector or optimize a selection."""
    labels = {}
    for row in dataset.observations:
        require(row.mastery_label is not None, "Missing simulated label")
        value = row.mastery_label.value
        require(
            labels.setdefault(row.student_code, value) == value,
            "Conflicting simulated labels",
        )
    counts = {
        part: dict(
            Counter(
                labels[code]
                for code, split in dataset.learner_split.items()
                if split == part
            )
        )
        for part in ("train", "test")
    }
    require(set(labels) == set(dataset.learner_split), "Missing learner assignments")
    score_ranges, score_sets = {}, {}
    for label in CLASSES:
        values = [
            row.gameplay_score
            for row in dataset.observations
            if row.mastery_label.value == label
        ]
        require(values, f"Missing simulated class: {label}")
        score_sets[label] = set(values)
        score_ranges[label] = {
            "minimum": min(values),
            "maximum": max(values),
            "distinct_scores": len(set(values)),
        }
    overlap = {
        f"{left}/{right}": sorted(score_sets[left] & score_sets[right])
        for index, left in enumerate(CLASSES)
        for right in CLASSES[index + 1 :]
    }
    specs = {name: list(feature_set(name).names) for name in FEATURE_SETS}
    require(specs["score_only"] == ["gameplay_score"], "Score-only contract changed")
    forbidden = {
        "student_code",
        "session_id",
        "independent_label",
        "mastery_label",
        "source_reference",
        "split",
        "generator_seed",
        "assessed_at",
        "game_type",
        "total_steps",
    }
    require(
        not forbidden.intersection(specs["score_plus_behaviour"]), "Predictor leakage"
    )
    require(
        all(overlap.values()),
        "Source score classes no longer overlap; inspect before fitting",
    )
    return marked(
        archive_validation=dataset.validation,
        learner_class_counts=dict(Counter(labels.values())),
        original_partition_learner_classes=counts,
        thirty_learners_per_class_available=all(
            sum(counts[p].get(c, 0) for p in counts) >= 30 for c in CLASSES
        ),
        score_distributions=score_ranges,
        shared_score_values_between_classes=overlap,
        predictor_allowlists=specs,
        excluded_predictors=sorted(forbidden),
        generator_audit={
            "method": "Inspected bundled generator as text; never executed or modified it in this milestone.",
            "seed": 20261016,
            "label_source": "simulated_latent_ability; labels assigned before gameplay, not independent teacher assessments",
            "ability_means": {"beginner": -1.1, "intermediate": 0.0, "advanced": 1.1},
            "ability_standard_deviation": 0.67,
            "mechanism": "Class-dependent Gaussian ability, difficulty/mode/task noise, Bernoulli correctness, simulated retries/hints/completion and lognormal timing; two modes per learner.",
            "identifier_method": "Classes shuffled before SIM IDs; identifiers, timestamps, labels, seed and partitions never enter predictor frames.",
            "risks": [
                "Features intentionally encode class-dependent generator assumptions. This is not independent empirical validation.",
                "Wrong attempts equal retries by construction; correlated/redundant features are retained under the shared audited allowlist.",
                "Both skipped-step features are entirely missing because raw skipped_step_count counts unfinished tasks; training-only zero fallback and missing indicators apply.",
                "Timings are invented simulation values; reconstructed millisecond durations are not measured learner response times.",
                "Shared score values and overlapping ranges rule out a direct universal score threshold in this archive, not all possible synthetic shortcuts.",
                "No generator rule, subset, feature allowlist or hyperparameter is changed in response to this audit or held-out performance.",
            ],
        },
    )


def select_demo(dataset):
    labels, sessions = {}, defaultdict(list)
    for row in dataset.observations:
        require(
            re.fullmatch(r"SIM_\d{3}", row.student_code) is not None
            and row.session_id.startswith("SYN-SES-"),
            "Non-synthetic identity",
        )
        require(
            row.mastery_label is not None
            and row.mastery_label.source_reference.startswith("SYNTHETIC_GENERATOR:"),
            "Non-synthetic target",
        )
        value = row.mastery_label.value
        require(
            value in CLASSES and labels.setdefault(row.student_code, value) == value,
            "Invalid learner label",
        )
        sessions[row.student_code].append(row)
    require(set(labels) == set(dataset.learner_split), "Learner/split mismatch")
    require(
        set(dataset.learner_split.values()) == {"train", "test"},
        "Unknown source partition",
    )
    chosen = []
    available = {part: {c: 0 for c in CLASSES} for part in ("train", "test")}
    for label in CLASSES:
        for part, count in (("train", 24), ("test", 6)):
            candidates = [
                code
                for code in labels
                if labels[code] == label and dataset.learner_split[code] == part
            ]
            available[part][label] = len(candidates)
            require(
                len(candidates) >= count,
                f"Cannot preserve fixed 24/6 allocation for {label}/{part}: {len(candidates)} available; do not relabel or move learners",
            )

            def rank(code):
                return hashlib.sha256(
                    f"{SELECTION_NAMESPACE}|{label}|{part}|{code}".encode()
                ).hexdigest()

            for code in sorted(candidates, key=lambda code: (rank(code), code))[:count]:
                rows = sessions[code]
                require(
                    len(rows) == 2
                    and {r.game_type for r in rows} == {"drag_drop", "hangman"},
                    "Selected learner lacks both intended sessions",
                )
                chosen.append(
                    {
                        "student_code": code,
                        "simulated_class": label,
                        "original_split": part,
                        "selection_sha256": rank(code),
                        "session_ids": sorted(r.session_id for r in rows),
                    }
                )
    chosen.sort(key=lambda item: item["student_code"])
    codes = {item["student_code"] for item in chosen}
    observations = sorted(
        (r for r in dataset.observations if r.student_code in codes),
        key=lambda r: (r.student_code, r.session_id),
    )
    require(
        len(codes) == 90 and len(observations) == 180, "Unexpected demonstration size"
    )
    require(len({r.session_id for r in observations}) == 180, "Duplicate session")
    report = marked(
        namespace=SELECTION_NAMESPACE,
        selection_method="Lowest SHA256(namespace|class|original_split|learner_id); 24 original train + 6 original test per class, no feature values or evaluation results used.",
        source_archive_sha256=dataset.validation["zip_sha256"],
        available_partition_learner_classes=available,
        selected_learners=90,
        selected_sessions=180,
        selected_learner_classes={c: 30 for c in CLASSES},
        train_learners=72,
        test_learners=18,
        train_sessions=144,
        test_sessions=36,
        train_learner_classes={c: 24 for c in CLASSES},
        test_learner_classes={c: 6 for c in CLASSES},
        moved_learners=0,
        train_test_learner_overlap=0,
        learners=chosen,
    )
    subset = SyntheticDataset(
        observations,
        {code: dataset.learner_split[code] for code in sorted(codes)},
        dataset.validation,
        dataset.source_members,
    )
    return subset, report


def configuration(classifier):
    return ExperimentConfig(
        target="mastery",
        class_labels=CLASSES,
        classifier=classifier,
        classifier_parameters=CONFIGURATIONS[classifier],
        common_context=(),
        evaluation=EvaluationConfig(test_size=18 / 90),
    )


def check_preprocessing(run, cohort, split):
    spec = feature_set(run.metadata["feature_set"]["name"])
    frame = research_frame(cohort.rows, spec).iloc[list(split.train)]
    numeric = run.model.named_steps["preprocess"].named_transformers_["numeric"]
    imputer = numeric.named_steps["impute"]
    require(
        np.allclose(imputer.statistics_, frame.median().fillna(0).to_numpy()),
        "Imputer not training-only",
    )
    scaler = numeric.named_steps.get("scale")
    if scaler is not None:
        require(
            np.allclose(scaler.mean_, imputer.transform(frame).mean(axis=0))
            and scaler.n_samples_seen_ == len(frame),
            "Scaler not training-only",
        )
    return marked(
        passed=True,
        training_observations=len(frame),
        imputer_statistics=imputer.statistics_.tolist(),
        entirely_missing_features=[
            column for column in frame if frame[column].isna().all()
        ],
        scaler_training_rows=int(scaler.n_samples_seen_)
        if scaler is not None
        else None,
    )


def learner_summary(predictions):
    grouped = defaultdict(list)
    for row in predictions:
        require(
            re.fullmatch(r"SIM_\d{3}", row["student_code"]) is not None,
            "Non-SIM learner prediction",
        )
        grouped[row["student_code"]].append(row)
    records = []
    for code, rows in sorted(grouped.items()):
        actual = {row["actual"] for row in rows}
        require(
            len(actual) == 1 and actual <= set(CLASSES),
            "Conflicting/invalid simulated labels",
        )
        votes = Counter(row["predicted"] for row in rows)
        require(set(votes) <= set(CLASSES), "Unknown prediction")
        predicted = max(CLASSES, key=lambda label: votes[label])
        records.append(
            marked(
                result_kind=RESULT,
                student_code=code,
                actual=next(iter(actual)),
                predicted=predicted,
                session_count=len(rows),
                votes=dict(votes),
                session_predictions=rows,
            )
        )
    require(bool(records), "No synthetic learner predictions")
    metrics = evaluate_research(
        np.asarray([r["actual"] for r in records]),
        np.asarray([r["predicted"] for r in records]),
        CLASSES,
    )
    return marked(
        result_kind=RESULT,
        aggregation=VOTE_POLICY,
        simulated_learners=len(records),
        metrics=metrics,
        predictions=records,
    )


def load_demo_artifact(path, *, classifier, trusted_local_artifact=False):
    """Explicit local trust and synthetic/nonproduction checks precede joblib load."""
    require(trusted_local_artifact is True, "Explicit trusted local artifact required")
    metadata = json.loads((Path(path) / "metadata.json").read_text(encoding="utf-8"))
    require(
        metadata.get("status_flags") == list(FLAGS)
        and metadata.get("production_approved") is False
        and metadata.get("status") == STATUS
        and metadata.get("designation") == "SYNTHETIC_DEVELOPMENT"
        and metadata.get("training_data", {}).get("kind") == "synthetic_development"
        and metadata.get("milestone") == "2.4.1",
        "Not a synthetic PP1 nonproduction artifact",
    )
    require(
        metadata.get("source_archive_sha256") == ARCHIVE_SHA256,
        "Wrong synthetic source archive",
    )
    run = load_research_artifact(
        path, target="mastery", classifier=classifier, trusted_local_artifact=True
    )
    require(
        getattr(run.model, "synthetic_pp1_status_", None) == STATUS,
        "Pipeline synthetic designation missing",
    )
    return run


def predict_demo(run, observation):
    require(
        run.metadata.get("status_flags") == list(FLAGS)
        and run.metadata.get("production_approved") is False,
        "Synthetic nonproduction flags required",
    )
    return {**predict_synthetic(run, observation), **marked(result_kind=RESULT)}


def inventory(root):
    return {
        p.relative_to(root).as_posix(): sha(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != "experiment_manifest.json"
    }


def write_report(output, audit, selection, results):
    lines = [
        "# Milestone 2.4.1 — SYNTHETIC_DEVELOPMENT PP1 demonstration",
        "",
        STATUS,
        "",
        "Every metric below is a **SYNTHETIC TEST RESULT**. These results measure generator assumptions, not real student proficiency prediction or educational accuracy.",
        "",
        "## Source and separation",
        "",
        f"Original researcher archive SHA256: `{ARCHIVE_SHA256}`. Original archive and all earlier exports are preserved. No genuine STU observations, teacher labels, real-data models or real held-out predictions were read into this experiment. The 16-learner / 30-session genuine retrospective experiment remains separate and unchanged.",
        "",
        "The supplied Python generator was inspected as text, not executed. Seed 20261016 assigns 67 Beginner, 67 Intermediate and 66 Advanced latent classes before gameplay. Class-dependent ability means -1.1/0/+1.1 (SD 0.67), difficulty/mode/task noise and stochastic correctness produce errors, retries, hints, completion and fabricated response times. Labels are simulated, not teacher assessments. See source_audit.json and the unchanged archived source members.",
        "",
        "## Cohort and partition",
        "",
        selection["selection_method"],
        "",
        "90 learners: 30 Beginner / 30 Intermediate / 30 Advanced; both Drag & Drop and Hangman retained for each learner, 180 schema-valid sessions. Training: 72 learners / 144 sessions (24 learners per class). Testing: 18 learners / 36 sessions (6 learners per class). Zero learner overlap and zero moved source assignments. selected_learners.json lists every ID, selection hash and session ID.",
        "",
        "This is a deterministic class-balanced demonstration subset, not a representative learner sample. Selection and all six settings were written to experiment_plan.BEFORE_FITTING.json before fitting. No seed search, tuning, generator change, outcome-based selection or final full-data refit.",
        "",
        "## Features, provenance and shortcuts",
        "",
        "Model A uses exact first-attempt gameplay score only. Model B adds the same existing 12 behaviour fields. Models use identical observations and targets. Identifiers, class/assessment fields, timestamps, mode, planned-step count, generator seed and split are excluded from predictor frames. Median imputation, missing indicators and Logistic Regression scaling are fitted only on 144 training sessions; checks saved in each bundle.",
        "",
        "The raw hint rate counts requests; distinct hinted steps are reconstructed from step rows. Raw skipped_step_count counts unfinished tasks, so both skipped-step features stay null. Simulated duration is reconstructed from serialized step milliseconds and is never measured human time. Original raw source remains unchanged. The schema's source=test / 2000-01-01 date is explicitly synthetic fixture scaffolding, not a real test, teacher label or actual assessment date; original blank dates and simulated label provenance are preserved.",
        "",
        "No direct ID or target-label field enters features. Class score ranges overlap and share exact scores. Nevertheless, ability, correctness and behaviours depend deliberately on latent class; wrong attempts equal retries by construction. The data is structurally artificial, so this audit cannot certify freedom from generator shortcuts or validate real generalization.",
        "",
        "## Fixed settings",
        "",
        "All classifiers use seed 42 and the existing pipeline. Settings retained from the prior synthetic development configuration (not chosen using genuine data or current held-out results): Logistic Regression C=1, max_iter=2000, lbfgs; Decision Tree max_depth=5, min_samples_leaf=3; Random Forest 200 trees, max_depth=8, min_samples_leaf=2, n_jobs=1. Original predefined partitions replace random splitting; existing minimum-size and class-coverage safeguards remain enabled.",
        "",
        "## SYNTHETIC TEST RESULT — session metrics",
        "",
        "36 held-out sessions, correlated within 18 simulated learners. Class order throughout: Beginner, Intermediate, Advanced; matrix rows actual, columns predicted. No winning model is selected.",
        "",
        "| Classifier | Model | Macro F1 | Balanced accuracy |",
        "|---|---|---:|---:|",
    ]
    for classifier, report in results["reports"].items():
        for name, model in report["models"].items():
            metric = model["session_metrics"]
            lines.append(
                f"| {classifier} | {'A' if name == 'score_only' else 'B'} | {metric['macro_f1']:.6f} | {metric['balanced_accuracy']:.6f} |"
            )
    base = results["majority_class_baseline"]
    metric = base["session_metrics"]
    lines += [
        "",
        f"SYNTHETIC TEST RESULT — majority baseline: predict `{base['predicted_class']}` using training counts only; class ties resolved by fixed rubric order. Macro F1 {metric['macro_f1']:.6f}, balanced accuracy {metric['balanced_accuracy']:.6f}.",
        "",
        "## SYNTHETIC TEST RESULT — Model B minus A",
        "",
        "| Classifier | Macro F1 difference | Balanced accuracy difference |",
        "|---|---:|---:|",
    ]
    for classifier, report in results["reports"].items():
        delta = report["b_minus_a"]
        lines.append(
            f"| {classifier} | {delta['macro_f1']:+.6f} | {delta['balanced_accuracy']:+.6f} |"
        )
    lines += [
        "",
        "## SYNTHETIC TEST RESULT — per-class precision, recall and confusion matrices",
        "",
    ]
    for classifier, report in results["reports"].items():
        for name, model in report["models"].items():
            metric = model["session_metrics"]
            lines += [
                f"### SYNTHETIC TEST RESULT — {classifier} / {name}",
                "",
                "| Class | Precision | Recall | F1 | Support |",
                "|---|---:|---:|---:|---:|",
            ]
            for label, values in metric["per_class"].items():
                lines.append(
                    f"| {label} | {values['precision']:.6f} | {values['recall']:.6f} | {values['f1']:.6f} | {values['support']} |"
                )
            lines += [
                "",
                "```text",
                *[str(row) for row in metric["confusion_matrix"]],
                "```",
                "",
            ]
    lines += [
        "Majority baseline SYNTHETIC TEST RESULT confusion matrix (same axes):",
        "",
        "```text",
        *[str(row) for row in base["session_metrics"]["confusion_matrix"]],
        "```",
        "",
        "## SYNTHETIC TEST RESULT — learner evaluation",
        "",
        VOTE_POLICY,
        "",
        "| Classifier | Model | Learners | Macro F1 | Balanced accuracy |",
        "|---|---|---:|---:|---:|",
    ]
    for classifier, report in results["reports"].items():
        for name, model in report["models"].items():
            learner = model["learner_evaluation"]
            lines.append(
                f"| {classifier} | {'A' if name == 'score_only' else 'B'} | {learner['simulated_learners']} | {learner['metrics']['macro_f1']:.6f} | {learner['metrics']['balanced_accuracy']:.6f} |"
            )
    lines += [
        "",
        "synthetic_test_results.json contains complete learner predictions, per-class learner metrics and learner confusion matrices, plus baseline learner evaluation. heldout_label_free_predictions.json contains all 216 session predictions and class probabilities. Predictions are labeled SYNTHETIC TEST RESULT.",
        "",
        "## Offline inference",
        "",
        "Six newly saved trusted-local bundles were reloaded with schema/runtime/checksum checks and synthetic/nonproduction metadata guards. Predictions on all 36 held-out synthetic observations per model match in-memory results after removing both label objects. Feature order and missing-behaviour probes pass. No API or student-facing Game integration exists. See offline_inference_checks.json and OFFLINE_INFERENCE.md for a no-training command.",
        "",
        "## Limitations and next collection",
        "",
        "This balanced artificial subset does not validate real student proficiency prediction, Model B superiority, fairness, educational benefit or production readiness. Its 180 sessions represent 90 simulated learners; the test has only 18 independent simulated learners. One source seed and two tasks modes cannot represent the range of actual school behaviour. Past synthetic development work has already evaluated this archive's original held-out partition, so it is a demonstration holdout, not a fresh confirmatory test.",
        "",
        "Keep the existing genuine 16-learner experiment separately marked NOT_APPROVED_FOR_PRODUCTION. Future genuine work needs more independently assessed learners across all proficiency classes, verified learner/session access and identity, completed evidence-valid gameplay, recorded content/intervention provenance and known assessment ordering. Collect prospective observations before independently timed assessments; preserve existing quarantines and exclusions. Pre-register learner-disjoint evaluation and reserve a genuinely untouched test cohort. Repeated sessions do not substitute for additional independent learners. No new collection, production access or genuine training is performed here.",
        "",
        "## Preservation and reproduction",
        "",
        "experiment_manifest.json records artifact hashes and fresh-directory completion. Refusing existing output names provides snapshot discipline and tamper detection, not OS write protection or a digital signature. Source members are byte copies under this explicitly synthetic nonproduction directory. No original archive, prior synthetic experiment or genuine artifact is overwritten.",
        "",
        "From backend, choose a fresh output directory:",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe -B -m app.modules.game.ml.synthetic_pp1 train `",
        '  --archive "C:\\Users\\new user\\Downloads\\synthetic_game_ml_200x2.zip" `',
        '  --output "..\\exports\\' + STATUS + '-2.4.1-new-run"',
        "```",
        "",
    ]
    with (output / "PP1_REPORT.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines))


def train_demo(archive, output):
    archive, output = Path(archive).resolve(), Path(output).resolve()
    require(STATUS in output.name, f"Output directory must contain {STATUS}")
    require(not output.exists(), "Immutable output directory already exists")
    prior_exports = Path(__file__).resolve().parents[5] / "exports"
    preserved = {
        str(path.resolve()): sha(path)
        for path in sorted(prior_exports.rglob("*"))
        if path.is_file()
    }
    source = load_source(archive)
    audit = audit_source(source)
    dataset, selection = select_demo(source)
    configs = {classifier: configuration(classifier) for classifier in CONFIGURATIONS}
    cohort = prepare_cohort(dataset.observations, next(iter(configs.values())))
    require(
        len(cohort.rows) == 180 and not cohort.exclusions,
        "Unexpected demonstration exclusions",
    )
    split = predefined_split(cohort, dataset, next(iter(configs.values())))
    require(
        len(split.train) == 144 and len(split.test) == 36,
        "Source partition counts differ",
    )
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / "source_audit.json", audit)
    save_json(output / "selected_learners.json", selection)
    save_json(
        output / "adapted_observations.json",
        marked(observations=[r.model_dump(mode="json") for r in cohort.rows]),
    )
    source_dir = output / "source"
    source_dir.mkdir()
    for name, content in source.source_members.items():
        with (source_dir / name).open("xb") as stream:
            stream.write(content)
    implementations = {
        path.name: sha(path) for path in Path(__file__).parent.glob("*.py")
    }
    plan = marked(
        milestone="2.4.1",
        written_before_fitting_at_utc=datetime.now(UTC).isoformat(),
        archive_path=str(archive),
        archive_sha256=ARCHIVE_SHA256,
        selected_learners_sha256=sha(output / "selected_learners.json"),
        adapted_observations_sha256=sha(output / "adapted_observations.json"),
        source_audit_sha256=sha(output / "source_audit.json"),
        implementation_sha256=implementations,
        runtime_versions=runtime_versions(),
        configurations={
            key: value.model_dump(mode="json") for key, value in configs.items()
        },
        features={name: list(feature_set(name).names) for name in FEATURE_SETS},
        split=split.details,
        selection_namespace=SELECTION_NAMESPACE,
        learner_vote_policy=VOTE_POLICY,
        majority_baseline_policy="Training labels only; majority ties use fixed class order beginner, intermediate, advanced.",
        fitting_policy="Exactly six fits on the source training partition; no tuning, model selection or full-cohort refit; zero genuine observations.",
    )
    save_json(output / "experiment_plan.BEFORE_FITTING.json", plan)
    plan_hash = sha(output / "experiment_plan.BEFORE_FITTING.json")
    counts = Counter(str(cohort.labels[i]) for i in split.train)
    majority = max(CLASSES, key=lambda label: counts[label])
    baseline_rows = [
        marked(
            result_kind=RESULT,
            student_code=cohort.rows[i].student_code,
            session_id=cohort.rows[i].session_id,
            actual=str(cohort.labels[i]),
            predicted=majority,
        )
        for i in split.test
    ]
    baseline = marked(
        result_kind=RESULT,
        predicted_class=majority,
        training_class_counts=dict(counts),
        session_metrics=evaluate_research(
            cohort.labels[list(split.test)],
            np.repeat(majority, len(split.test)),
            CLASSES,
        ),
        learner_evaluation=learner_summary(baseline_rows),
    )
    reports, all_predictions, reloads = {}, [], []
    for classifier, config in configs.items():
        runs, model_results = {}, {}
        for name in FEATURE_SETS:
            run = fit_experiment(
                cohort,
                split,
                config,
                name,
                provenance=f"{STATUS}; original ZIP SHA256 {ARCHIVE_SHA256}; {SELECTION_NAMESPACE}",
                data_kind="synthetic_development",
            )
            run.metadata.update(
                marked(
                    milestone="2.4.1",
                    result_kind=RESULT,
                    source_archive_sha256=ARCHIVE_SHA256,
                    experiment_plan_sha256=plan_hash,
                    experiment_configuration=config.model_dump(mode="json"),
                    selection=selection,
                    adapter_policies=source.validation["adapter_policies"],
                    target_definition="Simulated latent proficiency; NOT real teacher, Game heuristic or Quiz assessment labels",
                    prediction_cutoff="Synthetic session closure; latent class assigned before simulated gameplay; no real assessment timing",
                )
            )
            run.metadata["evaluation"] = {
                **run.metadata["evaluation"],
                **marked(result_kind=RESULT),
            }
            run.metadata["heldout_predictions"] = [
                {**r, **marked(result_kind=RESULT)}
                for r in run.metadata["heldout_predictions"]
            ]
            run.metadata["training_only_preprocessing_checks"] = check_preprocessing(
                run, cohort, split
            )
            run.model.synthetic_development_designation_ = "SYNTHETIC_DEVELOPMENT"
            run.model.synthetic_pp1_status_ = STATUS
            session_records = []
            for i in split.test:
                row = cohort.rows[i]
                predicted = predict_demo(run, row)
                session_records.append(
                    marked(
                        result_kind=RESULT,
                        student_code=row.student_code,
                        session_id=row.session_id,
                        actual=str(cohort.labels[i]),
                        predicted=predicted["prediction"],
                        class_probabilities=predicted["class_probabilities"],
                    )
                )
            model_results[name] = marked(
                result_kind=RESULT,
                session_metrics=run.metadata["evaluation"],
                session_predictions=session_records,
                learner_evaluation=learner_summary(session_records),
            )
            runs[name] = run
        deltas = {
            metric: model_results["score_plus_behaviour"]["session_metrics"][metric]
            - model_results["score_only"]["session_metrics"][metric]
            for metric in ("macro_f1", "balanced_accuracy")
        }
        report = marked(
            result_kind=RESULT,
            classifier=classifier,
            split=split.details,
            models=model_results,
            majority_class_baseline=baseline,
            b_minus_a=deltas,
        )
        save_comparison(ResearchComparison(runs, report), output / classifier)
        for name, run in runs.items():
            bundle = output / classifier / name
            loaded = load_demo_artifact(
                bundle, classifier=classifier, trusted_local_artifact=True
            )
            require(
                loaded.metadata["feature_names"] == list(feature_set(name).names),
                "Feature order changed",
            )
            for i in split.test:
                original = cohort.rows[i]
                row = original.model_dump(mode="json")
                row.update(mastery_label=None, difficulty_label=None)
                expected, actual = (
                    predict_demo(run, original),
                    predict_demo(loaded, row),
                )
                require(actual == expected, "Reload or label-free prediction changed")
                all_predictions.append(
                    {
                        **actual,
                        "algorithm": classifier,
                        "student_code": row["student_code"],
                        "session_id": row["session_id"],
                        "actual_simulated_class": str(cohort.labels[i]),
                    }
                )
            missing = cohort.rows[split.test[0]].model_dump(mode="json")
            missing.update(
                mastery_label=None,
                difficulty_label=None,
                wrong_attempts=None,
                retry_count=None,
                hint_count=None,
                steps_with_hints=None,
                hint_observation_complete=False,
                task_duration_seconds=None,
                task_duration_reliable=False,
            )
            predict_demo(loaded, missing)
            reloads.append(
                marked(
                    result_kind=RESULT,
                    classifier=classifier,
                    feature_set=name,
                    heldout_label_free_matches=36,
                    feature_order_matches=True,
                    missing_behaviour_probe_passed=True,
                    training_only_preprocessing=run.metadata[
                        "training_only_preprocessing_checks"
                    ],
                )
            )
        reports[classifier] = report
    results = marked(
        result_kind=RESULT,
        selection_summary={
            key: value for key, value in selection.items() if key != "learners"
        },
        majority_class_baseline=baseline,
        reports=reports,
    )
    save_json(output / "synthetic_test_results.json", results)
    save_json(
        output / "heldout_label_free_predictions.json",
        marked(result_kind=RESULT, predictions=all_predictions),
    )
    save_json(
        output / "offline_inference_checks.json",
        marked(
            result_kind=RESULT,
            predictions_checked=len(all_predictions),
            models=reloads,
            database_access=False,
            production_api_changes=False,
        ),
    )
    with (output / "metrics.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "designation",
                "production_status",
                "result_kind",
                "algorithm",
                "model",
                "unit",
                "macro_f1",
                "balanced_accuracy",
            ]
        )
        for classifier, report in reports.items():
            for name, model in report["models"].items():
                for unit, metrics in (
                    ("session", model["session_metrics"]),
                    ("learner", model["learner_evaluation"]["metrics"]),
                ):
                    writer.writerow(
                        [
                            "SYNTHETIC_DEVELOPMENT",
                            "NOT_APPROVED_FOR_PRODUCTION",
                            RESULT,
                            classifier,
                            name,
                            unit,
                            metrics["macro_f1"],
                            metrics["balanced_accuracy"],
                        ]
                    )
        for unit, metric in (
            ("session", baseline["session_metrics"]),
            ("learner", baseline["learner_evaluation"]["metrics"]),
        ):
            writer.writerow(
                [
                    "SYNTHETIC_DEVELOPMENT",
                    "NOT_APPROVED_FOR_PRODUCTION",
                    RESULT,
                    "majority_baseline",
                    "training_majority",
                    unit,
                    metric["macro_f1"],
                    metric["balanced_accuracy"],
                ]
            )
    write_report(output, audit, selection, results)
    instruction = f"""# SYNTHETIC_DEVELOPMENT offline PP1 inference

{STATUS}

SYNTHETIC TEST RESULT only. From `backend`, reload the six locally generated
bundles and predict the saved 36 held-out synthetic sessions per model without
training or using labels as features:

```powershell
.\\.venv\\Scripts\\python.exe -B -m app.modules.game.ml.synthetic_pp1 infer `
  --experiment "..\\exports\\{output.name}" `
  --trusted-local-artifacts
```

Only use that trust flag for your own locally generated bundles. Joblib can
execute code; manifests detect changes but do not authenticate an untrusted
download. This command verifies the complete experiment, flags, original
partition, feature allowlist and runtime/hash contracts, removes both label
objects, and prints the same 216 SYNTHETIC TEST RESULT predictions. It neither
trains nor writes artifacts. Do not connect these models to production APIs or
student-facing Game results. Source labels are simulated, never teacher labels.
"""
    with (output / "OFFLINE_INFERENCE.md").open("x", encoding="utf-8") as stream:
        stream.write(instruction)
    require(
        sha(archive) == ARCHIVE_SHA256, "Original archive changed during experiment"
    )
    require(
        sha(output / "experiment_plan.BEFORE_FITTING.json") == plan_hash,
        "Frozen prefit plan changed",
    )
    require(
        all(
            Path(path).is_file() and sha(path) == expected
            for path, expected in preserved.items()
        ),
        "A pre-existing export changed during the synthetic experiment",
    )
    save_json(
        output / "prior_exports_preservation.json",
        marked(
            purpose="SHA256 preservation only; no genuine observations, labels, predictions or models used in this experiment",
            all_preexisting_export_files_unchanged=True,
            checked_files=len(preserved),
            files_sha256=preserved,
        ),
    )
    require(
        all(
            sha(Path(__file__).with_name(name)) == expected
            for name, expected in implementations.items()
        ),
        "Implementation changed during fitting",
    )
    save_json(
        output / "experiment_manifest.json",
        marked(
            milestone="2.4.1",
            complete=True,
            models_trained=6,
            source_archive_sha256=ARCHIVE_SHA256,
            files_sha256=inventory(output),
        ),
    )
    return results


def verify_experiment(output):
    output = Path(output).resolve()
    require(STATUS in output.name, "Synthetic nonproduction experiment path required")
    manifest = json.loads(
        (output / "experiment_manifest.json").read_text(encoding="utf-8")
    )
    require(
        manifest.get("complete") is True
        and manifest.get("status_flags") == list(FLAGS)
        and manifest.get("production_approved") is False
        and manifest.get("milestone") == "2.4.1"
        and manifest.get("models_trained") == 6
        and manifest.get("source_archive_sha256") == ARCHIVE_SHA256,
        "Incomplete or incompatible PP1 experiment",
    )
    require(
        inventory(output) == manifest["files_sha256"],
        "Experiment members or checksums changed",
    )
    return manifest


def infer_demo(output, *, trusted_local_artifacts=False):
    require(
        trusted_local_artifacts is True, "Explicit trusted local artifacts required"
    )
    output = Path(output).resolve()
    verify_experiment(output)
    rows = json.loads(
        (output / "adapted_observations.json").read_text(encoding="utf-8")
    )["observations"]
    selection = json.loads(
        (output / "selected_learners.json").read_text(encoding="utf-8")
    )
    heldout = {
        r["student_code"]
        for r in selection["learners"]
        if r["original_split"] == "test"
    }
    expected = json.loads(
        (output / "heldout_label_free_predictions.json").read_text(encoding="utf-8")
    )["predictions"]
    expected_map = {
        (p["algorithm"], p["feature_set"], p["session_id"]): p for p in expected
    }
    predictions = []
    for classifier in CONFIGURATIONS:
        for name in FEATURE_SETS:
            run = load_demo_artifact(
                output / classifier / name,
                classifier=classifier,
                trusted_local_artifact=True,
            )
            for row in rows:
                if row["student_code"] not in heldout:
                    continue
                label_free = {**row, "mastery_label": None, "difficulty_label": None}
                actual = predict_demo(run, label_free)
                reference = expected_map[(classifier, name, row["session_id"])]
                require(
                    actual["prediction"] == reference["prediction"]
                    and actual["class_probabilities"]
                    == reference["class_probabilities"],
                    "Saved synthetic inference changed",
                )
                predictions.append(
                    {
                        **actual,
                        "algorithm": classifier,
                        "student_code": row["student_code"],
                        "session_id": row["session_id"],
                    }
                )
    require(
        len(predictions) == 216 and len(heldout) == 18,
        "Held-out demonstration size changed",
    )
    return marked(
        result_kind=RESULT,
        predictions=predictions,
        predictions_checked=216,
        models_loaded=6,
        fits_performed=0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train", help="Fit exactly six synthetic PP1 models")
    train.add_argument("--archive", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    infer = commands.add_parser(
        "infer", help="Trusted-local synthetic inference; no training or writes"
    )
    infer.add_argument("--experiment", type=Path, required=True)
    infer.add_argument("--trusted-local-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "train":
            result = train_demo(args.archive, args.output)
            print(
                json.dumps(
                    marked(
                        result_kind=RESULT,
                        experiment=str(args.output),
                        selected_learners=90,
                        sessions=180,
                        models_trained=6,
                        reports={
                            c: {
                                n: model["session_metrics"]
                                for n, model in r["models"].items()
                            }
                            for c, r in result["reports"].items()
                        },
                    ),
                    indent=2,
                )
            )
        else:
            print(
                json.dumps(
                    infer_demo(
                        args.experiment,
                        trusted_local_artifacts=args.trusted_local_artifacts,
                    ),
                    indent=2,
                )
            )
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Synthetic PP1 demonstration stopped: {error}\n")


if __name__ == "__main__":
    main()
