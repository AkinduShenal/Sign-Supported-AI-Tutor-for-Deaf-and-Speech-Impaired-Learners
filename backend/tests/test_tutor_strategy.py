import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.game.models import GameResult
from app.modules.quiz.models import QuizResult
from app.modules.tutor.schemas import TutorStrategyRequest
from app.modules.tutor.service import TutorStrategyService
from app.modules.tutor.models import TutorStrategyPrediction


test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


def override_get_db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def make_request_payload() -> dict:
    return {
        "student_id": "STU001",
        "concept_id": "linear_equations",
        "quiz": {
            "quiz_session_id": "QUIZ-001",
            "weak_concept": "linear_equation_balancing",
            "quiz_mastery_score": 0.35,
            "recommended_support_level": "high",
            "questions_total": 10,
            "questions_attempted": 10,
            "correct_answers": 4,
            "quiz_accuracy": 0.4,
            "quiz_avg_response_time_sec": 42.5,
            "quiz_hint_rate": 0.7,
            "misconception_code": "inverse_operation",
            "quiz_difficulty_level": "beginner",
            "quiz_attempt_count": 2,
            "completed_at": "2026-09-26T10:30:00Z",
        },
        "game": {
            "game_session_id": "GAME-001",
            "engagement_level": "medium",
            "behavioral_difficulty": "high",
            "hint_dependency": 0.7,
            "game_mastery_score": 0.4,
            "tasks_total": 10,
            "tasks_attempted": 8,
            "tasks_completed": 7,
            "successful_tasks": 4,
            "game_success_rate": 0.5,
            "game_completion_rate": 0.7,
            "game_avg_attempts_per_task": 2.5,
            "game_hint_rate": 0.6,
            "game_difficulty_level": "beginner",
            "game_active_time_sec": 420,
            "completed_at": "2026-09-26T11:00:00Z",
        },
        "learner": {
            "prior_mastery_score": 0.35,
            "preferred_mode": "visual",
            "sign_support_required": True,
        },
    }


def test_recommends_step_by_step_for_low_performance() -> None:
    response = client.post("/api/v1/tutor/strategy", json=make_request_payload())

    assert response.status_code == 200
    response_body = response.json()
    uuid.UUID(response_body.pop("prediction_id"))
    uuid.UUID(response_body.pop("quiz_result_id"))
    uuid.UUID(response_body.pop("game_result_id"))
    assert response_body == {
        "student_id": "STU001",
        "concept_id": "linear_equations",
        "primary_strategy": "step_by_step",
        "supporting_strategies": [
            "worked_example_based",
            "progressive_hints",
        ],
        "confidence": 1.0,
        "preferred_mode": "visual",
        "sign_support_required": True,
        "model_version": "rule-based-v2",
    }


def test_recommends_advanced_challenge_for_high_performance() -> None:
    payload = make_request_payload()
    payload["quiz"].update(
        {
            "quiz_mastery_score": 0.9,
            "recommended_support_level": "low",
            "correct_answers": 9,
            "quiz_accuracy": 0.9,
            "quiz_avg_response_time_sec": 15,
            "quiz_hint_rate": 0.1,
            "misconception_code": "none",
            "quiz_difficulty_level": "advanced",
        }
    )
    payload["game"].update(
        {
            "engagement_level": "high",
            "behavioral_difficulty": "low",
            "hint_dependency": 0.1,
            "game_mastery_score": 0.9,
            "successful_tasks": 7,
            "game_success_rate": 0.9,
            "game_completion_rate": 0.9,
            "game_avg_attempts_per_task": 1.2,
            "game_hint_rate": 0.1,
            "game_difficulty_level": "advanced",
        }
    )
    payload["learner"]["prior_mastery_score"] = 0.9

    response = client.post("/api/v1/tutor/strategy", json=payload)

    assert response.status_code == 200
    assert response.json()["primary_strategy"] == "advanced_challenge"
    assert response.json()["supporting_strategies"] == []


def test_rejects_inconsistent_quiz_counts() -> None:
    payload = make_request_payload()
    payload["quiz"]["correct_answers"] = 11

    response = client.post("/api/v1/tutor/strategy", json=payload)

    assert response.status_code == 422


def test_rejects_invalid_diagnostic_model_score() -> None:
    payload = make_request_payload()
    payload["game"]["game_mastery_score"] = 1.2

    response = client.post("/api/v1/tutor/strategy", json=payload)

    assert response.status_code == 422


def test_persists_quiz_game_and_prediction_records() -> None:
    response = client.post("/api/v1/tutor/strategy", json=make_request_payload())

    assert response.status_code == 200
    with Session(test_engine) as database:
        assert database.scalar(select(func.count()).select_from(QuizResult)) == 1
        assert database.scalar(select(func.count()).select_from(GameResult)) == 1
        assert (
            database.scalar(
                select(func.count()).select_from(TutorStrategyPrediction)
            )
            == 1
        )
        prediction = database.scalar(select(TutorStrategyPrediction))
        assert prediction is not None
        assert prediction.primary_strategy == "step_by_step"
        assert prediction.supporting_strategies == [
            "worked_example_based",
            "progressive_hints",
        ]
        quiz_result = database.scalar(select(QuizResult))
        assert quiz_result is not None
        assert quiz_result.weak_concept == "linear_equation_balancing"
        assert quiz_result.quiz_mastery_score == 0.35
        assert quiz_result.recommended_support_level == "high"
        game_result = database.scalar(select(GameResult))
        assert game_result is not None
        assert game_result.engagement_level == "medium"
        assert game_result.behavioral_difficulty == "high"
        assert game_result.hint_dependency == 0.7
        assert game_result.game_mastery_score == 0.4


def test_duplicate_session_payload_is_idempotent() -> None:
    first_response = client.post(
        "/api/v1/tutor/strategy",
        json=make_request_payload(),
    )
    second_response = client.post(
        "/api/v1/tutor/strategy",
        json=make_request_payload(),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["prediction_id"] == first_response.json()[
        "prediction_id"
    ]
    with Session(test_engine) as database:
        assert database.scalar(select(func.count()).select_from(QuizResult)) == 1
        assert database.scalar(select(func.count()).select_from(GameResult)) == 1
        assert (
            database.scalar(
                select(func.count()).select_from(TutorStrategyPrediction)
            )
            == 1
        )


def test_changed_duplicate_session_payload_returns_conflict() -> None:
    first_response = client.post(
        "/api/v1/tutor/strategy",
        json=make_request_payload(),
    )
    changed_payload = make_request_payload()
    changed_payload["quiz"]["quiz_hint_rate"] = 0.2

    second_response = client.post(
        "/api/v1/tutor/strategy",
        json=changed_payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_rolls_back_all_records_when_prediction_fails() -> None:
    class FailingStrategyModel:
        def predict(self, request: TutorStrategyRequest) -> None:
            raise RuntimeError("Prediction failed")

    request = TutorStrategyRequest.model_validate(make_request_payload())
    database = TestingSessionLocal()
    failing_service = TutorStrategyService(model=FailingStrategyModel())

    try:
        with pytest.raises(RuntimeError, match="Prediction failed"):
            failing_service.recommend(request, database)
    finally:
        database.close()

    with Session(test_engine) as verification_database:
        assert (
            verification_database.scalar(
                select(func.count()).select_from(QuizResult)
            )
            == 0
        )
        assert (
            verification_database.scalar(
                select(func.count()).select_from(GameResult)
            )
            == 0
        )
        assert (
            verification_database.scalar(
                select(func.count()).select_from(TutorStrategyPrediction)
            )
            == 0
        )
