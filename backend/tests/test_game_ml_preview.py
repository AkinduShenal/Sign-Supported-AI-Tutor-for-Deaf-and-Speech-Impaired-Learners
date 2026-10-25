"""Synthetic, in-memory evidence only; preview GETs must not alter any rows."""

import copy
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.modules.game.ml.research_schema import ResearchObservation
from app.modules.game.ml_preview import first_attempt_accuracy, read_ml_input_preview
from app.modules.game.models import GameResult, GameSession, GameTaskAttempt, GameplayEvent
from app.modules.game.router import router


@pytest.fixture(params=["drag_drop", "hangman"])
def evidence(request):
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    tables = [model.__table__ for model in (GameSession, GameTaskAttempt, GameplayEvent, GameResult)]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as db:
        mode = request.param
        start = datetime(2026, 10, 20, 8, tzinfo=UTC)
        session = GameSession(game_session_id=str(uuid.uuid4()), student_id="STU_999",
                              concept_id="linear_equations", learning_cycle_id=uuid.uuid4(),
                              assessment_phase="pre_tutor", status="completed", started_at=start)
        db.add(session)
        db.flush()
        events = []

        def emit(kind, task=None, **payload):
            event = GameplayEvent(game_session_id=session.game_session_id, task_id=task,
                                  event_type=kind, event_timestamp=start + timedelta(seconds=len(events)),
                                  event_payload={"game_type": mode, "client_event_id": str(uuid.uuid4()), **payload})
            db.add(event)
            events.append(event)

        emit("GAME_STARTED", recording_protocol="game-evidence-v1")
        attempts, planned = [], 0
        for task_index, difficulty in enumerate(["easy", "easy", "medium", "medium", "hard", "hard"]):
            task = f"SYNTHETIC_{task_index}"
            steps = 1 if mode == "hangman" or difficulty == "easy" else 2
            planned += steps
            for step in range(steps):
                context = {"difficulty_level": difficulty}
                if mode == "drag_drop":
                    context.update(step_index=step, step_count=steps)
                emit("QUESTION_SHOWN", task, **context)
                hinted = task_index == 1 and step == 0
                if hinted:
                    emit("HINT_REQUESTED", task, **context)
                wrong_first = task_index == 0 and step == 0
                for number in range(1, 3 if wrong_first else 2):
                    if number > 1:
                        emit("RETRY_STARTED", task, **context)
                    correct = not wrong_first or number == 2
                    response = "4" if correct else "3"
                    answer = {**context, "attempt_number": number, "question_prompt": "x + 3 = 7",
                              "expected_response": "4", "hints_before_attempt": int(hinted),
                              "answer_type": "final_value" if mode == "hangman" else "equation_operation",
                              "submitted_value" if mode == "hangman" else "selected_choice": response}
                    emit("ANSWER_SUBMITTED", task, **answer)
                    emit("ANSWER_CORRECT" if correct else "ANSWER_INCORRECT", task, **answer)
                emit("TASK_COMPLETED", task, **context)
            attempt = GameTaskAttempt(game_session_id=session.game_session_id, task_id=task,
                                      activity_id=task, variant_id=task, difficulty_level=difficulty,
                                      attempt_number=1, attempts_count=steps + int(task_index == 0),
                                      wrong_attempts=int(task_index == 0), hints_used=int(task_index == 1),
                                      skipped_steps=2 if task_index == 0 else 0, time_taken_sec=12.375,
                                      is_completed=True, is_successful=True)
            db.add(attempt)
            attempts.append(attempt)
        emit("GAME_COMPLETED")
        session.completed_at = start + timedelta(seconds=len(events))
        result = GameResult(game_session_id=session.game_session_id, student_id=session.student_id,
                            concept_id=session.concept_id, learning_cycle_id=session.learning_cycle_id,
                            assessment_phase=session.assessment_phase, completed_at=session.completed_at,
                            engagement_level="high", behavioral_difficulty="low", hint_dependency=1 / 6,
                            game_mastery_score=1, tasks_total=6, tasks_attempted=6, tasks_completed=6,
                            successful_tasks=6, game_success_rate=1, game_completion_rate=1,
                            game_avg_attempts_per_task=(planned + 1) / 6, game_hint_rate=1 / 6,
                            game_difficulty_level="advanced", game_active_time_sec=74,
                            wrong_attempt_count=1, retry_count=1, total_hint_count=1,
                            skipped_step_count=2, model_version="game-heuristic-v1")
        db.add(result)
        db.commit()
        yield db, session, result, events, attempts, planned
    engine.dispose()


def test_preview_matches_saved_values_and_research_first_attempt_definition(evidence):
    db, session, result, events, _, planned = evidence
    preview = read_ml_input_preview(session.game_session_id, db)
    observation = ResearchObservation(
        student_code=session.student_id, session_id=session.game_session_id, concept=session.concept_id,
        game_type=events[0].event_payload["game_type"], activity_ids=["SYNTHETIC"], assessment_phase="pre_tutor",
        observation_started_at=session.started_at, observation_ended_at=session.completed_at,
        total_steps=planned, first_attempt_correct_steps=planned - 1, first_attempt_observation_complete=True,
        wrong_attempts=1, retry_count=1, hint_count=1, steps_with_hints=1, hint_observation_complete=True,
        tasks_total=6, tasks_completed=6, task_completed=True, skipped_steps=2,
        task_duration_seconds=None, task_duration_reliable=False, difficulty_label=None,
    )
    values = preview.features.model_dump()
    assert values["first_attempt_accuracy"] == observation.first_attempt_accuracy == (planned - 1) / planned
    assert values["first_attempt_accuracy"] != values["game_success_rate"] == 1
    for name in values.keys() - {"first_attempt_accuracy"}:
        assert values[name] == getattr(result, name)
    assert values["game_hint_rate"] == 1 / 6  # not the displayed rounded percentage
    assert values["skipped_step_count"] == 2  # actual saved value, not a hardcoded zero
    assert values["game_active_time_sec"] == 74  # preserve saved rounding/elapsed semantics
    assert preview.all_features_available and not preview.ready_for_inference


def test_first_attempt_score_does_not_depend_on_database_row_order(evidence):
    _, session, _, events, attempts, planned = evidence
    assert first_attempt_accuracy(session, attempts, list(reversed(events))) == (planned - 1) / planned


@pytest.mark.parametrize("mutation", ["missing_first", "duplicate_first", "missing_shown", "contradictory_response", "unknown_protocol", "reversed_time", "invalid_client_id"])
def test_missing_or_ambiguous_evidence_is_null_without_substituting_success(evidence, mutation):
    db, session, _, events, _, _ = evidence
    first = next(event for event in events if event.event_type == "ANSWER_INCORRECT")
    if mutation == "missing_first":
        db.delete(first)
    elif mutation == "duplicate_first":
        second = next(event for event in events if event.event_type == "ANSWER_CORRECT")
        second.event_payload = {**second.event_payload, "attempt_number": 1}
    elif mutation == "missing_shown":
        db.delete(next(event for event in events if event.event_type == "QUESTION_SHOWN"))
    elif mutation == "contradictory_response":
        field = "submitted_value" if "submitted_value" in first.event_payload else "selected_choice"
        first.event_payload = {**first.event_payload, field: "4"}
    elif mutation == "unknown_protocol":
        events[0].event_payload = {**events[0].event_payload, "recording_protocol": "legacy"}
    elif mutation == "invalid_client_id":
        first.event_payload = {**first.event_payload, "client_event_id": 123}
    else:
        first.event_timestamp = session.completed_at + timedelta(seconds=10)
    db.commit()
    preview = read_ml_input_preview(session.game_session_id, db)
    assert preview.features.first_attempt_accuracy is None
    assert preview.features.game_success_rate == 1
    assert "first_attempt_accuracy" in preview.unavailable_reasons
    assert not preview.all_features_available and not preview.ready_for_inference


def test_wrong_owner_never_exposes_another_learners_result(evidence):
    db, session, result, *_ = evidence
    result.student_id = "STU_998"
    db.commit()
    preview = read_ml_input_preview(session.game_session_id, db)
    assert set(preview.features.model_dump().values()) == {None}


def test_missing_saved_metric_is_not_invented(evidence):
    db, session, result, *_ = evidence
    # Simulate a historical missing value without writing NULL to a NOT NULL column.
    with db.no_autoflush:
        result.skipped_step_count = None
        preview = read_ml_input_preview(session.game_session_id, db)
        assert preview.features.skipped_step_count is None
        assert not preview.all_features_available
    db.rollback()


def test_get_is_read_only_and_missing_result_is_404(evidence):
    db, session, *_ = evidence
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    models = (GameSession, GameTaskAttempt, GameplayEvent, GameResult)

    def snapshot():
        return copy.deepcopy([
            [tuple(getattr(row, column.name) for column in model.__table__.columns)
             for row in db.scalars(select(model).order_by(model.id))]
            for model in models
        ])

    db.expire_all()  # Compare database representations on both sides (SQLite strips tzinfo).
    before = snapshot()
    statements = []

    def record_sql(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(db.get_bind(), "before_cursor_execute", record_sql)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/game/results/{session.game_session_id}/ml-inputs")
        assert response.status_code == 200
        assert len(response.json()["features"]) == 9
        assert response.json()["ready_for_inference"] is False
        assert client.get("/api/v1/game/results/missing/ml-inputs").status_code == 404
    assert statements and all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    event.remove(db.get_bind(), "before_cursor_execute", record_sql)
    db.expire_all()
    assert snapshot() == before
