from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.tutor.adaptive_lesson import (
    LEVELS,
    PRACTICE,
    _example,
    preview_lesson,
    plan_lesson,
)
from app.modules.tutor.schemas import TutorStrategyRequest, TutoringStrategy
from app.modules.tutor.strategy_model import StrategyPrediction
from test_tutor_strategy import make_request_payload

client = TestClient(app)


@pytest.mark.parametrize("level", LEVELS)
def test_level_has_distinct_content_complete_glossary_and_hints(level):
    response = client.get(f"/api/v1/tutor/grade10/{level}")
    assert response.status_code == 200
    lesson = response.json()
    assert lesson["plan"]["source"] == "preview"
    assert lesson["plan"]["model_version"] == "preview-no-inference"
    assert len(lesson["worked_examples"]) >= 2
    glossary = {s["sign_id"] for s in lesson["sign_glossary"]}
    for example in lesson["worked_examples"]:
        assert [step["order"] for step in example["steps"]] == list(
            range(1, len(example["steps"]) + 1)
        )
        assert any("Substitute" in step["instruction"] for step in example["steps"])
        for step in example["steps"]:
            assert set(step["sign_actions"]) <= glossary
    assert all(len(q["progressive_hints"]) == 3 for q in lesson["practice_questions"])
    assert not any(
        s["validation_status"] == "validated" for s in lesson["sign_glossary"]
    )
    review_animations = [
        sign
        for sign in lesson["sign_glossary"]
        if sign["animation_type"]
        == "composite_prototype_educational_gesture"
    ]
    assert len(review_animations) == 34
    assert all(sign["prototype_ready"] for sign in review_animations)
    assert {"ALGEBRA", "BRACKET", "COEFFICIENT", "HINT", "CORRECT"} <= {
        sign["sign_id"] for sign in review_animations
    }


def test_low_diagnostic_receives_scaffolding_not_a_claimed_ml_prediction():
    response = client.post("/api/v1/tutor/adaptive-lesson", json=make_request_payload())
    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["level"] == "foundation"
    assert plan["primary_strategy"] == "step_by_step"
    assert plan["model_version"] == "rule-based-v2"
    assert "Undo addition" in plan["misconception_support"]


def test_advanced_diagnostic_gets_both_sides_brackets_and_fractions():
    payload = make_request_payload()
    payload["quiz"].update(
        quiz_mastery_score=0.95,
        quiz_hint_rate=0,
        recommended_support_level="low",
        quiz_difficulty_level="advanced",
        misconception_code="none",
    )
    payload["game"].update(
        game_mastery_score=0.95,
        hint_dependency=0,
        behavioral_difficulty="low",
        game_avg_attempts_per_task=1,
    )
    payload["learner"]["prior_mastery_score"] = 0.95
    body = client.post("/api/v1/tutor/adaptive-lesson", json=payload).json()
    assert body["plan"]["level"] == "extended"
    assert body["plan"]["primary_strategy"] == "advanced_challenge"
    assert [e["problem"] for e in body["worked_examples"]] == [
        "3x + 2 = x + 10",
        "2(x + 3) = 14",
        "x/3 + 2 = 5",
        "-2x + 3 = 8",
    ]


def test_predictor_is_injectable_and_accessibility_is_preserved():
    class TestPredictor:
        version = "test-model"

        def predict(self, request):
            return StrategyPrediction(TutoringStrategy.CONCEPTUAL_EXPLANATION, (), 0.8)

    payload = make_request_payload()
    payload["learner"].update(sign_support_required=False, preferred_mode="text")
    plan = plan_lesson(
        TutorStrategyRequest.model_validate(payload), TestPredictor()
    ).plan
    assert plan.model_version == "test-model"
    assert plan.primary_strategy == "conceptual_explanation"
    assert plan.sign_support_required is False
    assert plan.preferred_mode == "text"


def test_refuses_out_of_scope_and_bad_inputs():
    payload = make_request_payload()
    payload["quiz"]["weak_concept"] = "geometry"
    assert client.post("/api/v1/tutor/adaptive-lesson", json=payload).status_code == 422
    assert client.post("/api/v1/tutor/adaptive-lesson", json={}).status_code == 422
    assert client.get("/api/v1/tutor/grade10/unknown").status_code == 422
    assert (
        client.post(
            "/api/v1/tutor/practice/check",
            json={"question_id": "unknown", "answer": "3"},
        ).status_code
        == 404
    )


@pytest.mark.parametrize("answer", ["-5/2", "x = -2.5", "−2.50", "-10/4"])
def test_equivalent_fraction_answers_are_accepted(answer):
    result = client.post(
        "/api/v1/tutor/practice/check",
        json={"question_id": "g10-v1-extended-2", "answer": answer},
    )
    assert result.status_code == 200
    assert result.json()["correct"] is True


@pytest.mark.parametrize(
    "answer", ["NaN", "inf", "__import__('os')", "1/0", "2.5", "x=2=3"]
)
def test_invalid_or_incorrect_answers_are_safe(answer):
    assert (
        client.post(
            "/api/v1/tutor/practice/check",
            json={"question_id": "g10-v1-extended-2", "answer": answer},
        ).json()["correct"]
        is False
    )


def test_every_practice_answer_satisfies_original_equation():
    for level, equations in PRACTICE.items():
        for question, (a, b, c, d) in zip(
            preview_lesson(level).practice_questions, equations, strict=True
        ):
            x = Fraction(question.expected_answer.split("=")[1].strip())
            assert a * x + b == c * x + d


def test_generated_equations_verify_original_sides_and_never_invent_fraction_signs():
    for a in (-3, -1, 1, 2, 4):
        for c in (0, 1, 2):
            if a == c:
                continue
            example = _example(a, 3, c, 8)
            x = Fraction(example.answer.split("=")[1].strip())
            assert a * x + 3 == c * x + 8
            assert example.steps[-2].expression == f"{a * x + 3} = {c * x + 8}"
            if x < 0 or x.denominator != 1:
                assert not any(
                    action.startswith("NUMBER_")
                    for action in example.steps[-3].sign_actions
                )


def test_slow_response_time_is_not_an_ability_penalty():
    payload = make_request_payload()
    first = plan_lesson(TutorStrategyRequest.model_validate(payload)).plan
    payload["quiz"]["quiz_avg_response_time_sec"] = 9999
    assert plan_lesson(TutorStrategyRequest.model_validate(payload)).plan == first


def test_sign_misconception_selects_negative_constant_example_first():
    payload = make_request_payload()
    payload["quiz"]["misconception_code"] = "sign_error"
    lesson = plan_lesson(TutorStrategyRequest.model_validate(payload))
    assert lesson.worked_examples[0].problem == "x - 4 = 2"
    assert "Keep the sign" in lesson.plan.misconception_support


@pytest.mark.parametrize(
    "score,level",
    [(0.49, "foundation"), (0.5, "one_step"), (0.69, "one_step"), (0.7, "two_step")],
)
def test_draft_placement_boundaries(score, level):
    class FixedPredictor:
        version = "test-model"

        def predict(self, request):
            return StrategyPrediction(TutoringStrategy.WORKED_EXAMPLE_BASED, (), 0.8)

    payload = make_request_payload()
    payload["quiz"]["quiz_mastery_score"] = score
    payload["game"]["game_mastery_score"] = score
    payload["learner"]["prior_mastery_score"] = score
    assert (
        plan_lesson(
            TutorStrategyRequest.model_validate(payload), FixedPredictor()
        ).plan.level
        == level
    )
