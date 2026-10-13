"""SYNTHETIC DEVELOPMENT FIXTURES ONLY: no learner observations or DB imports."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.modules.game.ml.artifacts import load_artifact, save_artifact
from app.modules.game.ml.dataset import FEATURE_NAMES, build_examples, extract_features
from app.modules.game.ml.inference import predict_next_hint
from app.modules.game.ml.schema import TaskRecord, validate_dataset
from app.modules.game.ml.training import (
    TrainingDataError,
    evaluate,
    feature_frame,
    split_by_learner,
    train,
)


def synthetic_task(**overrides) -> dict:
    """Fabricated task for unit tests, never a claim about real learner behaviour."""
    return {
        "student_code": "SYNTHETIC-learner-0",
        "session_id": "SYNTHETIC-session-0",
        "learning_cycle_id": "SYNTHETIC-cycle-0",
        "game_type": "drag_drop",
        "task_id": "SYNTHETIC-task-1",
        "task_order": 1,
        "difficulty": "easy",
        "concept": "linear_equations",
        "total_steps": 4,
        "first_attempt_correct_steps": 3,
        "wrong_attempts": 2,
        "retry_count": 2,
        "hint_requests": 1,
        "steps_with_hints": 1,
        "task_duration_seconds": 20.0,
        "task_completed": True,
        "hint_observation_complete": True,
        "task_duration_reliable": True,
        "next_task_hint_used_label": None,
        **overrides,
    }


@pytest.fixture
def synthetic_rows() -> list[dict]:
    """12 invented learners, two sessions each, six tasks per session."""
    rows = []
    for learner in range(12):
        for session in range(2):
            for order in range(1, 7):
                hints = (learner + session + order) % 2
                rows.append(
                    synthetic_task(
                        student_code=f"SYNTHETIC-learner-{learner}",
                        session_id=f"SYNTHETIC-session-{learner}-{session}",
                        learning_cycle_id=f"SYNTHETIC-cycle-{learner}",
                        task_id=f"SYNTHETIC-task-{order}",
                        task_order=order,
                        difficulty=("easy", "medium", "hard")[(order - 1) // 2],
                        hint_requests=hints,
                        steps_with_hints=hints,
                        task_duration_seconds=float(learner + order + 10),
                        next_task_difficulty=("easy", "medium", "hard")[
                            min(order // 2, 2)
                        ]
                        if order < 6
                        else None,
                    )
                )
    return rows


@pytest.fixture
def synthetic_run(synthetic_rows):
    return train(
        synthetic_rows,
        provenance="unit-test invented fixture",
        data_kind="synthetic_development",
    )


def test_feature_extraction_and_allowlist():
    current = TaskRecord(**synthetic_task(task_order=2, next_task_difficulty="hard"))
    previous = TaskRecord(**synthetic_task(difficulty="medium"))
    extraction = extract_features(current, previous)
    assert extraction.values == {
        "first_attempt_accuracy": 0.75,
        "wrong_attempts_per_step": 0.5,
        "retry_count": 2,
        "hint_requests": 1,
        "share_steps_with_hints": 0.25,
        "task_completed": 1,
        "task_duration_seconds": 20.0,
        "game_type": "drag_drop",
        "concept": "linear_equations",
        "difficulty": "easy",
        "previous_task_difficulty": "medium",
        "next_task_difficulty": "hard",
    }
    assert not extraction.unavailable
    assert set(extraction.values) == set(FEATURE_NAMES)
    assert not {
        "student_code",
        "session_id",
        "task_id",
        "learning_cycle_id",
        "task_order",
        "next_task_hint_used_label",
        "game_mastery_score",
    } & set(FEATURE_NAMES)


def test_unknown_features_stay_null_and_unreliable_duration_is_masked():
    current = TaskRecord(
        **synthetic_task(
            total_steps=None,
            first_attempt_correct_steps=None,
            wrong_attempts=None,
            retry_count=None,
            hint_requests=None,
            steps_with_hints=None,
            task_completed=None,
            hint_observation_complete=False,
            task_duration_reliable=False,
            game_type=None,
            concept=None,
            difficulty=None,
        )
    )
    extraction = extract_features(current)
    assert all(value is None for value in extraction.values.values())
    assert set(extraction.unavailable) == set(FEATURE_NAMES)
    assert current.task_duration_seconds == 20.0  # raw input is never rewritten


@pytest.mark.parametrize(
    "previous",
    [
        {"session_id": "another-session"},
        {"student_code": "another-learner"},
        {"task_order": 2},
    ],
)
def test_previous_task_must_belong_to_same_session_and_precede_current(previous):
    with pytest.raises(ValueError, match="previous task"):
        extract_features(
            TaskRecord(**synthetic_task(task_order=2)),
            TaskRecord(**synthetic_task(**previous)),
        )


def test_target_uses_explicit_order_and_final_task_is_unknown():
    rows = [
        synthetic_task(
            task_id=f"task-{i}", task_order=i, hint_requests=h, steps_with_hints=h
        )
        for i, h in ((3, 0), (1, 1), (2, 1))
    ]
    examples = build_examples(rows)
    assert [e.current.task_order for e in examples] == [1, 2, 3]
    assert [e.label for e in examples] == [1, 0, None]
    assert [e.next_task_id for e in examples] == ["task-2", "task-3", None]
    assert examples[-1].exclusion_reason == "final_task_no_next_observation"


def test_targets_and_previous_features_never_cross_session_boundaries():
    examples = build_examples(
        [synthetic_task(), synthetic_task(session_id="another-session")]
    )
    assert [e.label for e in examples] == [None, None]
    assert all(e.features.values["previous_task_difficulty"] is None for e in examples)


@pytest.mark.parametrize(
    "overrides, label, reason",
    [
        ({"hint_requests": 0, "steps_with_hints": 0}, 0, None),
        ({"hint_requests": 2, "hint_observation_complete": False}, 1, None),
        ({"task_completed": False}, None, "next_task_incomplete_or_completion_unknown"),
        ({"task_completed": None}, None, "next_task_incomplete_or_completion_unknown"),
        (
            {"hint_requests": None, "hint_observation_complete": False},
            None,
            "next_task_hint_count_unavailable",
        ),
        (
            {
                "hint_requests": 0,
                "steps_with_hints": 0,
                "hint_observation_complete": False,
            },
            None,
            "next_task_zero_hints_unverified",
        ),
    ],
)
def test_target_observability_gates(overrides, label, reason):
    examples = build_examples(
        [
            synthetic_task(),
            synthetic_task(task_order=2, task_id="next", **overrides),
        ]
    )
    assert (examples[0].label, examples[0].exclusion_reason) == (label, reason)


def test_incomplete_target_is_not_skipped_to_reach_a_later_task():
    examples = build_examples(
        [
            synthetic_task(),
            synthetic_task(task_order=2, task_id="unfinished", task_completed=False),
            synthetic_task(task_order=3, task_id="later"),
        ]
    )
    assert examples[0].label is None
    assert examples[0].next_task_id == "unfinished"


def test_gaps_mean_next_observed_task_and_ids_do_not_encode_order():
    examples = build_examples(
        [
            synthetic_task(task_order=9, task_id="alphabetically-first"),
            synthetic_task(task_order=2, task_id="z-last"),
        ]
    )
    assert examples[0].next_task_id == "alphabetically-first"


def test_future_outcomes_and_actual_future_difficulty_never_enter_current_features():
    current = synthetic_task()
    no_hint = synthetic_task(
        task_order=2,
        task_id="next",
        hint_requests=0,
        steps_with_hints=0,
        difficulty="hard",
    )
    hinted = {
        **no_hint,
        "hint_requests": 3,
        "steps_with_hints": 2,
        "wrong_attempts": 90,
        "difficulty": "medium",
    }
    a, b = build_examples([current, no_hint])[0], build_examples([current, hinted])[0]
    assert a.label == 0 and b.label == 1
    assert a.features == b.features
    assert a.features.values["next_task_difficulty"] is None


def test_supplied_labels_are_checked_never_blindly_trusted():
    with pytest.raises(ValueError, match="conflicts"):
        build_examples([synthetic_task(next_task_hint_used_label=0)])
    examples = build_examples(
        [
            synthetic_task(next_task_hint_used_label=1),
            synthetic_task(task_id="next", task_order=2),
        ]
    )
    assert examples[0].label == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"task_order": 0},
        {"task_order": True},
        {"total_steps": 0},
        {"wrong_attempts": -1},
        {"retry_count": "2"},
        {"hint_requests": False},
        {"first_attempt_correct_steps": 5},
        {"steps_with_hints": 3},
        {"task_duration_seconds": float("nan")},
        {"task_duration_seconds": float("inf")},
        {"student_code": "  "},
        {"difficulty": "advanced"},
        {"next_task_hint_used_label": True},
        {"hint_requests": None},
        {"task_duration_seconds": None},
        {"game_mastery_score": 0.8},
    ],
)
def test_schema_rejects_invalid_or_heuristic_inputs(overrides):
    with pytest.raises(ValidationError):
        TaskRecord(**synthetic_task(**overrides))


def test_missing_required_metric_requires_explicit_null():
    row = synthetic_task()
    del row["retry_count"]
    with pytest.raises(ValidationError):
        TaskRecord(**row)


@pytest.mark.parametrize(
    "second, message",
    [
        ({"task_id": "other"}, "duplicate task_order"),
        ({"task_order": 2}, "duplicate task_id"),
        ({"student_code": "other"}, "one learner"),
        ({"learning_cycle_id": "other"}, "one learner"),
        ({"game_type": "hangman"}, "one learner"),
    ],
)
def test_ambiguous_dataset_identity_and_order_fail(second, message):
    with pytest.raises(ValueError, match=message):
        validate_dataset([synthetic_task(), synthetic_task(**second)])


def test_single_class_training_fails(synthetic_rows):
    for row in synthetic_rows:
        row.update(hint_requests=0, steps_with_hints=0)
    with pytest.raises(TrainingDataError, match="both target classes"):
        train(synthetic_rows, provenance="synthetic", data_kind="synthetic_development")


def test_empty_training_fails():
    with pytest.raises(TrainingDataError, match="both target classes"):
        train([], provenance="synthetic", data_kind="synthetic_development")


def test_tiny_training_fails(synthetic_rows):
    with pytest.raises(TrainingDataError, match="too small"):
        train(
            synthetic_rows[:12],
            provenance="synthetic",
            data_kind="synthetic_development",
        )


def test_learner_split_keeps_all_sessions_of_a_learner_together(synthetic_rows):
    examples = [e for e in build_examples(synthetic_rows) if e.label is not None]
    train_indices, test_indices = split_by_learner(examples)
    train_learners = {examples[i].current.student_code for i in train_indices}
    test_learners = {examples[i].current.student_code for i in test_indices}
    assert train_learners.isdisjoint(test_learners)
    assert len(train_learners | test_learners) == 12
    again = split_by_learner(examples)
    np.testing.assert_array_equal(train_indices, again[0])
    np.testing.assert_array_equal(test_indices, again[1])


def test_one_class_in_heldout_group_fails():
    examples = build_examples(
        [
            synthetic_task(
                student_code=f"learner-{i}",
                session_id=f"session-{i}",
                task_id=str(j),
                task_order=j,
                hint_requests=i % 2,
                steps_with_hints=i % 2,
            )
            for i in range(2)
            for j in range(1, 3)
        ]
    )
    with pytest.raises(TrainingDataError, match="partition has only one target class"):
        split_by_learner([e for e in examples if e.label is not None])


def test_pipeline_evaluation_counts_and_baseline(synthetic_run):
    metadata = synthetic_run.metadata
    assert metadata["counts"]["distinct_learners"] == 12
    assert metadata["counts"]["sessions"] == 24
    assert metadata["counts"]["valid_training_examples"] == 120
    assert metadata["counts"]["label_distribution"] == {"0": 60, "1": 60}
    assert metadata["counts"]["exclusions"] == {"final_task_no_next_observation": 24}
    assert metadata["split"]["train"]["learners"] == 9
    assert metadata["split"]["test"]["learners"] == 3
    assert metadata["split"]["test"]["examples"] == 30
    for report in metadata["evaluation"].values():
        assert np.array(report["confusion_matrix"]).sum() == 30
        assert 0 <= report["macro_f1"] <= 1
        assert 0 <= report["balanced_accuracy"] <= 1
    baseline = metadata["evaluation"]["majority_class_baseline"]
    assert baseline["confusion_matrix"] == [[15, 0], [15, 0]]
    assert baseline["macro_f1"] == pytest.approx(1 / 3)
    assert baseline["balanced_accuracy"] == 0.5
    assert metadata["training_data"]["kind"] == "synthetic_development"
    json.dumps(metadata, allow_nan=False)


def test_preprocessing_is_fit_on_training_rows_only(synthetic_rows):
    examples = [e for e in build_examples(synthetic_rows) if e.label is not None]
    train_indices, test_indices = split_by_learner(examples)
    heldout_learners = {examples[i].current.student_code for i in test_indices}
    for row in synthetic_rows:
        if row["student_code"] in heldout_learners:
            row["task_duration_seconds"] = 99999.0
            row["concept"] = "heldout_only_concept"
    run = train(
        synthetic_rows,
        provenance="synthetic leakage check",
        data_kind="synthetic_development",
    )
    numeric = run.model.named_steps["preprocess"].named_transformers_["numeric"]
    assert numeric.named_steps["impute"].statistics_[6] < 100
    assert numeric.named_steps["scale"].mean_[6] < 100
    encoder = (
        run.model.named_steps["preprocess"]
        .named_transformers_["categorical"]
        .named_steps["encode"]
    )
    assert "heldout_only_concept" not in encoder.categories_[1]
    frame = feature_frame([e.features.values for e in examples])
    assert len(run.model.predict(frame.iloc[test_indices])) == len(test_indices)


def test_missing_columns_train_and_predict_without_fabricating_raw_values(
    synthetic_rows,
):
    for row in synthetic_rows:
        row.update(
            total_steps=None,
            first_attempt_correct_steps=None,
            wrong_attempts=None,
            retry_count=None,
            task_duration_reliable=False,
            concept=None,
        )
    run = train(
        synthetic_rows,
        provenance="synthetic missing metrics",
        data_kind="synthetic_development",
    )
    result = predict_next_hint(run, TaskRecord(**synthetic_rows[0]))
    assert 0 <= result["next_task_hint_probability"] <= 1
    assert "first_attempt_accuracy" in result["unavailable_features"]
    assert run.metadata["missing_feature_counts"]["first_attempt_accuracy"] == 120
    assert synthetic_rows[0]["first_attempt_correct_steps"] is None


def test_model_inference_output_and_unseen_category(synthetic_run):
    result = predict_next_hint(
        synthetic_run, TaskRecord(**synthetic_task(game_type="future_mode"))
    )
    assert result["next_task_hint_used_prediction"] in (0, 1)
    assert 0 <= result["next_task_hint_probability"] <= 1
    assert result["decision_threshold"] == 0.5
    assert result["model_version"] == "game-next-hint-logreg-v1"
    assert "not_research_validated" in result["status"]


def test_training_is_reproducible_with_shuffled_input(synthetic_rows, synthetic_run):
    again = train(
        list(reversed(synthetic_rows)),
        provenance="synthetic",
        data_kind="synthetic_development",
    )
    np.testing.assert_array_equal(
        synthetic_run.model.named_steps["classifier"].coef_,
        again.model.named_steps["classifier"].coef_,
    )
    assert again.metadata["split"] == synthetic_run.metadata["split"]
    assert (
        again.metadata["training_data"]["canonical_dataset_sha256"]
        == synthetic_run.metadata["training_data"]["canonical_dataset_sha256"]
    )


def test_artifact_roundtrip_requires_trust_and_refuses_overwrite(
    tmp_path, synthetic_run
):
    destination = tmp_path / "synthetic-artifact"
    save_artifact(synthetic_run, destination)
    with pytest.raises(ValueError, match="trusted_local_artifact"):
        load_artifact(destination)
    loaded = load_artifact(destination, trusted_local_artifact=True)
    current = TaskRecord(**synthetic_task())
    assert predict_next_hint(loaded, current) == predict_next_hint(
        synthetic_run, current
    )
    before = (destination / "model.joblib").read_bytes()
    with pytest.raises(FileExistsError):
        save_artifact(synthetic_run, destination)
    assert (destination / "model.joblib").read_bytes() == before
    metadata = json.loads((destination / "metadata.json").read_text())
    for key in (
        "feature_schema_version",
        "trained_at_utc",
        "training_data",
        "target_definition",
        "feature_names",
        "evaluation",
        "model_sha256",
        "runtime_versions",
    ):
        assert key in metadata


def test_artifact_corruption_fails_before_loading(tmp_path, synthetic_run):
    destination = save_artifact(synthetic_run, tmp_path / "synthetic-artifact")
    (destination / "model.joblib").write_bytes(b"invalid untrusted bytes")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_artifact(destination, trusted_local_artifact=True)


def test_runtime_mismatch_fails_before_loading(tmp_path, synthetic_run):
    destination = save_artifact(synthetic_run, tmp_path / "synthetic-artifact")
    metadata_path = destination / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["runtime_versions"]["scikit-learn"] = "wrong-version"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="runtime versions differ"):
        load_artifact(destination, trusted_local_artifact=True)


def test_evaluation_balanced_accuracy_is_unknown_for_single_class():
    assert evaluate(np.array([1, 1]), np.array([1, 1]))["balanced_accuracy"] is None


def test_cli_synthetic_pipeline_and_no_overwrite(tmp_path, synthetic_rows):
    dataset = tmp_path / "SYNTHETIC-unit-test-tasks.json"
    dataset.write_text(json.dumps(synthetic_rows), encoding="utf-8")
    output = tmp_path / "SYNTHETIC-unit-test-model"
    command = [
        sys.executable,
        "-m",
        "app.modules.game.ml",
        "--dataset",
        str(dataset),
        "--output",
        str(output),
        "--provenance",
        "SYNTHETIC CLI unit test",
        "--data-kind",
        "synthetic_development",
    ]
    result = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["counts"]["valid_training_examples"] == 120
    result = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "already exists" in result.stderr


def test_cli_rejects_invalid_input_without_artifact(tmp_path):
    dataset = tmp_path / "bad.json"
    dataset.write_text("{}", encoding="utf-8")
    output = tmp_path / "must-not-exist"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.modules.game.ml",
            "--dataset",
            str(dataset),
            "--output",
            str(output),
            "--provenance",
            "synthetic",
            "--data-kind",
            "synthetic_development",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "JSON array" in result.stderr
    assert not output.exists()
