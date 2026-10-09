import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


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


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_database():
    # Save/restore app.dependency_overrides[get_db] rather than permanently
    # reassigning it at import time (as test_tutor_strategy.py does) — two
    # test files both doing a permanent reassignment would make whichever
    # one Python imports last silently win for the whole test session,
    # breaking the other file's tests with "no such table" errors.
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if previous is not None:
        app.dependency_overrides[get_db] = previous
    else:
        app.dependency_overrides.pop(get_db, None)


def _create_session(**overrides) -> dict:
    payload = {
        "student_id": "TEST001",
        "concept_id": "simple_equations",
        "learning_cycle_id": str(uuid.uuid4()),
        "assessment_phase": "pre_tutor",
        **overrides,
    }
    response = client.post("/api/v1/game/sessions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_game_session():
    body = _create_session()
    assert body["student_id"] == "TEST001"
    assert body["concept_id"] == "simple_equations"
    assert body["assessment_phase"] == "pre_tutor"
    assert body["status"] == "in_progress"
    assert body["completed_at"] is None
    assert body["game_session_id"]


def test_create_game_session_invalid_assessment_phase_rejected():
    response = client.post(
        "/api/v1/game/sessions",
        json={
            "student_id": "TEST001",
            "concept_id": "simple_equations",
            "learning_cycle_id": str(uuid.uuid4()),
            "assessment_phase": "during_tutor",
        },
    )
    assert response.status_code == 422


def test_record_game_event():
    session = _create_session()
    response = client.post(
        "/api/v1/game/events",
        json={
            "game_session_id": session["game_session_id"],
            "task_id": "TASK_E_001",
            "event_type": "QUESTION_SHOWN",
            "event_timestamp": datetime.now(UTC).isoformat(),
            "event_payload": {"difficulty_level": "easy", "variant_id": "LEQ_E_001"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["event_type"] == "QUESTION_SHOWN"
    assert body["event_payload"]["variant_id"] == "LEQ_E_001"


def test_record_game_event_invalid_event_type_rejected():
    session = _create_session()
    response = client.post(
        "/api/v1/game/events",
        json={
            "game_session_id": session["game_session_id"],
            "task_id": "TASK_E_001",
            "event_type": "NOT_A_REAL_EVENT",
            "event_timestamp": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 422


def test_record_game_event_unknown_session_returns_404():
    response = client.post(
        "/api/v1/game/events",
        json={
            "game_session_id": "does-not-exist",
            "event_type": "GAME_STARTED",
            "event_timestamp": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 404


def test_save_task_attempt():
    session = _create_session()
    response = client.post(
        "/api/v1/game/task-attempts",
        json={
            "game_session_id": session["game_session_id"],
            "task_id": "ASSESS_E_01",
            "attempt_number": 1,
            "attempts_count": 3,
            "wrong_attempts": 2,
            "hints_used": 1,
            "time_taken_sec": 38,
            "is_completed": True,
            "is_successful": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["wrong_attempts"] == 2
    assert body["is_successful"] is True


def test_save_task_attempt_with_variant_metadata_round_trips():
    session = _create_session()
    response = client.post(
        "/api/v1/game/task-attempts",
        json={
            "game_session_id": session["game_session_id"],
            "task_id": "ASSESS_E_01",
            "activity_id": "LEQ_ONE_STEP_ADD",
            "variant_id": "LEQ_E_004",
            "difficulty_level": "easy",
            "attempts_count": 3,
            "is_completed": True,
            "is_successful": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["activity_id"] == "LEQ_ONE_STEP_ADD"
    assert body["variant_id"] == "LEQ_E_004"
    assert body["difficulty_level"] == "easy"


def test_save_task_attempt_invalid_difficulty_level_rejected():
    session = _create_session()
    response = client.post(
        "/api/v1/game/task-attempts",
        json={
            "game_session_id": session["game_session_id"],
            "task_id": "ASSESS_E_01",
            "difficulty_level": "impossible",
        },
    )
    assert response.status_code == 422


def test_save_task_attempt_score_out_of_range_rejected():
    session = _create_session()
    response = client.post(
        "/api/v1/game/task-attempts",
        json={
            "game_session_id": session["game_session_id"],
            "task_id": "ASSESS_E_01",
            "score": 1.5,
        },
    )
    assert response.status_code == 422


def test_complete_game_session():
    session = _create_session()
    response = client.post(
        f"/api/v1/game/sessions/{session['game_session_id']}/complete"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


def test_complete_unknown_session_returns_404():
    response = client.post("/api/v1/game/sessions/does-not-exist/complete")
    assert response.status_code == 404


def test_get_game_result_before_creation_returns_404():
    session = _create_session()
    response = client.get(f"/api/v1/game/results/{session['game_session_id']}")
    assert response.status_code == 404


def test_variant_usage_counts_are_zero_for_a_fresh_student():
    response = client.get(
        "/api/v1/game/variant-usage",
        params={"student_id": "NEVER_PLAYED", "concept_id": "linear_equations"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["usage_counts"] == {}


def test_variant_usage_counts_increment_across_sessions():
    student_id = "USAGE_TEST_001"
    concept_id = "linear_equations"

    for _ in range(2):
        session = _create_session(student_id=student_id, concept_id=concept_id)
        attempt_response = client.post(
            "/api/v1/game/task-attempts",
            json={
                "game_session_id": session["game_session_id"],
                "task_id": "ASSESS_E_01",
                "activity_id": "LEQ_ONE_STEP_ADD",
                "variant_id": "LEQ_E_004",
                "difficulty_level": "easy",
                "is_completed": True,
                "is_successful": True,
            },
        )
        assert attempt_response.status_code == 201

    response = client.get(
        "/api/v1/game/variant-usage",
        params={"student_id": student_id, "concept_id": concept_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["usage_counts"] == {"LEQ_E_004": 2}

    # A different student's usage must never be mixed into this count.
    other_response = client.get(
        "/api/v1/game/variant-usage",
        params={"student_id": "SOMEONE_ELSE", "concept_id": concept_id},
    )
    assert other_response.json()["usage_counts"] == {}


def test_full_session_event_attempt_flow():
    """Mirrors Milestone 3 Step 7's end-to-end backend verification."""
    session = _create_session()
    session_id = session["game_session_id"]

    for event_type, task_id in [
        ("GAME_STARTED", None),
        ("QUESTION_SHOWN", "ASSESS_E_01"),
        ("ANSWER_INCORRECT", "ASSESS_E_01"),
        ("HINT_REQUESTED", "ASSESS_E_01"),
        ("RETRY_STARTED", "ASSESS_E_01"),
        ("ANSWER_CORRECT", "ASSESS_E_01"),
        ("TASK_COMPLETED", "ASSESS_E_01"),
    ]:
        response = client.post(
            "/api/v1/game/events",
            json={
                "game_session_id": session_id,
                "task_id": task_id,
                "event_type": event_type,
                "event_timestamp": datetime.now(UTC).isoformat(),
            },
        )
        assert response.status_code == 201, response.text

    attempt_response = client.post(
        "/api/v1/game/task-attempts",
        json={
            "game_session_id": session_id,
            "task_id": "ASSESS_E_01",
            "attempts_count": 2,
            "wrong_attempts": 1,
            "hints_used": 1,
            "time_taken_sec": 34,
            "is_completed": True,
            "is_successful": True,
        },
    )
    assert attempt_response.status_code == 201, attempt_response.text

    complete_response = client.post(f"/api/v1/game/sessions/{session_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
