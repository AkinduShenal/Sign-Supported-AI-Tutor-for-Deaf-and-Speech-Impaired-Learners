"""No fitting in tests: pure guards plus locally generated genuine artifact checks.

Private snapshot/artifact checks skip when the approved local inputs are absent.
In-memory malformed/missing-value probes never enter training or evaluation.
"""

import copy
import json
import os
import shutil
from pathlib import Path

import pytest

from app.modules.game.ml.real_retrospective import (
    APPROVED_MANIFEST_SHA256,
    FLAGS,
    STATUS,
    check_inputs,
    check_train_only_preprocessing,
    learner_summary,
    load_real_artifact,
    settings,
    train,
    validate_snapshot,
)
from app.modules.game.ml.research_inference import predict_research
from app.modules.game.ml.research_training import ExperimentConfig
from app.modules.game.ml.training import TrainingRun

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "exports/ml-milestone-2-3-4-20261019-preparation-001"


@pytest.fixture
def snapshot():
    if not SNAPSHOT.exists():
        pytest.skip("Private approved research snapshot is not installed")
    return SNAPSHOT


@pytest.fixture(scope="module")
def approved():
    if not SNAPSHOT.exists():
        pytest.skip("Private approved research snapshot is not installed")
    return validate_snapshot(SNAPSHOT)


@pytest.fixture(scope="module")
def experiment():
    value = os.environ.get("REAL_RETROSPECTIVE_TEST_EXPERIMENT")
    if not value:
        pytest.skip("Explicit locally generated real-data experiment path required")
    path = Path(value)
    if not (path / "experiment_manifest.json").exists():
        pytest.skip("Complete trusted-local experiment is unavailable")
    return path


def test_declared_parameters_do_not_tune_on_test_data():
    configs = settings(
        ExperimentConfig(
            target="mastery", class_labels=("beginner", "intermediate", "advanced")
        )
    )
    assert set(configs) == {"logistic_regression", "decision_tree", "random_forest"}
    for config in configs.values():
        assert config.evaluation.random_state == 42
        assert config.evaluation.test_size == 0.25
        assert config.evaluation.min_examples == 20
        assert config.evaluation.min_learners == 6
        assert config.evaluation.require_all_classes_in_partitions
        assert config.common_context == ()
    assert configs["logistic_regression"].classifier_parameters["C"] == 1.0
    assert configs["decision_tree"].classifier_parameters["max_depth"] == 5
    assert configs["random_forest"].classifier_parameters["n_estimators"] == 100


def test_learner_metrics_do_not_count_sessions_as_students():
    # Invented predictions only, not assessments or a fitted dataset.
    rows = [
        {"student_code": "ENGINEERING-A", "actual": "beginner", "predicted": p}
        for p in ["beginner", "beginner", "advanced"]
    ]
    rows += [
        {"student_code": "ENGINEERING-B", "actual": "advanced", "predicted": "advanced"}
    ]
    result = learner_summary(rows)
    assert result["independent_learners"] == 2
    assert sum(p["session_count"] for p in result["predictions"]) == 4
    assert sum(sum(row) for row in result["metrics"]["confusion_matrix"]) == 2


def test_learner_vote_ties_use_predeclared_rubric_order():
    result = learner_summary(
        [
            {
                "student_code": "ENGINEERING-A",
                "actual": "advanced",
                "predicted": "advanced",
            },
            {
                "student_code": "ENGINEERING-A",
                "actual": "advanced",
                "predicted": "beginner",
            },
        ]
    )
    assert result["predictions"][0]["predicted"] == "beginner"


def test_conflicting_learner_targets_are_rejected():
    with pytest.raises(ValueError, match="Conflicting independent"):
        learner_summary(
            [
                {
                    "student_code": "ENGINEERING-A",
                    "actual": "beginner",
                    "predicted": "advanced",
                },
                {
                    "student_code": "ENGINEERING-A",
                    "actual": "advanced",
                    "predicted": "advanced",
                },
            ]
        )


def test_changed_approved_manifest_stops_before_fitting(
    snapshot, tmp_path, monkeypatch
):
    from app.modules.game.ml import real_retrospective

    copied = tmp_path / "snapshot"
    copied.mkdir()
    (copied / "snapshot_manifest.json").write_bytes(
        (snapshot / "snapshot_manifest.json").read_bytes() + b"\n"
    )
    monkeypatch.setattr(
        real_retrospective,
        "run_comparison",
        lambda *a, **k: pytest.fail("Must not fit"),
    )
    with pytest.raises(ValueError, match="manifest changed"):
        train(copied, tmp_path / (STATUS + "-test"))


def test_changed_feature_member_stops_before_fitting(snapshot, tmp_path):
    copied = tmp_path / "snapshot"
    shutil.copytree(snapshot, copied)
    (copied / "retrospective/score_only_features.json").write_text(
        "[]", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Snapshot member changed"):
        check_inputs(copied)


def test_reproduced_cohort_and_group_split_are_exact(approved):
    assert len(approved["cohort"].rows) == 30
    assert len(approved["split"].train) == 22
    assert len(approved["split"].test) == 8
    train_codes = {
        approved["cohort"].rows[i].student_code for i in approved["split"].train
    }
    test_codes = {
        approved["cohort"].rows[i].student_code for i in approved["split"].test
    }
    assert len(train_codes) == 12 and len(test_codes) == 4
    assert not train_codes & test_codes
    assert (
        approved["report"]["readiness"]["prospective"]["mechanical_evaluation_status"]
        == "BLOCKED"
    )


def test_existing_experiment_is_never_overwritten(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        train(Path("not-read"), output)


@pytest.mark.parametrize(
    "algorithm,short",
    [("logistic_regression", "lr"), ("decision_tree", "dt"), ("random_forest", "rf")],
)
@pytest.mark.parametrize("feature", ["score_only", "score_plus_behaviour"])
def test_real_artifact_reload_preprocessing_and_no_target_leakage(
    experiment, approved, algorithm, short, feature
):
    path = experiment / short / feature
    run = load_real_artifact(path, classifier=algorithm, trusted_local_artifact=True)
    assert run.metadata["status_flags"] == list(FLAGS)
    assert not run.metadata["production_approved"]
    assert run.metadata["approved_snapshot_manifest_sha256"] == APPROVED_MANIFEST_SHA256
    assert run.metadata["training_data"]["kind"] == "real_collected"
    assert set(run.model.classes_) == {"beginner", "intermediate", "advanced"}
    assert check_train_only_preprocessing(run, approved["cohort"], approved["split"])[
        "passed"
    ]
    assert run.metadata["split"] == approved["split"].details
    assert list(run.model.feature_names_in_) == run.metadata["feature_names"]
    assert not {
        "teacher_score",
        "assessment_score",
        "mastery_label",
        "student_code",
    } & set(run.metadata["feature_names"])
    row = approved["cohort"].rows[approved["split"].test[0]].model_dump(mode="json")
    expected = predict_research(run, row)
    row["mastery_label"] = row["difficulty_label"] = None
    assert predict_research(run, row) == expected


def test_loader_requires_trust_before_deserialization(experiment):
    with pytest.raises(ValueError, match="Explicit trust"):
        load_real_artifact(
            experiment / "lr/score_only", classifier="logistic_regression"
        )


@pytest.mark.parametrize(
    "change", ["synthetic", "prospective", "production", "snapshot"]
)
def test_wrong_artifact_kind_is_rejected_before_joblib(
    experiment, tmp_path, monkeypatch, change
):
    import joblib

    path = tmp_path / "candidate"
    path.mkdir()
    metadata = json.loads((experiment / "lr/score_only/metadata.json").read_text())
    if change == "synthetic":
        metadata["training_data"]["kind"] = "synthetic_development"
    elif change == "prospective":
        metadata["analysis_purpose"] = "prospective"
    elif change == "production":
        metadata["production_approved"] = True
    else:
        metadata["approved_snapshot_manifest_sha256"] = "0" * 64
    (path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(
        joblib, "load", lambda *a, **k: pytest.fail("Must not deserialize")
    )
    with pytest.raises(ValueError):
        load_real_artifact(
            path, classifier="logistic_regression", trusted_local_artifact=True
        )


def test_corrupt_model_checksum_is_rejected_before_joblib(
    experiment, tmp_path, monkeypatch
):
    import joblib

    path = tmp_path / "corrupt"
    shutil.copytree(experiment / "lr/score_only", path)
    (path / "model.joblib").write_bytes(b"corrupt engineering test copy")
    monkeypatch.setattr(
        joblib, "load", lambda *a, **k: pytest.fail("Must not deserialize")
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_real_artifact(
            path, classifier="logistic_regression", trusted_local_artifact=True
        )


def test_input_schema_and_feature_order_are_checked(experiment, approved):
    run = load_real_artifact(
        experiment / "lr/score_plus_behaviour",
        classifier="logistic_regression",
        trusted_local_artifact=True,
    )
    row = approved["cohort"].rows[approved["split"].test[0]].model_dump(mode="json")
    with pytest.raises(ValueError):
        predict_research(run, {**row, "teacher_score": 10})
    wrong = TrainingRun(run.model, copy.deepcopy(run.metadata))
    wrong.metadata["feature_names"].reverse()
    with pytest.raises(ValueError, match="feature definition"):
        predict_research(wrong, row)


def test_missing_value_input_probe_uses_saved_preprocessing(experiment, approved):
    run = load_real_artifact(
        experiment / "lr/score_plus_behaviour",
        classifier="logistic_regression",
        trusted_local_artifact=True,
    )
    row = approved["cohort"].rows[approved["split"].test[0]].model_dump(mode="json")
    row.update(
        mastery_label=None,
        difficulty_label=None,
        gameplay_score=None,
        first_attempt_correct_steps=None,
        first_attempt_observation_complete=False,
        hint_count=None,
        steps_with_hints=None,
        hint_observation_complete=False,
    )
    result = predict_research(run, row)
    assert result["prediction"] in ("beginner", "intermediate", "advanced")
    assert abs(sum(result["class_probabilities"].values()) - 1) < 1e-12
