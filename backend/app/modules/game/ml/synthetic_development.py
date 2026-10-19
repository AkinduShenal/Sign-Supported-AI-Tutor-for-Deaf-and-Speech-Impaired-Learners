"""Isolated SIM-only adapter and predefined-split experiments; no database imports."""

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from sklearn.dummy import DummyClassifier

from .research_artifacts import load_research_artifact, save_comparison
from .research_dataset import feature_set
from .research_inference import predict_research
from .research_schema import IndependentLabel, ResearchObservation
from .research_training import (
    ExperimentConfig,
    EvaluationConfig,
    ResearchComparison,
    ResearchSplit,
    distribution,
    evaluate_research,
    fit_experiment,
    prepare_cohort,
    research_frame,
    unit_digest,
)

DESIGNATION = "SYNTHETIC_DEVELOPMENT"
VERSION = "synthetic-game-200x2-adapter-v1"
CLASSES = ("beginner", "intermediate", "advanced")
PLACEHOLDER_DATE = "2000-01-01T00:00:00Z"
CSV_NAMES = (
    "synthetic_sessions_all",
    "synthetic_sessions_train",
    "synthetic_sessions_test",
    "synthetic_task_steps",
    "synthetic_independent_labels",
    "synthetic_learner_split",
)
MEMBERS = {
    *(name + ".csv" for name in CSV_NAMES),
    "README.md",
    "manifest.json",
    "checksums.sha256.json",
    "generate_synthetic_game_ml.py",
    "synthetic_observations_train.json",
    "synthetic_observations_test.json",
}
CONFIGURATIONS = {
    "logistic_regression": {"C": 1.0, "max_iter": 2000},
    "decision_tree": {"max_depth": 5, "min_samples_leaf": 3},
    "random_forest": {"n_estimators": 200, "max_depth": 8, "min_samples_leaf": 2},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(row, key):
    value = int(row[key])
    require(value >= 0, f"Negative {key}")
    return value


def close(actual, expected, tolerance=0.00000051):
    require(
        abs(float(actual) - expected) <= tolerance, "Aggregate/step evidence mismatch"
    )


@dataclass
class SyntheticDataset:
    observations: list[ResearchObservation]
    learner_split: dict[str, str]
    validation: dict
    source_members: dict[str, bytes]


def read_synthetic_archive(path: Path) -> SyntheticDataset:
    """Read fixed members, never extract paths or execute bundled instructions/code."""
    with ZipFile(path) as archive:
        names = archive.namelist()
        require(
            len(names) == len(set(names)) and set(names) == MEMBERS,
            "Unexpected/duplicate archive members",
        )
        require(
            all(info.file_size <= 10_000_000 for info in archive.infolist()),
            "Synthetic archive member too large",
        )
        contents = {name: archive.read(name) for name in names}
    checksums = json.loads(contents["checksums.sha256.json"])
    require(
        set(checksums)
        == MEMBERS - {"checksums.sha256.json", "generate_synthetic_game_ml.py"},
        "Checksum coverage differs from supplied format",
    )
    for name, expected in checksums.items():
        require(
            hashlib.sha256(contents[name]).hexdigest() == expected,
            f"Source checksum mismatch: {name}",
        )
    manifest = json.loads(contents["manifest.json"])
    require(
        manifest["data_kind"] == "synthetic_development"
        and manifest["contains_real_student_data"] is False
        and manifest["contains_teacher_assessment_results"] is False,
        "Only explicitly synthetic non-teacher data is accepted",
    )
    require(manifest["generator_seed"] == 20261016, "Unexpected generation seed")
    tables = {}
    for name in CSV_NAMES:
        reader = csv.DictReader(
            io.StringIO(contents[name + ".csv"].decode("utf-8-sig"))
        )
        require(
            len(reader.fieldnames or []) == len(set(reader.fieldnames or [])),
            "Duplicate CSV headers",
        )
        rows = list(reader)
        require(
            all(
                None not in row and all(v is not None for v in row.values())
                for row in rows
            ),
            "Malformed CSV rows",
        )
        tables[name] = rows
    sessions = tables["synthetic_sessions_all"]
    learners = {f"SIM_{i:03}" for i in range(1, 201)}
    require(
        len(sessions) == 400 and {r["student_code"] for r in sessions} == learners,
        "Need exactly 200 simulated learners / 400 sessions",
    )
    for rows in tables.values():
        for row in rows:
            require(
                row["student_code"] in learners, "Non-SIM or unknown learner identity"
            )
            if "data_kind" in row:
                require(row["data_kind"] == "synthetic_development", "Mixed data kinds")
    owners = {row["game_session_id"]: row for row in sessions}
    require(
        len(owners) == 400
        and all(re.fullmatch(r"SYN-SES-\d{3}-0[12]", sid) for sid in owners),
        "Duplicate/invalid synthetic session IDs",
    )
    for code in learners:
        modes = Counter(r["game_type"] for r in sessions if r["student_code"] == code)
        require(
            modes == {"drag_drop": 1, "hangman": 1},
            "Need one session of each mode per learner",
        )
    splits = tables["synthetic_learner_split"]
    labels = tables["synthetic_independent_labels"]
    require(len(splits) == len(labels) == 200, "Need one split and label per learner")
    split_map = {r["student_code"]: r["split"] for r in splits}
    label_map = {r["student_code"]: r for r in labels}
    require(
        set(split_map) == set(label_map) == learners,
        "Duplicate/missing learner label or split",
    )
    require(set(split_map.values()) == {"train", "test"}, "Invalid partition")
    for row in splits:
        label = label_map[row["student_code"]]
        require(
            label["split"] == row["split"]
            and label["independent_label"] == row["independent_label"],
            "Label/split disagreement",
        )
        require(
            label["independent_label"] in CLASSES
            and label["concept_id"] == "linear_equations"
            and label["independent_target"] == "mastery_label"
            and label["label_source"] == "simulated_latent_ability"
            and label["source_reference"] == "SYNTHETIC_GENERATOR"
            and label["rubric_version"] == "SIMULATED_v1"
            and not label["assessed_at"],
            "Unsupported/non-simulated label provenance",
        )
    require(
        dict(Counter(r["independent_label"] for r in labels))
        == manifest["class_counts"],
        "Manifest label distribution differs",
    )
    require(
        manifest["simulated_learners"] == 200
        and manifest["sessions"] == 400
        and manifest["sessions_per_learner"] == 2
        and set(manifest["game_types"]) == {"drag_drop", "hangman"},
        "Manifest counts differ",
    )
    for part, expected in (("train", 161), ("test", 39)):
        expected_rows = [r for r in sessions if split_map[r["student_code"]] == part]
        require(
            tables[f"synthetic_sessions_{part}"] == expected_rows,
            "Train/test CSV does not match supplied learner partition",
        )
        require(
            len(expected_rows) == expected * 2
            and manifest[f"{'training' if part == 'train' else 'test'}_learners"]
            == expected
            and manifest[f"{'training' if part == 'train' else 'test'}_sessions"]
            == expected * 2,
            "Manifest partition counts differ",
        )
        observed = json.loads(contents[f"synthetic_observations_{part}.json"])
        projected = []
        for r in expected_rows:
            projection = {
                k: r[k]
                for k in (
                    "student_code",
                    "game_session_id",
                    "concept_id",
                    "assessment_phase",
                    "game_type",
                    "independent_target",
                    "split",
                    "data_kind",
                )
                if k in r
            }
            projection.update(
                observation_id=r["game_session_id"],
                mastery_label=r["independent_label"],
                independent_target="mastery_label",
                label_source="simulated_latent_ability",
            )
            for key in (
                "wrong_attempt_count",
                "retry_count",
                "total_hint_count",
                "skipped_step_count",
                "first_attempt_correct_steps",
                "planned_steps",
            ):
                projection[key] = integer(r, key)
            for key in (
                "gameplay_score",
                "game_hint_rate",
                "game_completion_rate",
                "game_active_time_sec",
            ):
                projection[key] = float(r[key])
            projected.append(projection)
        require(
            observed == projected, "Convenience observations differ from source CSV"
        )
    steps = tables["synthetic_task_steps"]
    require(len(steps) == 3600, "Need all 3600 simulated answer steps")
    by_session = defaultdict(list)
    for row in steps:
        require(row["game_session_id"] in owners, "Orphan answer step")
        parent = owners[row["game_session_id"]]
        require(
            all(
                row[k] == parent[k]
                for k in ("student_code", "game_type", "concept_id", "split")
            ),
            "Step/session ownership or partition conflict",
        )
        by_session[row["game_session_id"]].append(row)
    observations = []
    hint_rate_corrections = 0
    for sid, session in owners.items():
        code = session["student_code"]
        require(
            session["split"] == split_map[code]
            and session["independent_label"] == label_map[code]["independent_label"]
            and session["concept_id"] == "linear_equations"
            and session["assessment_phase"] == "pre_tutor"
            and session["status"] == "completed"
            and session["provenance"] == "AI_SYNTHETIC_NOT_REAL_STUDENT"
            and integer(session, "generator_seed") == manifest["generator_seed"],
            "Session provenance/label/split conflict",
        )
        rows = by_session[sid]
        nsteps = 2 if session["game_type"] == "drag_drop" else 1
        tasks = defaultdict(list)
        for row in rows:
            tasks[row["task_id"]].append(row)
            first = integer(row, "first_attempt_correct")
            wrong = integer(row, "wrong_attempt_count")
            require(
                first in (0, 1)
                and ((first == 1 and wrong == 0) or (first == 0 and wrong >= 1))
                and integer(row, "retry_count") == wrong,
                "Invalid first-answer/retry evidence",
            )
            require(
                float(row["response_time_sec"]) > 0,
                "Invalid simulated response duration",
            )
            integer(row, "hint_count")
        require(
            set(tasks) == {f"{sid}-T{i:02}" for i in range(1, 7)},
            "Task roster mismatch",
        )
        difficulties = Counter()
        for task_rows in tasks.values():
            require(
                len(task_rows) == nsteps
                and {integer(r, "step_index") for r in task_rows}
                == set(range(1, nsteps + 1)),
                "Duplicate/missing answer steps",
            )
            require(
                len({r["difficulty_level"] for r in task_rows}) == 1,
                "Conflicting task difficulty",
            )
            difficulties[task_rows[0]["difficulty_level"]] += 1
        require(
            difficulties == {"easy": 2, "medium": 2, "hard": 2},
            "Difficulty roster mismatch",
        )
        first = sum(integer(r, "first_attempt_correct") for r in rows)
        wrong = sum(integer(r, "wrong_attempt_count") for r in rows)
        hints = sum(integer(r, "hint_count") for r in rows)
        hinted = sum(integer(r, "hint_count") > 0 for r in rows)
        duration = sum(round(float(r["response_time_sec"]) * 1000) for r in rows) / 1000
        completed = integer(session, "tasks_completed")
        require(
            integer(session, "tasks_total") == integer(session, "tasks_attempted") == 6
            and completed <= 6
            and integer(session, "planned_steps") == len(rows)
            and integer(session, "first_attempt_correct_steps") == first
            and integer(session, "wrong_attempt_count")
            == integer(session, "retry_count")
            == wrong
            and integer(session, "total_hint_count") == hints
            and integer(session, "skipped_step_count") == 6 - completed,
            "Session totals disagree with step evidence",
        )
        require(
            integer(session, "first_attempt_correct_tasks")
            == sum(
                all(integer(r, "first_attempt_correct") for r in group)
                for group in tasks.values()
            ),
            "First-correct task aggregate differs",
        )
        close(session["gameplay_score"], first / len(rows))
        close(session["game_hint_rate"], hints / len(rows))
        close(session["hinted_step_fraction"], min(hints, len(rows)) / len(rows))
        close(session["game_completion_rate"], completed / 6, 0.0000051)
        close(session["game_active_time_sec"], duration, len(rows) * 0.00051)
        close(
            session["avg_response_time_sec"],
            float(session["game_active_time_sec"]) / len(rows),
            0.0006,
        )
        start = datetime.fromisoformat(session["started_at"])
        end = datetime.fromisoformat(session["completed_at"])
        require(
            start.tzinfo is not None and end.tzinfo is not None,
            "Naive simulation clock",
        )
        close((end - start).total_seconds(), duration, len(rows) * 0.00051)
        hint_rate_corrections += (
            abs(hinted / len(rows) - float(session["hinted_step_fraction"]))
            > 0.00000051
        )
        label = IndependentLabel(
            student_code=code,
            session_id=sid,
            concept="linear_equations",
            assessment_phase="pre_tutor",
            value=label_map[code]["independent_label"],
            source="test",
            assessed_at=PLACEHOLDER_DATE,
            source_reference="SYNTHETIC_GENERATOR: latent label; test-fixture contract only; date is a placeholder; NOT teacher/quiz/test evidence",
            rubric_version="SIMULATED_v1",
            gameplay_independent=True,
        )
        observations.append(
            ResearchObservation(
                student_code=code,
                session_id=sid,
                concept="linear_equations",
                game_type=session["game_type"],
                activity_ids=sorted(tasks),
                assessment_phase="pre_tutor",
                observation_started_at=start,
                observation_ended_at=start + timedelta(seconds=duration),
                total_steps=len(rows),
                first_attempt_correct_steps=first,
                first_attempt_observation_complete=True,
                wrong_attempts=wrong,
                retry_count=wrong,
                hint_count=hints,
                steps_with_hints=hinted,
                hint_observation_complete=True,
                tasks_total=6,
                tasks_completed=completed,
                task_completed=completed == 6,
                skipped_steps=None,
                task_duration_seconds=duration,
                task_duration_reliable=True,
                difficulty_label=None,
                mastery_label=label,
            )
        )
    validation = {
        "designation": DESIGNATION,
        "dataset_version": VERSION,
        "manifest": manifest,
        "zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "member_sha256": {
            n: hashlib.sha256(b).hexdigest() for n, b in contents.items()
        },
        "learners": 200,
        "sessions": 400,
        "steps": 3600,
        "train_learners": 161,
        "test_learners": 39,
        "learner_overlap": 0,
        "hinted_fraction_corrections": hint_rate_corrections,
        "adapter_policies": [
            "Exact score reconstructed from step counts; rounded convenience score only validated.",
            "Hint rate uses distinct hinted steps, not total hint requests or a capped request count.",
            "skipped_step_count counts unfinished tasks; preserve raw field but skipped_steps remains null.",
            "Synthetic duration/window reconstructed from serialized step milliseconds, not measured human time.",
            "source=test and 2000-01-01 date are synthetic schema scaffolding; no real assessment occurred.",
            "All raw source members retained unchanged; no genuine data is loaded.",
        ],
    }
    return SyntheticDataset(observations, split_map, validation, contents)


def predefined_split(cohort, dataset, config):
    """Construct existing ResearchSplit directly; never invoke random splitting."""
    require(
        len(cohort.rows) >= config.evaluation.min_examples
        and len(dataset.learner_split) >= config.evaluation.min_learners,
        "Synthetic cohort below existing guardrails",
    )
    indices = {
        p: tuple(
            i
            for i, r in enumerate(cohort.rows)
            if dataset.learner_split[r.student_code] == p
        )
        for p in ("train", "test")
    }
    groups = {p: {cohort.rows[i].student_code for i in ix} for p, ix in indices.items()}
    require(not groups["train"] & groups["test"], "Learner leakage")
    details = {
        "method": "supplied_predefined_learner_split",
        "group": "student_code",
        "number_of_splits": 1,
        "train_test_learner_overlap": 0,
        "generator_seed": dataset.validation["manifest"]["generator_seed"],
    }
    for p, ix in indices.items():
        require(
            set(cohort.labels[list(ix)]) == set(config.class_labels),
            "Missing partition classes",
        )
        details[p] = {
            "observations": len(ix),
            "learners": len(groups[p]),
            "sessions": len(ix),
            "label_distribution": distribution(
                cohort.labels[list(ix)], config.class_labels
            ),
            "example_indices": list(ix),
            "unit_sha256": [unit_digest(cohort.rows[i]) for i in ix],
        }
    return ResearchSplit(indices["train"], indices["test"], details)


def predict_synthetic(run, row):
    require(
        run.metadata.get("designation") == DESIGNATION
        and run.metadata["training_data"]["kind"] == "synthetic_development",
        "Not a synthetic artifact",
    )
    code = (
        row.student_code
        if isinstance(row, ResearchObservation)
        else row["student_code"]
    )
    sid = row.session_id if isinstance(row, ResearchObservation) else row["session_id"]
    require(
        re.fullmatch(r"SIM_\d{3}", code) and sid.startswith("SYN-SES-"),
        "SIM-only inference",
    )
    return {**predict_research(run, row), "designation": DESIGNATION}


def train_synthetic(dataset, output: Path):
    require(
        DESIGNATION in str(output),
        "Output path must explicitly identify synthetic development",
    )
    require(
        dataset.validation.get("designation") == DESIGNATION
        and all(
            re.fullmatch(r"SIM_\d{3}", row.student_code)
            and row.session_id.startswith("SYN-SES-")
            and row.mastery_label is not None
            and row.mastery_label.source_reference.startswith("SYNTHETIC_GENERATOR:")
            for row in dataset.observations
        ),
        "Only synthetic SIM observations and simulated labels may enter this runner",
    )
    output.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")

    save("validation.json", dataset.validation)
    source = output / "source"
    source.mkdir()
    for name, data in dataset.source_members.items():
        with (source / name).open("xb") as stream:
            stream.write(data)
    save(
        "adapted_observations.json",
        [r.model_dump(mode="json") for r in dataset.observations],
    )
    reports, predictions = {}, []
    for classifier, parameters in CONFIGURATIONS.items():
        config = ExperimentConfig(
            target="mastery",
            class_labels=CLASSES,
            classifier=classifier,
            classifier_parameters=parameters,
            evaluation=EvaluationConfig(test_size=39 / 200),
        )
        cohort = prepare_cohort(dataset.observations, config)
        require(
            len(cohort.rows) == 400 and not cohort.exclusions,
            "Unexpected cohort exclusions",
        )
        split = predefined_split(cohort, dataset, config)
        runs = {}
        for name in ("score_only", "score_plus_behaviour"):
            run = fit_experiment(
                cohort,
                split,
                config,
                name,
                provenance=f"{DESIGNATION} ZIP {dataset.validation['zip_sha256']}",
                data_kind="synthetic_development",
            )
            run.metadata.update(
                designation=DESIGNATION,
                synthetic_dataset_version=VERSION,
                experiment_configuration=config.model_dump(mode="json"),
                adapter_policies=dataset.validation["adapter_policies"],
                target_definition="Simulated latent proficiency, NOT a real teacher/quiz/test assessment",
                source_validation=dataset.validation,
                prediction_cutoff="Synthetic session closure; latent class was generated before gameplay; no real assessment",
            )
            run.model.synthetic_development_designation_ = DESIGNATION
            spec = feature_set(name)
            train_frame = research_frame(cohort.rows, spec).iloc[list(split.train)]
            numeric = run.model.named_steps["preprocess"].named_transformers_["numeric"]
            imputer = numeric.named_steps["impute"]
            expected_medians = (
                train_frame[list(spec.numeric)].median().fillna(0).to_numpy()
            )
            require(
                np.allclose(imputer.statistics_, expected_medians),
                "Preprocessing did not use training medians",
            )
            if "scale" in numeric.named_steps:
                training_values = imputer.transform(train_frame[list(spec.numeric)])
                require(
                    np.allclose(
                        numeric.named_steps["scale"].mean_, training_values.mean(axis=0)
                    ),
                    "Scaler did not use training rows",
                )
            run.metadata["training_only_preprocessing_checks"] = {
                "training_medians_match": True,
                "training_scaler_mean_matches": True
                if "scale" in numeric.named_steps
                else None,
            }
            metric = run.metadata["evaluation"]
            metric["accuracy"] = float(
                np.mean(
                    [
                        r["actual"] == r["predicted"]
                        for r in run.metadata["heldout_predictions"]
                    ]
                )
            )
            runs[name] = run
        baseline = DummyClassifier(strategy="most_frequent")
        baseline.fit(np.zeros((len(split.train), 1)), cohort.labels[list(split.train)])
        truth = cohort.labels[list(split.test)]
        majority = baseline.predict(np.zeros((len(split.test), 1)))
        baseline_metrics = evaluate_research(truth, majority, CLASSES)
        baseline_metrics["accuracy"] = float(np.mean(truth == majority))
        delta = (
            runs["score_plus_behaviour"].metadata["evaluation"]["macro_f1"]
            - runs["score_only"].metadata["evaluation"]["macro_f1"]
        )
        report = {
            "designation": DESIGNATION,
            "status": "SYNTHETIC TEST RESULTS ONLY",
            "dataset_version": VERSION,
            "source_validation": dataset.validation,
            "runtime_versions": runs["score_only"].metadata["runtime_versions"],
            "feature_sets": {name: run.metadata["feature_set"] for name, run in runs.items()},
            "configuration": config.model_dump(mode="json"),
            "split": split.details,
            "models": {n: r.metadata["evaluation"] for n, r in runs.items()},
            "majority_class_baseline": baseline_metrics,
            "macro_f1_difference_b_minus_a": delta,
            "interpretation": "Comparison of generator assumptions, not real learner performance; no tuning on heldout learners",
        }
        for run in runs.values():
            run.metadata["synthetic_test_comparison"] = report
        destination = output / classifier
        save_comparison(ResearchComparison(runs, report), destination)
        for name, original in runs.items():
            loaded = load_research_artifact(
                destination / name,
                target="mastery",
                classifier=classifier,
                trusted_local_artifact=True,
            )
            require(
                loaded.metadata["feature_names"] == list(feature_set(name).names),
                "Feature order mismatch",
            )
            for i in split.test:
                row = cohort.rows[i].model_dump(mode="json")
                expected = predict_synthetic(original, row)
                row.update(mastery_label=None, difficulty_label=None)
                actual = predict_synthetic(loaded, row)
                require(actual == expected, "Reload/label-free inference differs")
                predictions.append(
                    {
                        "designation": DESIGNATION,
                        "algorithm": classifier,
                        "feature_set": name,
                        "student_code": row["student_code"],
                        "session_id": row["session_id"],
                        "actual": str(cohort.labels[i]),
                        **actual,
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
            predict_synthetic(loaded, missing)
        reports[classifier] = report
    save(
        "synthetic_test_results.json", {"designation": DESIGNATION, "reports": reports}
    )
    save("heldout_label_free_predictions.json", predictions)
    save(
        "offline_inference_checks.json",
        {
            "designation": DESIGNATION,
            "predictions": len(predictions),
            "saved_reload_matches": True,
            "label_free_matches": True,
            "feature_order_matches": True,
            "missing_behavior_handling": "passed",
        },
    )
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = train_synthetic(read_synthetic_archive(args.archive), args.output)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Synthetic-only experiment failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
