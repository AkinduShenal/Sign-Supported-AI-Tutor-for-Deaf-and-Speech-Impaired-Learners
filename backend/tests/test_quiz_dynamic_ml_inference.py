"""Isolated SQLite API checks for synthetic-trained Dynamic Quiz inference."""

import hashlib
import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.quiz import dynamic_ml_inference as inference
from app.modules.quiz.models import (
    MisconceptionMapping, QuizQuestion, QuizQuestionOption, QuizResponse,
    QuizResult, QuizSession, QuizSessionQuestion,
)
from scripts.seed_quiz_dynamic import load_bank, seed_bank
from scripts.seed_quiz_phase2 import load_bank as load_fixed, seed_bank as seed_fixed


TABLES = [model.__table__ for model in (
    MisconceptionMapping, QuizQuestion, QuizQuestionOption, QuizSession,
    QuizSessionQuestion, QuizResponse, QuizResult,
)]


def _complete(client: TestClient, factory, student: str, correct: bool) -> str:
    created = client.post("/api/v1/quiz/sessions", json={
        "student_id": student,
        "client_session_id": str(uuid.uuid4()),
        "bank_mode": "dynamic_dev",
        "assessment_phase": "pre_tutor",
    })
    assert created.status_code == 201, created.text
    session_id = created.json()["quiz_session_id"]
    questions = client.get(f"/api/v1/quiz/sessions/{session_id}/questions").json()
    assert len(questions) == 10
    for order, question in enumerate(questions, 1):
        with factory() as db:
            choices = list(db.scalars(select(QuizQuestionOption).where(
                QuizQuestionOption.question_id == uuid.UUID(question["id"]))))
        option = next(item for item in choices if item.is_correct is correct)
        saved = client.post(f"/api/v1/quiz/sessions/{session_id}/responses", json={
            "question_id": question["id"],
            "selected_option_id": str(option.id),
            "question_order": order,
            "response_time_sec": 12.0 + order if correct else 5.0 + order,
            "confidence_level": "high" if correct else "low",
        })
        assert saved.status_code == 201, saved.text
    completed = client.post(f"/api/v1/quiz/sessions/{session_id}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    analyzed = client.post(f"/api/v1/quiz/sessions/{session_id}/analyze")
    assert analyzed.status_code == 200, analyzed.text
    assert analyzed.json()["correct_answers"] == (10 if correct else 0)
    return session_id


def test_new_sessions_predict_reproducibly_and_fail_closed(tmp_path, monkeypatch):
    db_path = tmp_path / "isolated_quiz_demo.sqlite"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(engine, tables=TABLES)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db, db.begin():
        seed_fixed(db, load_fixed())
        seed_bank(db, load_bank())
    monkeypatch.setattr(settings, "quiz_dynamic_dev_enabled", True)
    monkeypatch.setattr(settings, "quiz_dynamic_ml_demo_enabled", True)
    monkeypatch.setattr(inference, "DEMO_DATABASE_PATH", db_path)

    def override():
        with factory() as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        first = _complete(client, factory, "STU_036", correct=True)
        second = _complete(client, factory, "STU_037", correct=False)
        route = lambda sid: f"/api/v1/quiz/sessions/{sid}/experimental-prediction"
        a = client.get(route(first))
        b = client.get(route(first))
        c = client.get(route(second))
        assert a.status_code == b.status_code == c.status_code == 200
        assert a.json() == b.json()
        assert a.json()["status"] == c.json()["status"] == "available"
        assert a.json()["training_data_origin"] == "SYNTHETIC_ENGINEERING_DEMO_ONLY"
        assert a.json()["research_validated"] is False
        assert [item["label"] for item in a.json()["predictions"]] == ["M1", "M2", "M3", "M4"]
        assert all(0 <= item["probability"] <= 1 and
                   item["flagged"] == (item["probability"] >= 0.5)
                   for item in a.json()["predictions"])
        assert any(abs(x["probability"] - y["probability"]) > 0.01
                   for x, y in zip(a.json()["predictions"], c.json()["predictions"]))

        monkeypatch.setattr(settings, "quiz_dynamic_ml_demo_enabled", False)
        assert client.get(route(first)).status_code == 404
        monkeypatch.setattr(settings, "quiz_dynamic_ml_demo_enabled", True)
        monkeypatch.setattr(inference, "DEMO_DATABASE_PATH", tmp_path / "different.sqlite")
        assert client.get(route(first)).status_code == 404
        monkeypatch.setattr(inference, "DEMO_DATABASE_PATH", db_path)

        monkeypatch.setattr(inference, "ARTIFACT_DIR", tmp_path / "missing-artifact")
        missing = client.get(route(first))
        assert missing.status_code == 200
        assert missing.json()["status"] == "unavailable"
        assert missing.json()["reason"] == "artifact_missing"
        assert missing.json()["predictions"] == []

        corrupt_dir = tmp_path / "corrupt-artifact"
        corrupt_dir.mkdir()
        (corrupt_dir / inference.MODEL_NAME).write_bytes(
            (Path(__file__).parents[2] / "local_ml_artifacts" /
             "quiz_dynamic_62_demo" / inference.MODEL_NAME).read_bytes()
        )
        manifest_source = (Path(__file__).parents[2] / "local_ml_artifacts" /
                           "quiz_dynamic_62_demo" / inference.MANIFEST_NAME)
        manifest = json.loads(manifest_source.read_text(encoding="utf-8"))
        manifest["model_sha256"] = "0" * 64
        (corrupt_dir / inference.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        monkeypatch.setattr(inference, "ARTIFACT_DIR", corrupt_dir)
        incompatible = client.get(route(first))
        assert incompatible.status_code == 200
        assert incompatible.json()["status"] == "unavailable"
        assert incompatible.json()["reason"] == "artifact_incompatible"

        manifest["model_sha256"] = hashlib.sha256(
            (corrupt_dir / inference.MODEL_NAME).read_bytes()).hexdigest()
        manifest["feature_names"][0], manifest["feature_names"][1] = (
            manifest["feature_names"][1], manifest["feature_names"][0])
        (corrupt_dir / inference.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        assert client.get(route(first)).json()["reason"] == "artifact_incompatible"
        manifest["feature_names"][0], manifest["feature_names"][1] = (
            manifest["feature_names"][1], manifest["feature_names"][0])
        manifest["target_columns"] = list(reversed(manifest["target_columns"]))
        (corrupt_dir / inference.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        assert client.get(route(first)).json()["reason"] == "artifact_incompatible"
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()
