"""INVENTED SYNTHETIC fixtures only; no real labels, learners, DB or research claims."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.modules.game.ml.artifacts import load_artifact
from app.modules.game.ml.research_artifacts import (
    load_research_artifact,
    save_comparison,
)
from app.modules.game.ml.research_dataset import (
    aggregate_observation,
    extract_research_features,
    feature_set,
)
from app.modules.game.ml.research_inference import predict_research
from app.modules.game.ml.research_schema import (
    IndependentLabel,
    ObservationContext,
    ResearchObservation,
    validate_research_dataset,
)
from app.modules.game.ml.research_training import (
    ExperimentConfig,
    ResearchSplit,
    evaluate_research,
    fit_experiment,
    learner_split,
    prepare_cohort,
    run_comparison,
)
from app.modules.game.ml.training import TrainingDataError

CLASSES = (
    "low",
    "medium",
    "high",
)  # Test rubric only; not approved research thresholds.


def synthetic_label(value="low", **overrides):
    return {
        "student_code": "SYNTHETIC-learner-0",
        "session_id": "SYNTHETIC-session-0",
        "concept": "SYNTHETIC-concept-0",
        "assessment_phase": "pre_tutor",
        "value": value,
        "source": "teacher",
        "source_reference": "SYNTHETIC-independent-assessment",
        "assessed_at": "2026-10-12T11:00:00+00:00",
        "rubric_version": "SYNTHETIC-test-rubric-v1",
        "gameplay_independent": True,
        **overrides,
    }


def synthetic_observation(**overrides):
    row = {
        "student_code": "SYNTHETIC-learner-0",
        "session_id": "SYNTHETIC-session-0",
        "concept": "SYNTHETIC-concept-0",
        "game_type": "drag_drop",
        "activity_ids": ["SYNTHETIC-activity-1", "SYNTHETIC-activity-2"],
        "assessment_phase": "pre_tutor",
        "observation_started_at": "2026-10-12T09:00:00+00:00",
        "observation_ended_at": "2026-10-12T10:00:00+00:00",
        "total_steps": 10,
        "first_attempt_correct_steps": 5,
        "first_attempt_observation_complete": True,
        "wrong_attempts": 5,
        "retry_count": 5,
        "hint_count": 1,
        "steps_with_hints": 1,
        "hint_observation_complete": True,
        "tasks_total": 2,
        "tasks_completed": 2,
        "task_completed": True,
        "skipped_steps": 0,
        "task_duration_seconds": 30.0,
        "task_duration_reliable": True,
        "difficulty_label": synthetic_label(),
        "mastery_label": synthetic_label("developing", source="quiz"),
        **overrides,
    }
    identity = {
        name: row[name]
        for name in ("student_code", "session_id", "concept", "assessment_phase")
    }
    for name in ("difficulty_label", "mastery_label"):
        if name not in overrides:
            row[name].update(identity)
    return row


@pytest.fixture
def synthetic_rows():
    """12 invented learners, 24 sessions, 72 independently labelled units.

    Fabricated fixture labels/behaviours intentionally make a separable pipeline
    test. The independence flag is test input, not a real teacher assessment.
    """
    rows = [
        synthetic_observation(
            student_code=f"SYNTHETIC-learner-{learner}",
            session_id=f"SYNTHETIC-session-{learner}-{session}",
            concept=f"SYNTHETIC-concept-{index}",
            wrong_attempts=5 + index * 3 + learner % 2,
            retry_count=5 + index * 3,
            hint_count=index * 2,
            steps_with_hints=index,
            task_duration_seconds=float(30 + index * 10),
        )
        for learner in range(12)
        for session in range(2)
        for index in range(3)
    ]
    for row in rows:
        index = int(row["concept"].rsplit("-", 1)[1])
        row["difficulty_label"]["value"] = CLASSES[index]
        row["mastery_label"]["value"] = "secure" if index == 0 else "developing"
    return rows


@pytest.fixture
def config():
    return ExperimentConfig(class_labels=CLASSES)


@pytest.fixture
def comparison(synthetic_rows, config):
    return run_comparison(
        synthetic_rows,
        config,
        provenance="SYNTHETIC unit-test fixture",
        data_kind="synthetic_development",
    )


def test_score_is_explicit_audited_first_attempt_correctness():
    row = ResearchObservation(**synthetic_observation())
    assert row.gameplay_score == row.first_attempt_accuracy == 0.5
    assert row.score_definition == "first_attempt_correctness_v1"
    assert (
        ResearchObservation(
            **synthetic_observation(first_attempt_correct_steps=0)
        ).gameplay_score
        == 0
    )
    assert (
        ResearchObservation(
            **synthetic_observation(first_attempt_correct_steps=10)
        ).gameplay_score
        == 1
    )
    assert (
        ResearchObservation(**synthetic_observation(gameplay_score=0.5)).gameplay_score
        == 0.5
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"total_steps": None},
        {"first_attempt_correct_steps": None},
        {"first_attempt_observation_complete": False},
    ],
)
def test_score_unavailable_when_evidence_or_coverage_is_missing(overrides):
    assert (
        ResearchObservation(**synthetic_observation(**overrides)).gameplay_score is None
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"gameplay_score": 0.9},
        {"gameplay_score": 0.5, "first_attempt_observation_complete": False},
        {"is_successful": True},
        {"game_mastery_score": 0.9},
        {"stars": 3},
        {"difficulty": "hard"},
        {"total_steps": 0},
        {"first_attempt_correct_steps": 11},
        {"wrong_attempts": True},
        {"tasks_completed": 3},
        {"task_completed": False},
        {"hint_count": 0},
        {"task_duration_seconds": None},
        {"task_duration_seconds": 3601.0},
        {"task_duration_seconds": float("nan")},
        {"skipped_steps": 11},
        {"observation_ended_at": "2026-10-12T08:00:00+00:00"},
        {"observation_started_at": "2026-10-12T09:00:00"},
        {"activity_ids": ["duplicate", "duplicate"]},
    ],
)
def test_contract_rejects_unsafe_or_inconsistent_inputs(overrides):
    with pytest.raises(ValidationError):
        ResearchObservation(**synthetic_observation(**overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"gameplay_independent": False},
        {"source": "game-heuristic-v1"},
        {"assessed_at": "2026-10-12T11:00:00"},
        {"rubric_version": " "},
    ],
)
def test_labels_need_independent_source_rubric_and_timezone(overrides):
    with pytest.raises(ValidationError):
        IndependentLabel(**synthetic_label(**overrides))


def test_label_dates_are_audit_only_and_may_precede_or_follow_gameplay():
    row = ResearchObservation(
        **synthetic_observation(
            difficulty_label=synthetic_label(assessed_at="2026-10-11T11:00:00+00:00")
        )
    )
    assert row.difficulty_label.assessed_at < row.observation_started_at
    assert "assessed_at" not in extract_research_features(row).values


@pytest.mark.parametrize("target", ["difficulty_label", "mastery_label"])
@pytest.mark.parametrize(
    "key, value",
    [
        ("student_code", "mismatched-student"),
        ("session_id", "mismatched-session"),
        ("concept", "mismatched-concept"),
        ("assessment_phase", "post_tutor"),
    ],
)
def test_independent_labels_must_match_observation_identity(target, key, value):
    row = synthetic_observation()
    row[target][key] = value
    with pytest.raises(ValidationError, match="does not match"):
        ResearchObservation(**row)


def test_duplicate_units_and_session_ownership_fail():
    with pytest.raises(ValueError, match="Duplicate"):
        validate_research_dataset([synthetic_observation(), synthetic_observation()])
    with pytest.raises(ValueError, match="one learner"):
        validate_research_dataset(
            [
                synthetic_observation(),
                synthetic_observation(concept="other", student_code="other"),
            ]
        )


def test_feature_sets_share_exact_scores_and_context_and_exclude_labels():
    context = ("concept", "game_type", "assessment_phase")
    a, b = (
        feature_set("score_only", context),
        feature_set("score_plus_behaviour", context),
    )
    assert a.numeric == ("gameplay_score",)
    assert set(a.names) < set(b.names)
    assert a.categorical == b.categorical == context
    features = extract_research_features(ResearchObservation(**synthetic_observation()))
    assert features.values["wrong_attempts_per_step"] == 0.5
    assert features.values["hint_usage_rate"] == 0.1
    assert features.values["completion_rate"] == 1.0
    assert features.values["duration_per_step"] == 3.0
    assert not {
        "student_code",
        "session_id",
        "difficulty_label",
        "mastery_label",
        "source",
        "assessed_at",
        "rubric_version",
        "game_mastery_score",
        "first_attempt_accuracy",
    } & set(b.names)


def test_unreliable_duration_and_hint_coverage_are_masked():
    row = ResearchObservation(
        **synthetic_observation(
            task_duration_reliable=False, hint_observation_complete=False
        )
    )
    features = extract_research_features(row)
    for name in (
        "hint_count",
        "hint_usage_rate",
        "task_duration_seconds",
        "duration_per_step",
    ):
        assert features.values[name] is None
        assert name in features.unavailable
    assert row.hint_count == 1 and row.task_duration_seconds == 30.0


def test_external_label_changes_cannot_change_predictor_values():
    a = ResearchObservation(**synthetic_observation())
    b = ResearchObservation(
        **synthetic_observation(
            difficulty_label=synthetic_label(
                "high", source="test", rubric_version="another-test-rubric"
            ),
            mastery_label=None,
        )
    )
    assert extract_research_features(a) == extract_research_features(b)


def synthetic_task(task_id, order, steps, correct, **overrides):
    return dict(
        student_code="SYNTHETIC-learner-0",
        session_id="SYNTHETIC-session-0",
        learning_cycle_id="SYNTHETIC-cycle",
        game_type="drag_drop",
        task_id=task_id,
        task_order=order,
        difficulty="easy",
        concept="SYNTHETIC-concept-0",
        total_steps=steps,
        first_attempt_correct_steps=correct,
        wrong_attempts=steps - correct,
        retry_count=steps - correct,
        hint_requests=1,
        steps_with_hints=1,
        task_duration_seconds=10.0,
        task_completed=True,
        hint_observation_complete=True,
        task_duration_reliable=True,
        **overrides,
    )


@pytest.fixture
def aggregate_inputs():
    context = ObservationContext(
        **{
            key: value
            for key, value in synthetic_observation().items()
            if key in ObservationContext.model_fields
        }
    )
    return context, [synthetic_task("t1", 1, 2, 1), synthetic_task("t2", 2, 8, 6)]


def test_aggregation_weights_planned_steps_and_retains_final_tasks(aggregate_inputs):
    context, tasks = aggregate_inputs
    row = aggregate_observation(
        tasks,
        context=context,
        difficulty_label=IndependentLabel(**synthetic_label()),
        first_attempt_observation_complete=True,
        skipped_steps_by_task={"t1": 0, "t2": 0},
    )
    assert row.gameplay_score == 0.7  # (1 + 6) / (2 + 8), not mean(.5, .75)
    assert row.tasks_total == row.tasks_completed == 2
    assert row.wrong_attempts == row.retry_count == 3
    assert row.hint_count == row.steps_with_hints == 2
    assert row.skipped_steps == 0 and row.task_duration_seconds == 20.0


def test_aggregation_does_not_silently_sum_partial_metrics(aggregate_inputs):
    context, tasks = aggregate_inputs
    tasks[1]["wrong_attempts"] = None
    tasks[1]["task_duration_reliable"] = False
    row = aggregate_observation(
        tasks,
        context=context,
        difficulty_label=None,
        first_attempt_observation_complete=True,
    )
    assert row.wrong_attempts is None and row.skipped_steps is None
    assert row.task_duration_seconds is None and not row.task_duration_reliable
    assert row.difficulty_label is None


def test_aggregation_keeps_abandoned_tasks_in_denominator(aggregate_inputs):
    context, tasks = aggregate_inputs
    tasks[1]["task_completed"] = False
    row = aggregate_observation(
        tasks,
        context=context,
        difficulty_label=None,
        first_attempt_observation_complete=True,
    )
    assert row.total_steps == 10 and row.tasks_total == 2 and row.tasks_completed == 1
    assert row.task_completed is False
    assert extract_research_features(row).values["completion_rate"] == 0.5


@pytest.mark.parametrize(
    "skipped", [{"t1": 0}, {"t1": 0, "t2": -1}, {"t1": 0, "t2": True}]
)
def test_aggregation_rejects_incomplete_or_invalid_skipped_evidence(
    aggregate_inputs, skipped
):
    context, tasks = aggregate_inputs
    with pytest.raises(ValueError, match="Skipped"):
        aggregate_observation(
            tasks, context=context, difficulty_label=None, skipped_steps_by_task=skipped
        )


def test_aggregation_refuses_cross_session_tasks(aggregate_inputs):
    context, tasks = aggregate_inputs
    tasks[1]["session_id"] = "another-session"
    with pytest.raises(ValueError, match="context"):
        aggregate_observation(tasks, context=context, difficulty_label=None)


@pytest.mark.parametrize(
    "classifier", ["logistic_regression", "decision_tree", "random_forest"]
)
def test_three_classifiers_use_identical_paired_cohort_split_and_parameters(
    synthetic_rows, classifier
):
    settings = ExperimentConfig(
        class_labels=CLASSES,
        classifier=classifier,
        classifier_parameters={"n_estimators": 8}
        if classifier == "random_forest"
        else {},
    )
    result = run_comparison(
        synthetic_rows,
        settings,
        provenance="SYNTHETIC classifier test",
        data_kind="synthetic_development",
    )
    a, b = result.models.values()
    assert a.metadata["split"] == b.metadata["split"] == result.report["split"]
    assert a.metadata["classifier_parameters"] == b.metadata["classifier_parameters"]
    assert a.metadata["counts"] == b.metadata["counts"]
    assert a.metadata["label_provenance"] == b.metadata["label_provenance"]
    assert result.report["counts"]["eligible_observations"] == 72
    assert result.report["split"]["train"]["learners"] == 9
    assert result.report["split"]["test"]["learners"] == 3
    train_groups = set(result.report["split"]["train"]["learner_sha256"])
    test_groups = set(result.report["split"]["test"]["learner_sha256"])
    assert train_groups.isdisjoint(test_groups)
    assert result.report["primary_metric"] == "macro_f1"
    assert result.report["macro_f1_difference_b_minus_a"] > 0
    assert result.report["behaviour_improved"] is True
    assert "not_assessed" in result.report["statistical_significance"]
    for metrics in result.report["models"].values():
        assert np.asarray(metrics["confusion_matrix"]).shape == (3, 3)
        assert np.asarray(metrics["confusion_matrix"]).sum() == 18


def test_missing_behaviour_never_filters_model_b_participants(synthetic_rows, config):
    synthetic_rows[0]["difficulty_label"] = None
    synthetic_rows[1]["first_attempt_observation_complete"] = False
    for row in synthetic_rows:
        row.update(
            wrong_attempts=None,
            retry_count=None,
            hint_count=None,
            steps_with_hints=None,
            hint_observation_complete=False,
            skipped_steps=None,
            task_duration_reliable=False,
        )
    result = run_comparison(
        synthetic_rows,
        config,
        provenance="SYNTHETIC missing metrics",
        data_kind="synthetic_development",
    )
    a, b = result.models.values()
    assert (
        a.metadata["counts"]["eligible_observations"]
        == b.metadata["counts"]["eligible_observations"]
        == 70
    )
    assert result.report["counts"]["exclusions"] == {
        "independent_target_label_unavailable": 1,
        "audited_gameplay_score_unavailable": 1,
    }
    assert a.metadata["split"] == b.metadata["split"]
    assert b.metadata["missing_feature_counts"]["wrong_attempts"] == 70


def test_no_improvement_is_reported_honestly(synthetic_rows, config):
    for row in synthetic_rows:
        row.update(
            wrong_attempts=5,
            retry_count=5,
            hint_count=1,
            steps_with_hints=1,
            task_duration_seconds=30.0,
        )
    result = run_comparison(
        synthetic_rows,
        config,
        provenance="SYNTHETIC no-signal behaviour",
        data_kind="synthetic_development",
    )
    assert result.report["macro_f1_difference_b_minus_a"] == 0
    assert result.report["behaviour_improved"] is False
    assert result.report["comparison_outcome"] == "no_change"
    assert "did not improve" in result.report["interpretation"]


def test_optional_mastery_uses_its_own_independent_labels(synthetic_rows):
    settings = ExperimentConfig(target="mastery", class_labels=("developing", "secure"))
    result = run_comparison(
        synthetic_rows,
        settings,
        provenance="SYNTHETIC mastery",
        data_kind="synthetic_development",
    )
    for run in result.models.values():
        assert run.metadata["target"] == "mastery"
        assert set(run.metadata["evaluation"]["per_class"]) == {"developing", "secure"}
        assert all(
            label["source"] == "quiz" for label in run.metadata["label_provenance"]
        )


def test_unknown_target_labels_are_rejected(synthetic_rows, config):
    synthetic_rows[0]["difficulty_label"]["value"] = "unconfigured"
    with pytest.raises(TrainingDataError, match="Unknown"):
        prepare_cohort(synthetic_rows, config)


@pytest.mark.parametrize("failure", ["single_class", "too_small", "missing_score"])
def test_inadequate_datasets_fail(synthetic_rows, config, failure):
    if failure == "single_class":
        for row in synthetic_rows:
            row["difficulty_label"]["value"] = "low"
    elif failure == "too_small":
        synthetic_rows = synthetic_rows[:6]
    else:
        for row in synthetic_rows:
            row["first_attempt_observation_complete"] = False
    with pytest.raises(TrainingDataError):
        run_comparison(
            synthetic_rows,
            config,
            provenance="SYNTHETIC invalid",
            data_kind="synthetic_development",
        )


def test_missing_classes_fail_by_default_and_are_explicit_when_allowed(
    synthetic_rows, config
):
    rows = [row for row in synthetic_rows if row["difficulty_label"]["value"] != "high"]
    with pytest.raises(TrainingDataError, match="missing configured classes"):
        run_comparison(
            rows,
            config,
            provenance="SYNTHETIC incomplete classes",
            data_kind="synthetic_development",
        )
    settings = ExperimentConfig(
        class_labels=CLASSES, evaluation={"require_all_classes_in_partitions": False}
    )
    result = run_comparison(
        rows,
        settings,
        provenance="SYNTHETIC explicit incomplete classes",
        data_kind="synthetic_development",
    )
    assert result.report["split"]["test"]["missing_classes"] == ["high"]
    assert result.report["models"]["score_only"]["per_class"]["high"]["support"] == 0


def test_multiclass_metrics_include_every_configured_class():
    result = evaluate_research(
        np.array(["a", "b", "c", "a"]), np.array(["a", "c", "c", "b"]), ("a", "b", "c")
    )
    assert result["confusion_matrix"] == [[1, 1, 0], [0, 0, 1], [0, 0, 1]]
    assert result["macro_f1"] == pytest.approx(4 / 9)
    assert result["per_class"]["a"]["precision"] == 1
    assert result["per_class"]["c"]["recall"] == 1
    with pytest.raises(ValueError, match="outside"):
        evaluate_research(np.array(["a"]), np.array(["unknown"]), ("a", "b"))


def test_binary_metrics_use_configured_names_and_class_order():
    result = evaluate_research(
        np.array(["no", "yes", "yes"]), np.array(["no", "no", "yes"]), ("no", "yes")
    )
    assert result["confusion_matrix"] == [[1, 0], [1, 1]]
    assert result["macro_f1"] == pytest.approx(2 / 3)
    assert result["balanced_accuracy"] == 0.75


def test_preprocessing_fits_only_training_observations(synthetic_rows):
    settings = ExperimentConfig(class_labels=CLASSES, common_context=("concept",))
    cohort = prepare_cohort(synthetic_rows, settings)
    split = learner_split(cohort, settings)
    heldout = {cohort.rows[i].student_code for i in split.test}
    for row in synthetic_rows:
        if row["student_code"] in heldout:
            row["task_duration_seconds"] = 2000.0
            row["concept"] = "HELDOUT-" + row["concept"]
            for target in ("difficulty_label", "mastery_label"):
                row[target]["concept"] = row["concept"]
    result = run_comparison(
        synthetic_rows,
        settings,
        provenance="SYNTHETIC leakage test",
        data_kind="synthetic_development",
    )
    run = result.models["score_plus_behaviour"]
    numeric = run.model.named_steps["preprocess"].named_transformers_["numeric"]
    index = feature_set("score_plus_behaviour").numeric.index("task_duration_seconds")
    assert numeric.named_steps["impute"].statistics_[index] < 100
    assert numeric.named_steps["scale"].mean_[index] < 100
    encoder = (
        run.model.named_steps["preprocess"]
        .named_transformers_["categorical"]
        .named_steps["encode"]
    )
    assert all(
        not category.startswith("HELDOUT-") for category in encoder.categories_[0]
    )


def test_configured_context_and_parameters_are_validated():
    for overrides in (
        {"common_context": ("student_code",)},
        {"classifier": "unsupported"},
        {"class_labels": ("same", "same")},
        {"classifier_parameters": {"random_state": 0}},
    ):
        with pytest.raises(ValidationError):
            ExperimentConfig(**{"class_labels": CLASSES, **overrides})


def test_corrupt_split_manifest_is_rejected(synthetic_rows, config):
    cohort = prepare_cohort(synthetic_rows, config)
    with pytest.raises(ValueError, match="partition"):
        fit_experiment(
            cohort,
            ResearchSplit((0,), (0,), {}),
            config,
            "score_only",
            provenance="SYNTHETIC invalid split",
            data_kind="synthetic_development",
        )


def test_cohort_target_cannot_be_reused_as_a_different_target(synthetic_rows, config):
    cohort = prepare_cohort(synthetic_rows, config)
    split = learner_split(cohort, config)
    mastery = ExperimentConfig(target="mastery", class_labels=("developing", "secure"))
    with pytest.raises(ValueError, match="Cohort target"):
        fit_experiment(
            cohort,
            split,
            mastery,
            "score_only",
            provenance="SYNTHETIC mismatch",
            data_kind="synthetic_development",
        )


def test_reversed_input_has_identical_split_features_and_results(
    synthetic_rows, comparison, config
):
    again = run_comparison(
        list(reversed(synthetic_rows)),
        config,
        provenance="SYNTHETIC repeat",
        data_kind="synthetic_development",
    )
    assert comparison.report["split"] == again.report["split"]
    assert comparison.report["models"] == again.report["models"]
    assert (
        comparison.report["training_data"]["canonical_dataset_sha256"]
        == again.report["training_data"]["canonical_dataset_sha256"]
    )


def test_provenance_and_local_artifact_roundtrip(tmp_path, comparison, synthetic_rows):
    destination = save_comparison(comparison, tmp_path / "SYNTHETIC-comparison")
    for name, original in comparison.models.items():
        run = load_research_artifact(
            destination / name,
            target="difficulty",
            classifier="logistic_regression",
            trusted_local_artifact=True,
        )
        assert predict_research(run, synthetic_rows[0]) == predict_research(
            original, synthetic_rows[0]
        )
        metadata = run.metadata
        assert metadata["training_data"]["kind"] == "synthetic_development"
        assert (
            metadata["label_provenance"][0]["rubric_version"]
            == "SYNTHETIC-test-rubric-v1"
        )
        assert (
            metadata["label_provenance"][0]["source_reference"]
            == "SYNTHETIC-independent-assessment"
        )
        assert "runtime_versions" in metadata and "trained_at_utc" in metadata
        assert "SYNTHETIC-learner-0" not in json.dumps(metadata)
        with pytest.raises(ValueError, match="trusted_local_artifact"):
            load_research_artifact(
                destination / name,
                target="difficulty",
                classifier="logistic_regression",
            )
        with pytest.raises(ValueError, match="version"):
            load_artifact(
                destination / name, trusted_local_artifact=True
            )  # Auxiliary loader defaults preserved.
    with pytest.raises(FileExistsError):
        save_comparison(comparison, destination)
    assert (
        json.loads((destination / "comparison.json").read_text())["primary_metric"]
        == "macro_f1"
    )


def test_research_inference_ignores_labels_and_accepts_unseen_context(
    comparison, synthetic_rows
):
    run = comparison.models["score_plus_behaviour"]
    first = predict_research(run, synthetic_rows[0])
    changed = {
        **synthetic_rows[0],
        "difficulty_label": None,
        "mastery_label": None,
        "game_type": "future-mode",
    }
    assert predict_research(run, changed) == first  # Context is excluded by default.
    assert set(first["class_probabilities"]) == set(CLASSES)
    assert sum(first["class_probabilities"].values()) == pytest.approx(1)


def test_generated_schema_matches_python_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "app/modules/game/ml/research_dataset.schema.json"
    )
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved.pop("$schema")
    assert saved == ResearchObservation.model_json_schema()


def test_research_cli_creates_pair_and_refuses_overwrite(
    tmp_path, synthetic_rows, config
):
    dataset, settings = (
        tmp_path / "SYNTHETIC-observations.json",
        tmp_path / "config.json",
    )
    dataset.write_text(json.dumps(synthetic_rows), encoding="utf-8")
    settings.write_text(config.model_dump_json(), encoding="utf-8")
    output = tmp_path / "SYNTHETIC-paired-models"
    command = [
        sys.executable,
        "-m",
        "app.modules.game.ml.research_cli",
        "--dataset",
        str(dataset),
        "--config",
        str(settings),
        "--output",
        str(output),
        "--provenance",
        "SYNTHETIC CLI test",
        "--data-kind",
        "synthetic_development",
    ]
    result = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["counts"]["eligible_observations"] == 72
    result = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True
    )
    assert result.returncode == 2 and "already exists" in result.stderr


def test_utc_dates_survive_export_roundtrip():
    row = ResearchObservation(**synthetic_observation())
    restored = ResearchObservation.model_validate_json(row.model_dump_json())
    assert restored.observation_ended_at == datetime(2026, 10, 12, 10, tzinfo=UTC)
    assert restored.gameplay_score == 0.5
