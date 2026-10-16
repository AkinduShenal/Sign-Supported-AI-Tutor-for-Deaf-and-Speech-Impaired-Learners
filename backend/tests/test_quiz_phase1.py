import uuid
import csv
import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.quiz.models import (
    MisconceptionMapping,
    QuizComparison,
    QuizQuestion,
    QuizQuestionOption,
    QuizResponse,
    QuizResult,
    QuizSession,
)


QUIZ_TABLES = [
    Base.metadata.tables[name]
    for name in (
        "misconception_mappings",
        "quiz_questions",
        "quiz_question_options",
        "quiz_sessions",
        "quiz_responses",
        "quiz_results",
        "quiz_comparisons",
    )
]


@pytest.fixture
def quiz_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=QUIZ_TABLES)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    previous_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        with factory() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), factory
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        Base.metadata.drop_all(engine, tables=QUIZ_TABLES)
        engine.dispose()


def seed_questions(factory):
    with factory() as database:
        mapping = MisconceptionMapping(
            concept_id="linear_equations",
            misconception_code="inverse_operation",
            name_en="Inverse operation error",
        )
        first = QuizQuestion(
            question_code="Q-PRE-1",
            concept_id="linear_equations",
            subconcept_code="one_step_addition",
            question_type="multiple_choice",
            question_text_en="Solve x + 5 = 12",
            question_text_si="සමීකරණය විසඳන්න",
            difficulty_level="easy",
            assessment_use="pre",
            is_active=True,
            teacher_validated=False,
            correct_answer_text="7",
        )
        second = QuizQuestion(
            question_code="Q-POST-1",
            concept_id="linear_equations",
            subconcept_code="one_step_addition",
            question_type="multiple_choice",
            question_text_en="Solve x + 4 = 11",
            question_text_si="සමීකරණය විසඳන්න",
            difficulty_level="medium",
            assessment_use="post",
            is_active=True,
        )
        database.add_all((mapping, first, second))
        database.flush()
        correct = QuizQuestionOption(
            question_id=first.id,
            option_code="A",
            option_text_en="7",
            option_text_si="7",
            is_correct=True,
        )
        wrong = QuizQuestionOption(
            question_id=first.id,
            option_code="B",
            option_text_en="17",
            option_text_si="17",
            is_correct=False,
            misconception_code="inverse_operation",
        )
        other_question_option = QuizQuestionOption(
            question_id=second.id,
            option_code="A",
            option_text_en="7",
            option_text_si="7",
            is_correct=True,
        )
        database.add_all((correct, wrong, other_question_option))
        database.commit()
        return first.id, second.id, correct.id, wrong.id, other_question_option.id


def create_session(client, *, phase="pre_tutor"):
    response = client.post(
        "/api/v1/quiz/sessions",
        json={
            "student_id": "TEST-STUDENT",
            "concept_id": "linear_equations",
            "assessment_phase": phase,
            "display_language": "bilingual",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def answer_payload(question_id, option_id, **changes):
    return {
        "question_id": str(question_id),
        "selected_option_id": str(option_id),
        "response_time_sec": 12.8,
        "confidence_level": "high",
        "question_order": 1,
        **changes,
    }


def test_all_live_quiz_table_models_are_registered():
    assert {table.name for table in QUIZ_TABLES} == {
        "misconception_mappings",
        "quiz_questions",
        "quiz_question_options",
        "quiz_sessions",
        "quiz_responses",
        "quiz_results",
        "quiz_comparisons",
    }
    assert {"learning_cycle_id", "assessment_phase", "diagnostic_evidence"} <= set(
        QuizResult.__table__.c.keys()
    )
    assert QuizComparison.__table__.c.pre_quiz_result_id is not None


def test_question_fetch_filters_phase_and_hides_answer_metadata(quiz_db):
    client, factory = quiz_db
    first_id, second_id, *_ = seed_questions(factory)
    pre = client.get(
        "/api/v1/quiz/questions",
        params={
            "concept_id": "linear_equations",
            "assessment_phase": "pre_tutor",
            "difficulty_level": "easy",
        },
    )
    assert pre.status_code == 200
    assert len(pre.json()) == 1
    assert pre.json()[0]["id"] == str(first_id)
    assert len(pre.json()[0]["options"]) == 2
    assert not (
        {"is_correct", "correct_option", "misconception_code", "correct_answer_text"} & set(pre.json()[0])
    )
    for option in pre.json()[0]["options"]:
        assert "is_correct" not in option
        assert "misconception_code" not in option
    post = client.get(
        "/api/v1/quiz/questions",
        params={
            "assessment_phase": "post_tutor",
        },
    )
    assert [question["id"] for question in post.json()] == [str(second_id)]


def test_create_and_read_session(quiz_db):
    client, factory = quiz_db
    session = create_session(client)
    assert session["status"] == "in_progress"
    assert session["completed_at"] is None
    uuid.UUID(session["learning_cycle_id"])
    detail = client.get(f"/api/v1/quiz/sessions/{session['quiz_session_id']}")
    assert detail.status_code == 200
    assert detail.json()["responses_saved"] == 0
    with factory() as database:
        stored = database.scalar(select(QuizSession))
        assert stored is not None
        assert stored.quiz_session_id == session["quiz_session_id"]
        assert stored.assessment_phase == "pre_tutor"


def test_correct_response_derives_result_and_stores_evidence(quiz_db):
    client, factory = quiz_db
    question_id, _, correct_id, _, _ = seed_questions(factory)
    session_id = create_session(client)["quiz_session_id"]
    payload = answer_payload(question_id, correct_id)
    saved = client.post(f"/api/v1/quiz/sessions/{session_id}/responses", json=payload)
    assert saved.status_code == 201, saved.text
    assert saved.json()["is_correct"] is True
    assert saved.json()["correct_option"] is None
    assert "misconception_code" not in saved.json()
    assert "feedback" not in saved.json()
    with factory() as database:
        stored = database.scalar(select(QuizResponse))
        assert stored is not None
        assert stored.selected_option_id == correct_id
        assert stored.is_correct is True
        assert stored.misconception_code is None
        assert stored.response_time_sec == 12.8
        assert stored.confidence_level == "high"
        assert stored.question_order == 1
        assert stored.answered_at is not None


def test_incorrect_response_uses_option_mapping_not_client_claim(quiz_db):
    client, factory = quiz_db
    question_id, _, correct_id, wrong_id, _ = seed_questions(factory)
    session_id = create_session(client)["quiz_session_id"]
    payload = answer_payload(question_id, wrong_id, confidence_level="medium")
    payload["is_correct"] = True
    payload["misconception_code"] = "none"
    rejected = client.post(
        f"/api/v1/quiz/sessions/{session_id}/responses", json=payload
    )
    assert rejected.status_code == 422
    payload.pop("is_correct")
    payload.pop("misconception_code")
    saved = client.post(f"/api/v1/quiz/sessions/{session_id}/responses", json=payload)
    assert saved.status_code == 201
    assert saved.json()["is_correct"] is False
    assert saved.json()["correct_option"]["id"] == str(correct_id)
    assert saved.json()["correct_option"]["option_text_en"] == "7"
    replayed = client.post(f"/api/v1/quiz/sessions/{session_id}/responses", json=payload)
    assert replayed.status_code == 201
    assert replayed.json()["response_id"] == saved.json()["response_id"]
    assert replayed.json()["correct_option"] == saved.json()["correct_option"]
    with factory() as database:
        stored = database.scalar(select(QuizResponse))
        assert stored is not None
        assert stored.is_correct is False
        assert stored.misconception_code == "inverse_operation"
        assert stored.confidence_level == "medium"


def test_wrong_question_option_and_conflicting_duplicate_are_rejected(quiz_db):
    client, factory = quiz_db
    question_id, _, correct_id, _, other_option_id = seed_questions(factory)
    session_id = create_session(client)["quiz_session_id"]
    url = f"/api/v1/quiz/sessions/{session_id}/responses"
    assert (
        client.post(url, json=answer_payload(question_id, other_option_id)).status_code
        == 422
    )
    assert (
        client.post(url, json=answer_payload(question_id, correct_id)).status_code
        == 201
    )
    replayed = client.post(url, json=answer_payload(question_id, correct_id))
    assert replayed.status_code == 201
    assert replayed.json()["response_id"]
    assert replayed.json()["is_correct"] is True
    assert client.post(url, json=answer_payload(question_id, correct_id, response_time_sec=99)).status_code == 409
    with factory() as database:
        assert len(list(database.scalars(select(QuizResponse)))) == 1


def test_incomplete_session_cannot_be_completed(quiz_db):
    client, factory = quiz_db
    question_id, _, correct_id, _, _ = seed_questions(factory)
    session_id = create_session(client)["quiz_session_id"]
    completed = client.post(f"/api/v1/quiz/sessions/{session_id}/complete")
    assert completed.status_code == 409
    assert client.post(f"/api/v1/quiz/sessions/{session_id}/responses", json=answer_payload(question_id, correct_id)).status_code == 201
    with factory() as database:
        stored = database.scalar(select(QuizSession))
        assert stored is not None
        assert stored.status == "in_progress"
        assert stored.completed_at is None
        assert len(list(database.scalars(select(QuizResponse)))) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"response_time_sec": -0.1},
        {"confidence_level": "certain"},
        {"question_order": 0},
    ],
)
def test_invalid_answer_fields_are_rejected(quiz_db, change):
    client, factory = quiz_db
    question_id, _, correct_id, _, _ = seed_questions(factory)
    session_id = create_session(client)["quiz_session_id"]
    response = client.post(
        f"/api/v1/quiz/sessions/{session_id}/responses",
        json=answer_payload(question_id, correct_id, **change),
    )
    assert response.status_code == 422


def test_invalid_phase_or_language_is_rejected(quiz_db):
    client, _ = quiz_db
    for change in ({"assessment_phase": "during_tutor"}, {"display_language": "fr"}):
        response = client.post(
            "/api/v1/quiz/sessions",
            json={
                "student_id": "TEST-STUDENT",
                **change,
            },
        )
        assert response.status_code == 422


def test_client_session_id_and_answer_replay_preserve_original_evidence(quiz_db):
    client, factory = quiz_db
    question_id, _, correct_id, wrong_id, _ = seed_questions(factory)
    client_id = str(uuid.uuid4())
    cycle_id = str(uuid.uuid4())
    request = {
        "student_id": "STU_001", "concept_id": "linear_equations",
        "assessment_phase": "pre_tutor", "display_language": "bilingual",
        "client_session_id": client_id, "learning_cycle_id": cycle_id,
    }
    first = client.post("/api/v1/quiz/sessions", json=request)
    replay = client.post("/api/v1/quiz/sessions", json=request)
    assert first.status_code == replay.status_code == 201
    assert first.json()["quiz_session_id"] == replay.json()["quiz_session_id"] == f"QUIZ-{client_id}"
    assert first.json()["student_id"] == "STU_001"
    assert client.post("/api/v1/quiz/sessions", json={**request, "student_id": "STU_002"}).status_code == 409
    assert client.post("/api/v1/quiz/sessions", json={**request, "client_session_id": str(uuid.uuid4()), "student_id": "TEST-STUDENT"}).status_code == 422

    action_at = datetime.now(UTC).isoformat()
    answer = answer_payload(question_id, correct_id, client_action_at=action_at)
    url = f"/api/v1/quiz/sessions/QUIZ-{client_id}/responses"
    saved = client.post(url, json=answer)
    again = client.post(url, json=answer)
    assert saved.status_code == again.status_code == 201
    assert saved.json()["response_id"] == again.json()["response_id"]
    assert saved.json()["selected_option_id"] == str(correct_id)
    assert saved.json()["response_time_sec"] == 12.8
    assert saved.json()["confidence_level"] == "high"
    assert datetime.fromisoformat(saved.json()["answered_at"]) == datetime.fromisoformat(action_at)
    assert client.post(url, json={**answer, "selected_option_id": str(wrong_id)}).status_code == 409
    assert client.post(url, json={**answer, "client_action_at": datetime.now(UTC).isoformat()}).status_code == 409
    with factory() as database:
        assert len(database.scalars(select(QuizSession)).all()) == 1
        assert len(database.scalars(select(QuizResponse)).all()) == 1


def test_incomplete_quiz_export_preserves_question_source_ids(quiz_db, tmp_path, monkeypatch):
    from io import BytesIO
    from zipfile import ZipFile

    from scripts.export_quiz_collection import export_quiz_data

    client, factory = quiz_db
    question_id, _, _, wrong_id, _ = seed_questions(factory)
    session = client.post("/api/v1/quiz/sessions", json={"student_id": "STU_001"}).json()
    action_at = datetime.now(UTC).isoformat()
    assert client.post(f"/api/v1/quiz/sessions/{session['quiz_session_id']}/responses", json=answer_payload(
        question_id, wrong_id, confidence_level="low", client_action_at=action_at
    )).status_code == 201
    with factory() as database:
        source = database.scalar(select(QuizResponse))
        counts = export_quiz_data(database, tmp_path)
    assert counts["total_sessions"] == counts["incomplete_sessions"] == 1
    assert counts["total_responses"] == 1
    with (tmp_path / "quiz_responses.csv").open(encoding="utf-8-sig", newline="") as handle:
        row = list(csv.DictReader(handle))[0]
    assert row["source_response_id"] == str(source.id)
    assert row["student_code"] == "STU_001"
    assert row["question_id"] == str(question_id)
    assert row["selected_option_id"] == str(wrong_id)
    assert row["confidence_level"] == "low"
    assert row["misconception_code"] == "inverse_operation"
    assert row["assessment_complete"] == "False"
    assert datetime.fromisoformat(row["answered_at"]) == datetime.fromisoformat(action_at)
    assert json.loads((tmp_path / "manifest.json").read_text())["counts"] == counts

    monkeypatch.setenv("QUIZ_COLLECTION_EXPORT_KEY", "isolated-test-key-12345")
    route = "/api/v1/quiz/exports/collection"
    assert client.get(route).status_code == 401
    response = client.get(route, headers={"Authorization": "Bearer isolated-test-key-12345"})
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        assert {"quiz_sessions.csv", "quiz_responses.csv", "manifest.json"} == set(archive.namelist())


def test_export_keeps_two_learner_codes_and_responses_separate(quiz_db, tmp_path):
    from scripts.export_quiz_collection import export_quiz_data

    client, factory = quiz_db
    question_id, _, correct_id, wrong_id, _ = seed_questions(factory)
    expected = {}
    for code, option_id in (("STU_001", correct_id), ("STU_002", wrong_id)):
        created = client.post("/api/v1/quiz/sessions", json={
            "student_id": code, "client_session_id": str(uuid.uuid4()),
        })
        assert created.status_code == 201
        session_id = created.json()["quiz_session_id"]
        saved = client.post(f"/api/v1/quiz/sessions/{session_id}/responses", json=answer_payload(
            question_id, option_id, client_action_at=datetime.now(UTC).isoformat()
        ))
        assert saved.status_code == 201
        expected[session_id] = (code, str(option_id), saved.json()["response_id"])

    with factory() as database:
        counts = export_quiz_data(database, tmp_path)
    assert counts["total_sessions"] == counts["incomplete_sessions"] == 2
    assert counts["total_responses"] == 2
    with (tmp_path / "quiz_sessions.csv").open(encoding="utf-8-sig", newline="") as handle:
        session_rows = {row["quiz_session_id"]: row for row in csv.DictReader(handle)}
    with (tmp_path / "quiz_responses.csv").open(encoding="utf-8-sig", newline="") as handle:
        response_rows = {row["quiz_session_id"]: row for row in csv.DictReader(handle)}
    assert set(session_rows) == set(response_rows) == set(expected)
    for session_id, (code, option_id, response_id) in expected.items():
        assert session_rows[session_id]["student_code"] == code
        assert response_rows[session_id]["student_code"] == code
        assert response_rows[session_id]["selected_option_id"] == option_id
        assert response_rows[session_id]["source_response_id"] == response_id
