import uuid

import pytest
from sqlalchemy import func, select

from app.modules.game.models import GameResult
from app.modules.quiz.models import QuizResult
from app.modules.tutor.models import TutorStrategyPrediction
from app.modules.tutor.schemas import TutorStrategyRequest
from app.modules.tutor.strategy_model import get_strategy_model
from test_tutor_strategy import (
    TestingSessionLocal, client, make_request_payload, seed_results,
)
from test_tutor_strategy import reset_database as reset_database

# Use the FK-enforcing, isolated database fixture, never the configured shared DB.
pytestmark = pytest.mark.usefixtures("reset_database")


def reference():
    return {"student_id": "STU001", "concept_id": "linear_equations",
            "learning_cycle_id": str(uuid.uuid4())}


def seed_cycle(ref):
    payload = make_request_payload()
    seed_results(payload)
    with TestingSessionLocal() as database:
        for model in (QuizResult, GameResult):
            row = database.scalar(select(model))
            row.learning_cycle_id = uuid.UUID(ref["learning_cycle_id"])
            row.assessment_phase = "pre_tutor"
        database.commit()
    return payload


def test_auto_lesson_uses_saved_quiz_prior_and_persists_the_model_decision():
    ref = reference()
    payload = seed_cycle(ref)
    status = client.get("/api/v1/tutor/learning-status", params=ref)
    assert status.json() == {"quiz_complete": True, "game_complete": True, "ready": True}
    response = client.post("/api/v1/tutor/adaptive-lesson/from-results", json=ref)
    assert response.status_code == 200
    plan = response.json()["plan"]
    expected = get_strategy_model().predict(TutorStrategyRequest.model_validate(payload))
    assert plan["primary_strategy"] == expected.primary_strategy.value
    assert plan["confidence"] == pytest.approx(expected.confidence)
    assert plan["source"] == "diagnostic"
    assert plan["model_version"] == "strategy-ml-v1"
    assert plan["prior_mastery_source"] == "pre_tutor_quiz"
    with TestingSessionLocal() as database:
        saved = database.scalar(select(TutorStrategyPrediction))
        assert str(saved.id) == plan["prediction_id"]
        assert saved.input_snapshot["learner"]["prior_mastery_score"] == .35
        assert saved.input_snapshot["quiz"]["quiz_mastery_score"] == .35
        assert database.scalar(select(func.count()).select_from(QuizResult)) == 1
        assert database.scalar(select(func.count()).select_from(GameResult)) == 1
    again = client.post("/api/v1/tutor/adaptive-lesson/from-results", json=ref)
    assert again.json()["plan"]["prediction_id"] == plan["prediction_id"]


@pytest.mark.parametrize("missing", ["quiz", "game", "both"])
def test_missing_evidence_returns_progress_without_any_default_strategy(missing):
    ref = reference()
    seed_cycle(ref)
    with TestingSessionLocal() as database:
        for kind, model in (("quiz", QuizResult), ("game", GameResult)):
            if missing in (kind, "both"):
                # Other-cycle records must not be borrowed for this lesson.
                database.scalar(select(model)).learning_cycle_id = uuid.uuid4()
        database.commit()
    status = client.get("/api/v1/tutor/learning-status", params=ref).json()
    assert status == {"quiz_complete": missing not in ("quiz", "both"),
                      "game_complete": missing not in ("game", "both"), "ready": False}
    assert client.post("/api/v1/tutor/adaptive-lesson/from-results", json=ref).status_code == 404
    with TestingSessionLocal() as database:
        assert database.scalar(select(func.count()).select_from(TutorStrategyPrediction)) == 0


@pytest.mark.parametrize("field,value", [("student_id", "OTHER"), ("learning_cycle_id", str(uuid.uuid4()))])
def test_automatic_flow_never_uses_another_learner_or_cycle(field, value):
    ref = reference()
    seed_cycle(ref)
    ref[field] = value
    assert client.get("/api/v1/tutor/learning-status", params=ref).json()["ready"] is False
    assert client.post("/api/v1/tutor/adaptive-lesson/from-results", json=ref).status_code == 404


def test_automatic_flow_excludes_post_tutor_and_legacy_unlinked_results():
    ref = reference()
    seed_cycle(ref)
    with TestingSessionLocal() as database:
        database.scalar(select(QuizResult)).assessment_phase = "post_tutor"
        database.scalar(select(GameResult)).learning_cycle_id = None
        database.commit()
    assert client.get("/api/v1/tutor/learning-status", params=ref).json()["ready"] is False


@pytest.mark.parametrize("override", [
    {"primary_strategy": "advanced_challenge"}, {"prior_mastery_score": .99},
    {"learner": {"prior_mastery_score": .99}},
])
def test_student_cannot_override_model_strategy_or_prior_mastery(override):
    assert client.post("/api/v1/tutor/adaptive-lesson/from-results", json={**reference(), **override}).status_code == 422
