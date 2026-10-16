import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.game.models import GameResult, GameSession
from app.modules.quiz.models import QuizResult
from app.modules.tutor.schemas import TutorStrategyRequest
from app.modules.tutor.service import TutorStrategyService
from app.modules.tutor.models import TutorStrategyPrediction
from app.modules.tutor.strategy_model import get_strategy_model


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


@event.listens_for(test_engine, "connect")
def enable_foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")


def override_get_db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_database():
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


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


def seed_results(payload: dict) -> None:
    request = TutorStrategyRequest.model_validate(payload)
    with TestingSessionLocal() as database:
        database.add(GameSession(
            game_session_id=request.game.game_session_id,
            student_id=request.student_id, concept_id=request.concept_id,
            learning_cycle_id=uuid.uuid4(), assessment_phase="pre_tutor",
            status="completed", completed_at=request.game.completed_at,
        ))
        database.flush()
        database.add(QuizResult(
            **request.quiz.model_dump(), student_id=request.student_id,
            concept_id=request.concept_id,
        ))
        database.add(GameResult(
            **request.game.model_dump(), student_id=request.student_id,
            concept_id=request.concept_id,
        ))
        database.commit()


def test_recommends_step_by_step_for_low_performance() -> None:
    seed_results(make_request_payload())
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
        "supporting_strategies": [],
        "confidence": get_strategy_model().predict(
            TutorStrategyRequest.model_validate(make_request_payload())
        ).confidence,
        "preferred_mode": "visual",
        "sign_support_required": True,
        "model_version": "strategy-ml-v1",
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

    seed_results(payload)
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
    seed_results(make_request_payload())
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
        assert prediction.supporting_strategies == []
        assert prediction.model_version == "strategy-ml-v1"
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
    seed_results(make_request_payload())
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
    seed_results(make_request_payload())
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


def test_preserves_diagnostic_records_when_prediction_fails() -> None:
    class FailingStrategyModel:
        version = "failing-test-model"

        def predict(self, request: TutorStrategyRequest) -> None:
            raise RuntimeError("Prediction failed")

    request = TutorStrategyRequest.model_validate(make_request_payload())
    seed_results(make_request_payload())
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
            == 1
        )
        assert (
            verification_database.scalar(
                select(func.count()).select_from(GameResult)
            )
            == 1
        )
        assert (
            verification_database.scalar(
                select(func.count()).select_from(TutorStrategyPrediction)
            )
            == 0
        )


def result_reference(payload=None):
    payload = payload or make_request_payload()
    return {
        "student_id": payload["student_id"], "concept_id": payload["concept_id"],
        "quiz_session_id": payload["quiz"]["quiz_session_id"],
        "game_session_id": payload["game"]["game_session_id"],
        "learner": payload["learner"],
    }


def test_predicts_from_database_without_changing_quiz_or_game():
    seed_results(make_request_payload())
    with TestingSessionLocal() as database:
        before_quiz = database.scalar(select(QuizResult))
        before_game = database.scalar(select(GameResult))
        before = [
            {c.key: getattr(row, c.key) for c in row.__table__.columns}
            for row in (before_quiz, before_game)
        ]
    response = client.post("/api/v1/tutor/strategy/from-results", json=result_reference())
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "strategy-ml-v1"
    assert body["primary_strategy"] == "step_by_step"
    assert 0 < body["confidence"] < 1
    with TestingSessionLocal() as database:
        quiz, game = database.scalar(select(QuizResult)), database.scalar(select(GameResult))
        after = [
            {c.key: getattr(row, c.key) for c in row.__table__.columns}
            for row in (quiz, game)
        ]
        assert after == before
        saved = database.scalar(select(TutorStrategyPrediction))
        assert str(saved.quiz_result_id) == body["quiz_result_id"]
        assert str(saved.game_result_id) == body["game_result_id"]
        assert saved.input_snapshot["quiz"]["quiz_mastery_score"] == quiz.quiz_mastery_score
        assert saved.input_snapshot["game"]["game_mastery_score"] == game.game_mastery_score
        assert saved.confidence == body["confidence"]
    repeated = client.post("/api/v1/tutor/strategy/from-results", json=result_reference())
    assert repeated.json()["prediction_id"] == body["prediction_id"]
    legacy = client.post("/api/v1/tutor/strategy", json=make_request_payload())
    assert legacy.json()["prediction_id"] == body["prediction_id"]


@pytest.mark.parametrize("endpoint,payload", [
    ("/strategy", make_request_payload()),
    ("/strategy/from-results", result_reference()),
])
def test_missing_results_return_404_without_inventing_diagnostics(endpoint, payload):
    assert client.post("/api/v1/tutor" + endpoint, json=payload).status_code == 404
    with TestingSessionLocal() as database:
        for model in (QuizResult, GameResult, TutorStrategyPrediction):
            assert database.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("field,value", [
    ("student_id", "ANOTHER-STUDENT"), ("concept_id", "another_concept"),
])
def test_from_results_rejects_wrong_student_or_concept(field, value):
    seed_results(make_request_payload())
    reference = result_reference()
    reference[field] = value
    assert client.post("/api/v1/tutor/strategy/from-results", json=reference).status_code == 409


@pytest.mark.parametrize("mismatch", ["cycle", "phase"])
def test_from_results_rejects_mismatched_cycles_and_phases(mismatch):
    seed_results(make_request_payload())
    with TestingSessionLocal() as database:
        quiz, game = database.scalar(select(QuizResult)), database.scalar(select(GameResult))
        quiz.learning_cycle_id = game.learning_cycle_id = uuid.uuid4()
        quiz.assessment_phase = game.assessment_phase = "pre_tutor"
        if mismatch == "cycle":
            game.learning_cycle_id = uuid.uuid4()
        else:
            game.assessment_phase = "post_tutor"
        database.commit()
    assert client.post(
        "/api/v1/tutor/strategy/from-results", json=result_reference()
    ).status_code == 409


def test_old_rule_prediction_does_not_shadow_the_trained_model():
    seed_results(make_request_payload())
    first = client.post("/api/v1/tutor/strategy/from-results", json=result_reference()).json()
    with TestingSessionLocal() as database:
        old = database.scalar(select(TutorStrategyPrediction))
        old.model_version = "rule-based-v2"
        old.primary_strategy = "advanced_challenge"
        database.commit()
    response = client.post("/api/v1/tutor/strategy/from-results", json=result_reference())
    assert response.status_code == 200
    assert response.json()["primary_strategy"] == "step_by_step"
    assert response.json()["model_version"] == "strategy-ml-v1"
    assert response.json()["prediction_id"] != first["prediction_id"]
    with TestingSessionLocal() as database:
        assert database.scalar(select(func.count()).select_from(TutorStrategyPrediction)) == 2


def test_prior_mastery_must_be_supplied_by_caller():
    reference = result_reference()
    del reference["learner"]["prior_mastery_score"]
    assert client.post("/api/v1/tutor/strategy/from-results", json=reference).status_code == 422


@pytest.mark.parametrize("expected,mastery,hints,attempts,misconception,support", [
    ("advanced_challenge", .95, .1, 1., "none", "low"),
    ("conceptual_explanation", .25, .1, 1., "concept_confusion", "medium"),
    ("progressive_hints", .95, .8, 3., "inverse_operation", "medium"),
    ("step_by_step", .25, .8, 3., "inverse_operation", "high"),
    ("worked_example_based", .55, .8, 3., "arithmetic_error", "medium"),
])
def test_all_five_strategies_are_predicted_and_saved_from_table_data(
    expected, mastery, hints, attempts, misconception, support,
):
    payload = make_request_payload()
    payload["quiz"].update(
        quiz_mastery_score=mastery, quiz_hint_rate=hints, misconception_code=misconception,
        quiz_difficulty_level="advanced" if mastery > .8 else "beginner" if mastery < .5 else "intermediate",
        recommended_support_level=support,
    )
    payload["game"].update(
        game_mastery_score=mastery, hint_dependency=hints, game_avg_attempts_per_task=attempts,
        game_difficulty_level="advanced" if mastery > .8 else "intermediate",
    )
    payload["learner"]["prior_mastery_score"] = mastery
    seed_results(payload)
    response = client.post("/api/v1/tutor/strategy/from-results", json=result_reference(payload))
    assert response.status_code == 200
    assert response.json()["primary_strategy"] == expected
    with TestingSessionLocal() as database:
        saved = database.scalar(select(TutorStrategyPrediction))
        assert saved.primary_strategy == expected
        assert saved.model_version == "strategy-ml-v1"
        assert saved.confidence == response.json()["confidence"]
