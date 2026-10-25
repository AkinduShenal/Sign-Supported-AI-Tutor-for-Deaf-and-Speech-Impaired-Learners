"""Portable invented SIM fixtures only; no school data or database access."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from zipfile import ZipFile

import pytest

from app.modules.game.ml.research_dataset import extract_research_features
from app.modules.game.ml.research_training import ExperimentConfig, prepare_cohort
from app.modules.game.ml.synthetic_development import (
    CLASSES,
    DESIGNATION,
    predefined_split,
    read_synthetic_archive,
    train_synthetic,
)


def pack(path, tables, manifest, observations):
    contents = {
        "manifest.json": json.dumps(manifest).encode(),
        "README.md": b"SYNTHETIC DEVELOPMENT fixture only",
        "generate_synthetic_game_ml.py": b"raise RuntimeError('Never execute fixture source')\n",
    }
    for name, rows in tables.items():
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        contents[name + ".csv"] = stream.getvalue().encode()
    for part, rows in observations.items():
        contents[f"synthetic_observations_{part}.json"] = json.dumps(rows).encode()
    contents["checksums.sha256.json"] = json.dumps(
        {
            n: hashlib.sha256(data).hexdigest()
            for n, data in contents.items()
            if n != "generate_synthetic_game_ml.py"
        }
    ).encode()
    with ZipFile(path, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return path


@pytest.fixture
def fixture_data(tmp_path):
    sessions, steps, labels, splits = [], [], [], []
    observations = {"train": [], "test": []}
    class_index = {level: 0 for level in CLASSES}
    for i in range(200):
        code = f"SIM_{i + 1:03}"
        level = "beginner" if i < 67 else ("intermediate" if i < 134 else "advanced")
        part = "test" if class_index[level] < 13 else "train"
        class_index[level] += 1
        labels.append(
            dict(
                student_code=code,
                concept_id="linear_equations",
                independent_target="mastery_label",
                independent_label=level,
                label_source="simulated_latent_ability",
                source_reference="SYNTHETIC_GENERATOR",
                assessed_at="",
                rubric_version="SIMULATED_v1",
                data_kind="synthetic_development",
                split=part,
            )
        )
        splits.append(dict(student_code=code, split=part, independent_label=level))
        for number, mode in enumerate(("drag_drop", "hangman"), 1):
            sid = f"SYN-SES-{i:03}-{number:02}"
            n = 2 if mode == "drag_drop" else 1
            start = datetime(2026, 10, 1, tzinfo=UTC)
            for task in range(6):
                for index in range(1, n + 1):
                    wrong = int(task == 0 and index == 1)
                    steps.append(
                        dict(
                            game_session_id=sid,
                            student_code=code,
                            game_type=mode,
                            concept_id="linear_equations",
                            task_id=f"{sid}-T{task + 1:02}",
                            difficulty_level=("easy", "medium", "hard")[task // 2],
                            step_index=index,
                            first_attempt_correct=1 - wrong,
                            wrong_attempt_count=wrong,
                            retry_count=wrong,
                            hint_count=2 * wrong,
                            response_time_sec=1.0,
                            simulated_correct_response="SYNTHETIC",
                            split=part,
                            data_kind="synthetic_development",
                        )
                    )
            row = dict(
                game_session_id=sid,
                student_code=code,
                game_type=mode,
                concept_id="linear_equations",
                assessment_phase="pre_tutor",
                status="completed",
                tasks_total=6,
                tasks_attempted=6,
                tasks_completed=5,
                game_completion_rate=round(5 / 6, 5),
                first_attempt_correct_steps=6 * n - 1,
                planned_steps=6 * n,
                gameplay_score=round((6 * n - 1) / (6 * n), 6),
                wrong_attempt_count=1,
                retry_count=1,
                total_hint_count=2,
                game_hint_rate=round(2 / (6 * n), 6),
                hinted_step_fraction=round(2 / (6 * n), 6),
                skipped_step_count=1,
                game_active_time_sec=float(6 * n),
                avg_response_time_sec=1.0,
                first_attempt_correct_tasks=5,
                started_at=start.isoformat(),
                completed_at=(start + timedelta(seconds=6 * n)).isoformat(),
                independent_label=level,
                split=part,
                data_kind="synthetic_development",
                provenance="AI_SYNTHETIC_NOT_REAL_STUDENT",
                generator_seed=20261016,
            )
            sessions.append(row)
            fields = (
                "game_session_id",
                "student_code",
                "concept_id",
                "assessment_phase",
                "game_type",
                "gameplay_score",
                "wrong_attempt_count",
                "retry_count",
                "total_hint_count",
                "game_hint_rate",
                "skipped_step_count",
                "game_completion_rate",
                "game_active_time_sec",
                "first_attempt_correct_steps",
                "planned_steps",
                "split",
                "data_kind",
            )
            observations[part].append(
                {
                    **{k: row[k] for k in fields},
                    "observation_id": sid,
                    "mastery_label": level,
                    "independent_target": "mastery_label",
                    "label_source": "simulated_latent_ability",
                }
            )
    tables = {
        "synthetic_sessions_all": sessions,
        "synthetic_sessions_train": [r for r in sessions if r["split"] == "train"],
        "synthetic_sessions_test": [r for r in sessions if r["split"] == "test"],
        "synthetic_task_steps": steps,
        "synthetic_independent_labels": labels,
        "synthetic_learner_split": splits,
    }
    manifest = dict(
        data_kind="synthetic_development",
        contains_real_student_data=False,
        contains_teacher_assessment_results=False,
        generator_seed=20261016,
        simulated_learners=200,
        sessions=400,
        sessions_per_learner=2,
        game_types=["drag_drop", "hangman"],
        training_learners=161,
        test_learners=39,
        training_sessions=322,
        test_sessions=78,
        class_counts={"beginner": 67, "intermediate": 67, "advanced": 66},
    )
    return tables, manifest, observations, tmp_path / "SYNTHETIC.zip"


def read_fixture(data):
    tables, manifest, observations, path = data
    return read_synthetic_archive(pack(path, tables, manifest, observations))


def test_adapter_reconciles_steps_and_preserves_unknowns_and_simulated_labels(
    fixture_data,
):
    dataset = read_fixture(fixture_data)
    assert len(dataset.observations) == 400
    for row in dataset.observations:
        assert row.student_code.startswith("SIM_")
        assert row.gameplay_score == row.first_attempt_correct_steps / row.total_steps
        assert row.hint_count == 2 and row.steps_with_hints == 1
        assert row.skipped_steps is None
        assert row.tasks_completed == 5 and row.task_completed is False
        assert row.mastery_label.source == "test"
        assert "NOT teacher/quiz/test evidence" in row.mastery_label.source_reference
        assert row.task_duration_seconds == row.total_steps
        values = extract_research_features(row).values
        assert values["hint_usage_rate"] == 1 / row.total_steps
        assert values["skipped_steps"] is None


@pytest.mark.parametrize(
    "mutation",
    ["genuine", "split", "owner", "step", "score", "teacher", "seed", "manifest"],
)
def test_invalid_inputs_fail_even_with_fresh_checksums(fixture_data, mutation):
    tables, manifest, observations, _ = fixture_data
    if mutation == "genuine":
        tables["synthetic_sessions_all"][0]["student_code"] = "STU_001"
    elif mutation == "split":
        tables["synthetic_learner_split"][0]["split"] = "train"
    elif mutation == "owner":
        tables["synthetic_task_steps"][0]["student_code"] = "SIM_200"
    elif mutation == "step":
        tables["synthetic_task_steps"][0]["step_index"] = 2
    elif mutation == "score":
        tables["synthetic_sessions_all"][0]["gameplay_score"] = 0.5
    elif mutation == "teacher":
        tables["synthetic_independent_labels"][0]["label_source"] = "teacher"
    elif mutation == "seed":
        manifest["generator_seed"] = 42
    else:
        manifest["class_counts"]["beginner"] = 66
    with pytest.raises(ValueError):
        read_fixture(fixture_data)


def test_supplied_learner_partition_is_retained_exactly(fixture_data):
    dataset = read_fixture(fixture_data)
    config = ExperimentConfig(target="mastery", class_labels=CLASSES)
    cohort = prepare_cohort(dataset.observations, config)
    split = predefined_split(cohort, dataset, config)
    assert len(split.train) == 322 and len(split.test) == 78
    assert {cohort.rows[i].student_code for i in split.train}.isdisjoint(
        {cohort.rows[i].student_code for i in split.test}
    )
    assert all(
        dataset.learner_split[cohort.rows[i].student_code] == "test" for i in split.test
    )


def test_direct_runner_rejects_genuine_rows_before_creating_output(
    fixture_data, tmp_path
):
    dataset = read_fixture(fixture_data)
    dataset.observations[0] = dataset.observations[0].model_copy(
        update={"student_code": "STU_001"}
    )
    output = tmp_path / DESIGNATION
    with pytest.raises(ValueError, match="Only synthetic"):
        train_synthetic(dataset, output)
    assert not output.exists()
