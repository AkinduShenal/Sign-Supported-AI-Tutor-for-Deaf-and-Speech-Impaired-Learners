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


# ---- Batch 4: feature engineering, automatic completion, game_results ----


def _save_attempt(session_id: str, task_id: str, difficulty: str, **overrides) -> dict:
    payload = {
        "game_session_id": session_id,
        "task_id": task_id,
        "variant_id": task_id,
        "activity_id": f"ACTIVITY_{task_id}",
        "difficulty_level": difficulty,
        "attempts_count": 1,
        "wrong_attempts": 0,
        "hints_used": 0,
        "time_taken_sec": 10,
        "is_completed": True,
        "is_successful": True,
        **overrides,
    }
    response = client.post("/api/v1/game/task-attempts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _complete_full_assessment(session_id: str, **first_task_overrides) -> dict:
    """Saves 2 easy + 2 medium + 2 hard task attempts (the Step 10
    blueprint), then completes the session. The first easy task accepts
    overrides so individual tests can control one task's numbers while
    the rest stay at tidy defaults."""
    _save_attempt(session_id, "E1", "easy", **first_task_overrides)
    _save_attempt(session_id, "E2", "easy")
    _save_attempt(session_id, "M1", "medium")
    _save_attempt(session_id, "M2", "medium")
    _save_attempt(session_id, "H1", "hard")
    _save_attempt(session_id, "H2", "hard")
    return client.post(f"/api/v1/game/sessions/{session_id}/complete").json()


def test_game_result_not_created_before_full_2_2_2_spread():
    session = _create_session()
    session_id = session["game_session_id"]
    # Only 1 easy + 1 medium + 1 hard — short of the 2+2+2 blueprint.
    _save_attempt(session_id, "E1", "easy")
    _save_attempt(session_id, "M1", "medium")
    _save_attempt(session_id, "H1", "hard")
    client.post(f"/api/v1/game/sessions/{session_id}/complete")

    result_response = client.get(f"/api/v1/game/results/{session_id}")
    assert result_response.status_code == 404


def test_game_result_created_automatically_once_2_2_2_reached():
    session = _create_session()
    session_id = session["game_session_id"]
    _complete_full_assessment(session_id)

    result_response = client.get(f"/api/v1/game/results/{session_id}")
    assert result_response.status_code == 200, result_response.text
    body = result_response.json()
    assert body["tasks_total"] == 6
    assert body["tasks_attempted"] == 6
    assert body["tasks_completed"] == 6
    assert body["successful_tasks"] == 6
    assert body["game_success_rate"] == 1.0
    assert body["game_completion_rate"] == 1.0


def test_game_result_rate_calculations_are_correct():
    session = _create_session()
    session_id = session["game_session_id"]
    # One task wrong/unsuccessful, with 1 hint and 1 retry recorded via a
    # gameplay event — everything else tidy defaults (0 hints, 1 attempt).
    _save_attempt(
        session_id,
        "E1",
        "easy",
        attempts_count=3,
        wrong_attempts=2,
        hints_used=1,
        time_taken_sec=20,
        is_successful=False,
    )
    client.post(
        "/api/v1/game/events",
        json={
            "game_session_id": session_id,
            "task_id": "E1",
            "event_type": "RETRY_STARTED",
            "event_timestamp": datetime.now(UTC).isoformat(),
        },
    )
    _save_attempt(session_id, "E2", "easy")
    _save_attempt(session_id, "M1", "medium")
    _save_attempt(session_id, "M2", "medium")
    _save_attempt(session_id, "H1", "hard")
    _save_attempt(session_id, "H2", "hard")
    client.post(f"/api/v1/game/sessions/{session_id}/complete")

    body = client.get(f"/api/v1/game/results/{session_id}").json()
    assert body["tasks_attempted"] == 6
    assert body["successful_tasks"] == 5
    assert body["game_success_rate"] == pytest.approx(5 / 6)
    assert body["wrong_attempt_count"] == 2
    assert body["retry_count"] == 1
    assert body["total_hint_count"] == 1
    # 1 of 6 tasks had a hint -> game_hint_rate is a share of tasks, not
    # hints-per-task (that has no upper bound and the column is 0-1).
    assert body["game_hint_rate"] == pytest.approx(1 / 6)
    # (3 + 1 + 1 + 1 + 1 + 1) / 6 attempted tasks
    assert body["game_avg_attempts_per_task"] == pytest.approx(8 / 6)
    assert body["game_active_time_sec"] == 20 + 10 * 5


def test_game_hint_rate_stays_within_0_and_1_even_with_many_hints_per_task():
    """A learner who requests several hints on every task must not push
    game_hint_rate past 1 — the database column enforces 0-1 on every
    *_rate field, same as the others."""
    session = _create_session()
    session_id = session["game_session_id"]
    for task_id, difficulty in [
        ("E1", "easy"),
        ("E2", "easy"),
        ("M1", "medium"),
        ("M2", "medium"),
        ("H1", "hard"),
        ("H2", "hard"),
    ]:
        _save_attempt(session_id, task_id, difficulty, hints_used=4)
    client.post(f"/api/v1/game/sessions/{session_id}/complete")

    body = client.get(f"/api/v1/game/results/{session_id}").json()
    assert body["game_hint_rate"] == 1.0
    assert body["total_hint_count"] == 24


def test_game_result_creation_is_idempotent_on_repeated_completion():
    session = _create_session()
    session_id = session["game_session_id"]
    _complete_full_assessment(session_id)
    first = client.get(f"/api/v1/game/results/{session_id}").json()

    # Completing an already-completed session again must not create a
    # second row (game_results.game_session_id is unique) or change it.
    second_complete = client.post(f"/api/v1/game/sessions/{session_id}/complete")
    assert second_complete.status_code == 200
    second = client.get(f"/api/v1/game/results/{session_id}").json()
    assert second == first


def test_game_result_is_ai_tutor_ready_json():
    """Mirrors Milestone 3 Step 19's required field list."""
    session = _create_session(student_id="AI_TUTOR_READY_001", concept_id="linear_equations")
    session_id = session["game_session_id"]
    _complete_full_assessment(session_id)

    body = client.get(f"/api/v1/game/results/{session_id}").json()
    for field in [
        "student_id",
        "concept_id",
        "game_session_id",
        "game_success_rate",
        "game_completion_rate",
        "game_avg_attempts_per_task",
        "game_hint_rate",
        "game_difficulty_level",
        "game_active_time_sec",
        "assessment_phase",
        "learning_cycle_id",
        "wrong_attempt_count",
        "retry_count",
        "total_hint_count",
        "skipped_step_count",
    ]:
        assert field in body, f"missing AI-Tutor-ready field: {field}"
    assert body["student_id"] == "AI_TUTOR_READY_001"
    assert body["assessment_phase"] == "pre_tutor"
    # Prototype-only indicators must be clearly labelled, never presented
    # as a trained model's output (Milestone 3 Step 17 / CLAUDE.md).
    assert body["model_version"] == "game-heuristic-v1"


def test_game_result_handles_a_fully_unsuccessful_assessment_without_dividing_by_zero():
    session = _create_session()
    session_id = session["game_session_id"]
    for task_id, difficulty in [
        ("E1", "easy"),
        ("E2", "easy"),
        ("M1", "medium"),
        ("M2", "medium"),
        ("H1", "hard"),
        ("H2", "hard"),
    ]:
        _save_attempt(session_id, task_id, difficulty, is_successful=False)
    client.post(f"/api/v1/game/sessions/{session_id}/complete")

    body = client.get(f"/api/v1/game/results/{session_id}").json()
    assert body["game_success_rate"] == 0.0
    assert body["successful_tasks"] == 0


# ---- Batch 5: audit/reconstruction and integrity ----


def test_session_can_be_reconstructed_from_events_and_attempts():
    """Milestone 3 Step 21 audit: from stored rows alone, can we tell which
    question (variant + step) the learner got and what they submitted?"""
    from sqlalchemy import select

    from app.modules.game.models import GameplayEvent, GameTaskAttempt

    session_id = _create_session()["game_session_id"]
    ts = datetime.now(UTC).isoformat()
    step = {"variant_id": "LEQ_M_001", "difficulty_level": "medium", "step_index": 0}
    events = [
        ("QUESTION_SHOWN", {**step, "equation_shown": "2x + 1 = 7", "choices_offered": ["-1", "+1"]}),
        ("ANSWER_SUBMITTED", {**step, "selected_choice": "+1", "is_correct": False}),
        ("ANSWER_INCORRECT", {**step, "selected_choice": "+1", "is_correct": False}),
        ("HINT_REQUESTED", step),
        ("RETRY_STARTED", {}),
        ("ANSWER_SUBMITTED", {**step, "selected_choice": "-1", "is_correct": True}),
    ]
    for event_type, payload in events:
        response = client.post(
            "/api/v1/game/events",
            json={
                "game_session_id": session_id,
                "task_id": "LEQ_M_001",
                "event_type": event_type,
                "event_timestamp": ts,
                "event_payload": payload,
            },
        )
        assert response.status_code == 201, response.text
    _save_attempt(session_id, "LEQ_M_001", "medium", attempts_count=2, wrong_attempts=1, hints_used=1)

    database = TestingSessionLocal()
    try:
        rows = database.scalars(
            select(GameplayEvent).where(GameplayEvent.game_session_id == session_id)
        ).all()
        shown = [r for r in rows if r.event_type == "QUESTION_SHOWN"]
        submitted = [r for r in rows if r.event_type == "ANSWER_SUBMITTED"]
        assert shown[0].event_payload["variant_id"] == "LEQ_M_001"
        assert shown[0].event_payload["equation_shown"] == "2x + 1 = 7"
        assert [r.event_payload["selected_choice"] for r in submitted] == ["+1", "-1"]
        assert [r.event_payload["is_correct"] for r in submitted] == [False, True]
        attempts = database.scalars(
            select(GameTaskAttempt).where(GameTaskAttempt.game_session_id == session_id)
        ).all()
        assert len(attempts) == 1 and attempts[0].variant_id == "LEQ_M_001"
    finally:
        database.close()


def test_multi_step_task_saved_once_counts_as_one_task():
    session_id = _create_session()["game_session_id"]
    for task_id, difficulty in [
        ("E1", "easy"), ("E2", "easy"), ("M1", "medium"),
        ("M2", "medium"), ("H1", "hard"), ("H2", "hard"),
    ]:
        # a 3-step task summarised in one row: attempts_count spans all steps
        _save_attempt(session_id, task_id, difficulty, attempts_count=3)
    client.post(f"/api/v1/game/sessions/{session_id}/complete")
    result = client.get(f"/api/v1/game/results/{session_id}").json()
    assert result["tasks_completed"] == 6
    assert result["game_completion_rate"] == 1.0
    assert result["game_avg_attempts_per_task"] == 3.0


def test_event_and_attempt_for_unknown_session_rejected_by_foreign_key():
    ts = datetime.now(UTC).isoformat()
    event = client.post(
        "/api/v1/game/events",
        json={"game_session_id": "nope", "event_type": "GAME_STARTED", "event_timestamp": ts},
    )
    attempt = client.post(
        "/api/v1/game/task-attempts",
        json={"game_session_id": "nope", "task_id": "E1"},
    )
    assert event.status_code == 404
    assert attempt.status_code == 404
