"""Local SQLite coverage for the teacher-approved dynamic Quiz release. No configured DB is used."""

import uuid
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.quiz.models import MisconceptionMapping, QuizQuestion, QuizSession
from scripts import release_quiz_dynamic_v1 as release
from scripts.seed_quiz_dynamic import MAPPING_NAMES, load_bank, seed_bank
from scripts.seed_quiz_phase2 import load_bank as load_fixed, seed_bank as seed_fixed
from test_quiz_dynamic import TABLES


def _database(with_mappings=True):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=TABLES)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database, database.begin():
        seed_fixed(database, load_fixed())
        present = set(database.scalars(select(MisconceptionMapping.misconception_code)))
        database.add_all(MisconceptionMapping(concept_id="linear_equations", misconception_code=code,
                                              name_en=name, teacher_validated=False)
                         for code, name in MAPPING_NAMES.items() if code not in present)
        if not with_mappings:
            database.delete(database.scalar(select(MisconceptionMapping)
                                            .where(MisconceptionMapping.misconception_code == "concept_confusion")))
    return engine, factory


def test_released_bank_is_the_approved_draft_content():
    released = release.load_released_bank()
    draft = load_bank()
    assert len(released) == 60
    assert {q["bank_version"] for q in released} == {release.RELEASE_VERSION}
    strip = lambda q: {k: v for k, v in q.items() if k != "bank_version"}
    assert [strip(q) for q in released] == [strip(q) for q in draft]


def test_release_refuses_a_changed_bank(monkeypatch):
    monkeypatch.setattr(release, "APPROVED_BANK_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="re-approval"):
        release.load_released_bank()


def test_dry_run_writes_nothing_and_apply_is_repeat_safe():
    engine, factory = _database()
    bank = release.load_released_bank()
    with factory() as database:
        assert release.release_bank(database, bank, apply=False) == (60, 0)
        database.rollback()
    with factory() as database:
        assert database.scalar(select(QuizQuestion).where(QuizQuestion.bank_version == release.RELEASE_VERSION)) is None
    with factory() as database, database.begin():
        assert release.release_bank(database, bank, apply=True) == (60, 0)
    with factory() as database, database.begin():
        assert release.release_bank(database, bank, apply=True) == (0, 60)
    with factory() as database:
        rows = database.scalars(select(QuizQuestion).where(QuizQuestion.bank_version == release.RELEASE_VERSION)).all()
        assert len(rows) == 60 and all(row.teacher_validated for row in rows)
    engine.dispose()


def test_release_refuses_missing_mappings_and_draft_rows():
    engine, factory = _database(with_mappings=False)
    with factory() as database, pytest.raises(ValueError, match="mappings missing"):
        release.release_bank(database, release.load_released_bank(), apply=False)
    engine.dispose()
    engine, factory = _database()
    with factory() as database, database.begin():
        seed_bank(database, load_bank())
    with factory() as database, pytest.raises(ValueError, match="no overwrite"):
        release.release_bank(database, release.load_released_bank(), apply=False)
    engine.dispose()


def test_released_sessions_get_a_prediction_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "quiz_dynamic_dev_enabled", False)
    monkeypatch.setattr(settings, "quiz_dynamic_ml_demo_enabled", False)
    engine, factory = _database()
    with factory() as database, database.begin():
        release.release_bank(database, release.load_released_bank(), apply=True)

    def override():
        with factory() as database:
            yield database

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        created = client.post("/api/v1/quiz/sessions", json={
            "student_id": "STU_002", "client_session_id": str(uuid.uuid4()),
            "bank_mode": "dynamic", "assessment_phase": "pre_tutor"})
        sid = created.json()["quiz_session_id"]
        for order, question in enumerate(client.get(f"/api/v1/quiz/sessions/{sid}/questions").json(), 1):
            assert client.post(f"/api/v1/quiz/sessions/{sid}/responses", json={
                "question_id": question["id"], "selected_option_id": question["options"][0]["id"],
                "question_order": order, "response_time_sec": 4.0 + order, "confidence_level": "medium",
            }).status_code == 201
        assert client.post(f"/api/v1/quiz/sessions/{sid}/complete").status_code == 200
        route = f"/api/v1/quiz/sessions/{sid}/experimental-prediction"

        monkeypatch.setenv("QUIZ_ML_ENABLED", "false")
        assert client.get(route).status_code == 404
        monkeypatch.setenv("QUIZ_ML_ENABLED", "true")
        predicted = client.get(route)
        assert predicted.status_code == 200, predicted.text
        body = predicted.json()
        assert body["status"] == "available" and body["bank_version"] == release.RELEASE_VERSION
        assert [item["label"] for item in body["predictions"]] == ["M1", "M2", "M3", "M4"]
        assert body["taxonomy_teacher_verified_on"] == "2026-10-15"
        assert all(0 <= item["probability"] <= 1 for item in body["predictions"])
        assert client.get(route).json() == body
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        engine.dispose()


def test_released_sessions_work_without_the_development_flag(monkeypatch):
    monkeypatch.setattr(settings, "quiz_dynamic_dev_enabled", False)
    engine, factory = _database()
    with factory() as database, database.begin():
        release.release_bank(database, release.load_released_bank(), apply=True)

    def override():
        with factory() as database:
            yield database

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        request = {"student_id": "STU_001", "client_session_id": str(uuid.uuid4()),
                   "bank_mode": "dynamic", "assessment_phase": "pre_tutor"}
        created = client.post("/api/v1/quiz/sessions", json=request)
        assert created.status_code == 201, created.text
        assert client.post("/api/v1/quiz/sessions", json=request).json() == created.json()
        assert client.post("/api/v1/quiz/sessions", json={**request, "bank_mode": "fixed"}).status_code == 409
        sid = created.json()["quiz_session_id"]
        questions = client.get(f"/api/v1/quiz/sessions/{sid}/questions").json()
        assert len(questions) == 10
        assert Counter(q["difficulty_level"] for q in questions) == {"easy": 4, "medium": 4, "hard": 2}
        assert len({q["question_code"].split("-V")[0] for q in questions}) == 10
        with factory() as database:
            session = database.scalar(select(QuizSession).where(QuizSession.quiz_session_id == sid))
            assert session.bank_version == release.RELEASE_VERSION
        # The draft development mode keeps its own guard.
        draft = client.post("/api/v1/quiz/sessions", json={**request, "client_session_id": str(uuid.uuid4()),
                                                            "bank_mode": "dynamic_dev"})
        assert draft.status_code == 409
        for order, question in enumerate(questions, 1):
            answered = client.post(f"/api/v1/quiz/sessions/{sid}/responses", json={
                "question_id": question["id"], "selected_option_id": question["options"][0]["id"],
                "question_order": order, "response_time_sec": 2.0, "confidence_level": "medium",
            })
            assert answered.status_code == 201, answered.text
        assert client.post(f"/api/v1/quiz/sessions/{sid}/complete").status_code == 200
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        engine.dispose()
