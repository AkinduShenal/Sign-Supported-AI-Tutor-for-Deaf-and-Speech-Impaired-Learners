import json
import shutil

import joblib
import pandas as pd
import pytest

from app.modules.tutor.schemas import TutorStrategyRequest
from app.modules.tutor.strategy_model import (
    ARTIFACT_DIRECTORY, TrainedStrategyModel, get_strategy_model,
)
from test_tutor_strategy import make_request_payload


@pytest.mark.parametrize("label,mastery,hints,attempts,misconception,support", [
    ("advanced_challenge", .95, .1, 1., "none", "low"),
    ("conceptual_explanation", .25, .1, 1., "concept_confusion", "medium"),
    ("progressive_hints", .95, .8, 3., "inverse_operation", "medium"),
    ("step_by_step", .25, .8, 3., "inverse_operation", "high"),
    ("worked_example_based", .55, .8, 3., "arithmetic_error", "medium"),
])
def test_all_five_exported_labels_and_confidence_match_original_pipeline(
    label, mastery, hints, attempts, misconception, support,
):
    payload = make_request_payload()
    difficulty = "advanced" if mastery > .8 else "beginner" if mastery < .5 else "intermediate"
    game_difficulty = "advanced" if mastery > .8 else "intermediate"
    payload["quiz"].update(
        quiz_mastery_score=mastery, quiz_hint_rate=hints, misconception_code=misconception,
        quiz_difficulty_level=difficulty, recommended_support_level=support,
    )
    payload["game"].update(
        game_mastery_score=mastery, hint_dependency=hints,
        game_avg_attempts_per_task=attempts, game_difficulty_level=game_difficulty,
    )
    payload["learner"]["prior_mastery_score"] = mastery
    # Independent frame verifies feature sources as well as probability class order.
    original_input = pd.DataFrame([{
        "quiz_mastery_score": mastery, "quiz_hint_rate": hints,
        "game_mastery_score": mastery, "game_avg_attempts_per_task": attempts,
        "hint_dependency": hints, "prior_mastery_score": mastery,
        "misconception_code": misconception, "quiz_difficulty_level": difficulty,
        "recommended_support_level": support, "game_difficulty_level": game_difficulty,
        "engagement_level": "medium",
    }])
    original = joblib.load(ARTIFACT_DIRECTORY / "teaching_strategy_model.joblib")
    prediction = get_strategy_model().predict(TutorStrategyRequest.model_validate(payload))
    assert prediction.primary_strategy.value == label == original.predict(original_input)[0]
    assert prediction.confidence == pytest.approx(original.predict_proba(original_input).max())
    assert prediction.supporting_strategies == ()


def test_backend_unseen_category_uses_exported_encoder_policy():
    payload = make_request_payload()
    payload["quiz"]["misconception_code"] = "sign_error"
    prediction = get_strategy_model().predict(TutorStrategyRequest.model_validate(payload))
    assert 0 < prediction.confidence < 1


def test_missing_artifact_fails_instead_of_silently_using_rules(tmp_path):
    with pytest.raises(FileNotFoundError):
        TrainedStrategyModel(tmp_path)


def test_mismatched_metadata_is_rejected(tmp_path):
    metadata = json.loads((ARTIFACT_DIRECTORY / "teaching_strategy_model_metadata.json").read_text())
    metadata["numeric_features"].remove("prior_mastery_score")
    (tmp_path / "teaching_strategy_model_metadata.json").write_text(json.dumps(metadata))
    shutil.copyfile(ARTIFACT_DIRECTORY / "teaching_strategy_model.joblib", tmp_path / "teaching_strategy_model.joblib")
    with pytest.raises(ValueError, match="metadata does not match"):
        TrainedStrategyModel(tmp_path)
