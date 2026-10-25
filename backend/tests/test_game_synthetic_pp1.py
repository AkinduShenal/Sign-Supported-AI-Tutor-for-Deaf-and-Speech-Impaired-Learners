"""Synthetic engineering fixtures / explicitly local synthetic bundles; never fit."""

import copy
import json
import os
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

from app.modules.game.ml.research_dataset import feature_set
from app.modules.game.ml.research_training import prepare_cohort, research_frame
from app.modules.game.ml.synthetic_development import (
    CLASSES,
    predefined_split,
    read_synthetic_archive,
)
from app.modules.game.ml import synthetic_pp1 as demo


@pytest.fixture(autouse=True)
def offline_no_fit():
    with (
        patch("psycopg.connect", side_effect=AssertionError("No database access")),
        patch(
            "sqlalchemy.create_engine", side_effect=AssertionError("No database engine")
        ),
        patch(
            "sklearn.pipeline.Pipeline.fit",
            side_effect=AssertionError("No fitting in regression tests"),
        ),
        patch(
            "joblib.dump",
            side_effect=AssertionError("No model saving in regression tests"),
        ),
    ):
        yield


@pytest.fixture
def dataset(tmp_path):
    from test_game_synthetic_development import fixture_data, pack

    tables, manifest, observations, path = fixture_data.__wrapped__(tmp_path)
    return read_synthetic_archive(pack(path, tables, manifest, observations))


def test_balanced_subset_keeps_source_partitions_and_both_modes(dataset):
    before = [row.model_dump(mode="json") for row in dataset.observations]
    subset, selection = demo.select_demo(dataset)
    assert len(subset.observations) == 180
    assert len(subset.learner_split) == 90
    assert Counter(
        r["simulated_class"] for r in selection["learners"]
    ) == dict.fromkeys(CLASSES, 30)
    for part, count in (("train", 24), ("test", 6)):
        assert Counter(
            r["simulated_class"]
            for r in selection["learners"]
            if r["original_split"] == part
        ) == dict.fromkeys(CLASSES, count)
    assert all(
        part == dataset.learner_split[code]
        for code, part in subset.learner_split.items()
    )
    for code in subset.learner_split:
        rows = [row for row in subset.observations if row.student_code == code]
        assert len(rows) == 2
        assert {r.game_type for r in rows} == {"drag_drop", "hangman"}
    config = demo.configuration("logistic_regression")
    cohort = prepare_cohort(subset.observations, config)
    split = predefined_split(cohort, subset, config)
    assert not cohort.exclusions
    assert len(split.train) == 144 and len(split.test) == 36
    assert not {cohort.rows[i].student_code for i in split.train} & {
        cohort.rows[i].student_code for i in split.test
    }
    assert before == [row.model_dump(mode="json") for row in dataset.observations]


def test_selection_is_order_invariant_and_never_uses_gameplay_or_predictions(dataset):
    _, expected = demo.select_demo(dataset)
    changed = copy.deepcopy(dataset)
    changed.observations.reverse()
    for row in changed.observations:
        row.wrong_attempts = 999
        row.retry_count = 999
        row.first_attempt_correct_steps = 0
    _, actual = demo.select_demo(changed)
    assert actual == expected


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("genuine_id", "Non-synthetic identity"),
        ("genuine_label", "Non-synthetic target"),
        ("one_mode", "both intended sessions"),
        ("class_shortfall", "Cannot preserve fixed"),
        ("partition", "Unknown source partition"),
    ],
)
def test_invalid_cohort_is_not_relabelled_or_reassigned(dataset, mutation, match):
    subset, selection = demo.select_demo(dataset)
    chosen = selection["learners"][0]["student_code"]
    rows = [row for row in dataset.observations if row.student_code == chosen]
    if mutation == "genuine_id":
        rows[0].student_code = "STU_001"
    elif mutation == "genuine_label":
        rows[0].mastery_label.source_reference = "REAL_TEACHER_SHEET"
    elif mutation == "one_mode":
        dataset.observations.remove(rows[0])
    elif mutation == "class_shortfall":
        removed = {
            r.student_code
            for r in dataset.observations
            if r.mastery_label.value == "beginner"
            and dataset.learner_split[r.student_code] == "test"
        }
        dataset.observations = [
            r for r in dataset.observations if r.student_code not in removed
        ]
        dataset.learner_split = {
            c: p for c, p in dataset.learner_split.items() if c not in removed
        }
    else:
        dataset.learner_split[chosen] = "validation"
    with pytest.raises(ValueError, match=match):
        demo.select_demo(dataset)


def test_source_audit_reports_generator_shortcuts_and_no_label_features(dataset):
    audit = demo.audit_source(dataset)
    assert audit["thirty_learners_per_class_available"]
    assert all(audit["shared_score_values_between_classes"].values())
    assert audit["predictor_allowlists"]["score_only"] == ["gameplay_score"]
    assert len(audit["predictor_allowlists"]["score_plus_behaviour"]) == 13
    risks = " ".join(audit["generator_audit"]["risks"])
    assert "generator assumptions" in risks and "Wrong attempts equal retries" in risks
    subset, _ = demo.select_demo(dataset)
    for name in demo.FEATURE_SETS:
        labeled = research_frame(subset.observations, feature_set(name))
        stripped = copy.deepcopy(subset.observations)
        for row in stripped:
            row.mastery_label = None
            row.difficulty_label = None
        assert labeled.equals(research_frame(stripped, feature_set(name)))


def test_pinned_source_rejects_missing_or_different_archive(tmp_path):
    path = tmp_path / "synthetic_game_ml_200x2.zip"
    with pytest.raises(ValueError, match="Required researcher archive missing"):
        demo.load_source(path)
    path.write_bytes(b"not researcher evidence")
    with pytest.raises(ValueError, match="fingerprint changed"):
        demo.load_source(path)


def test_prefit_plan_and_cohort_are_saved_before_any_fit(
    dataset, tmp_path, monkeypatch
):
    output = tmp_path / (demo.STATUS + "-engineering-only")
    monkeypatch.setattr(demo, "load_source", lambda _: dataset)

    def stop_fit(*args, **kwargs):
        plan_path = output / "experiment_plan.BEFORE_FITTING.json"
        plan = json.loads(plan_path.read_text())
        assert len(plan["configurations"]) == 3
        assert plan["split"]["train"]["learners"] == 72
        assert plan["split"]["test"]["learners"] == 18
        assert plan["selection_namespace"] == demo.SELECTION_NAMESPACE
        assert plan["selected_learners_sha256"] == demo.sha(
            output / "selected_learners.json"
        )
        assert not list(output.rglob("*.joblib"))
        raise RuntimeError("Stopped deliberately before fitting")

    monkeypatch.setattr(demo, "fit_experiment", stop_fit)
    with pytest.raises(RuntimeError, match="Stopped deliberately"):
        demo.train_demo(tmp_path / "unused.zip", output)
    assert not (output / "experiment_manifest.json").exists()
    with pytest.raises(ValueError, match="already exists"):
        demo.train_demo(tmp_path / "unused.zip", output)


def test_bad_output_path_fails_before_loading_source(tmp_path):
    with pytest.raises(ValueError, match="Output directory must contain"):
        demo.train_demo(tmp_path / "missing.zip", tmp_path / "real-data")


def test_learner_majority_ties_ignore_actual_class():
    rows = [
        {"student_code": "SIM_001", "actual": "advanced", "predicted": p}
        for p in ("advanced", "beginner")
    ]
    summary = demo.learner_summary(rows)
    assert summary["simulated_learners"] == 1
    assert summary["predictions"][0]["predicted"] == "beginner"
    assert sum(sum(row) for row in summary["metrics"]["confusion_matrix"]) == 1
    with pytest.raises(ValueError, match="Non-SIM"):
        demo.learner_summary([{**rows[0], "student_code": "STU_001"}])


def test_loader_requires_trust_and_flags_before_deserialization(tmp_path):
    with pytest.raises(ValueError, match="trusted local"):
        demo.load_demo_artifact(tmp_path, classifier="decision_tree")
    (tmp_path / "metadata.json").write_text(
        json.dumps({"training_data": {"kind": "real_collected"}})
    )
    with patch("joblib.load", side_effect=AssertionError("Must reject before loading")):
        with pytest.raises(ValueError, match="synthetic PP1"):
            demo.load_demo_artifact(
                tmp_path, classifier="decision_tree", trusted_local_artifact=True
            )
    with pytest.raises(ValueError, match="trusted local"):
        demo.infer_demo(tmp_path)


@pytest.fixture(scope="module")
def experiment():
    value = os.environ.get("SYNTHETIC_PP1_TEST_EXPERIMENT")
    if not value:
        pytest.skip("Explicit trusted-local synthetic PP1 output required")
    path = Path(value)
    demo.verify_experiment(path)
    return path


def test_new_local_artifacts_are_synthetic_only_and_preprocessed_on_train(experiment):
    document = json.loads((experiment / "adapted_observations.json").read_text())
    for classifier in demo.CONFIGURATIONS:
        cohort = prepare_cohort(
            document["observations"], demo.configuration(classifier)
        )
        selection = json.loads((experiment / "selected_learners.json").read_text())
        splits = {r["student_code"]: r["original_split"] for r in selection["learners"]}
        source = demo.SyntheticDataset(
            list(cohort.rows), splits, {"manifest": {"generator_seed": 20261016}}, {}
        )
        split = predefined_split(cohort, source, demo.configuration(classifier))
        for name in demo.FEATURE_SETS:
            run = demo.load_demo_artifact(
                experiment / classifier / name,
                classifier=classifier,
                trusted_local_artifact=True,
            )
            assert run.metadata["status"] == demo.STATUS
            assert run.metadata["source_archive_sha256"] == demo.ARCHIVE_SHA256
            assert all(
                p["source_reference"].startswith("SYNTHETIC_GENERATOR:")
                and p["source"] == "test"
                for p in run.metadata["label_provenance"]
            )
            assert demo.check_preprocessing(run, cohort, split)["passed"]


def test_inference_reloads_six_models_without_fitting_or_saving(experiment):
    before = demo.inventory(experiment)
    result = demo.infer_demo(experiment, trusted_local_artifacts=True)
    assert result["predictions_checked"] == 216
    assert result["fits_performed"] == 0
    assert len({p["student_code"] for p in result["predictions"]}) == 18
    assert all(
        p["result_kind"] == "SYNTHETIC TEST RESULT" for p in result["predictions"]
    )
    assert before == demo.inventory(experiment)


def test_saved_metrics_use_test_only_and_distinct_learner_counts(experiment):
    results = json.loads((experiment / "synthetic_test_results.json").read_text())
    for classifier, report in results["reports"].items():
        for name, model in report["models"].items():
            assert len(model["session_predictions"]) == 36
            assert (
                sum(sum(r) for r in model["session_metrics"]["confusion_matrix"]) == 36
            )
            assert model["learner_evaluation"]["simulated_learners"] == 18
            assert (
                sum(
                    sum(r)
                    for r in model["learner_evaluation"]["metrics"]["confusion_matrix"]
                )
                == 18
            )
            assert Counter(
                p["actual"] for p in model["session_predictions"]
            ) == dict.fromkeys(CLASSES, 12)


def test_manifest_member_change_is_rejected_without_loading(experiment, tmp_path):
    output = tmp_path / (demo.STATUS + "-tampered")
    output.mkdir()
    (output / "experiment_manifest.json").write_bytes(
        (experiment / "experiment_manifest.json").read_bytes()
    )
    with patch(
        "joblib.load", side_effect=AssertionError("No loading changed experiment")
    ):
        with pytest.raises(ValueError, match="checksums changed"):
            demo.infer_demo(output, trusted_local_artifacts=True)
