"""Researcher downloads against synthetic in-memory Game data only."""

import csv
import json
import uuid
from datetime import UTC, datetime
from io import BytesIO, StringIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.game.collection_export import GameExportSettings, collection_zip
from app.modules.game.models import (
    GameResult,
    GameSession,
    GameTaskAttempt,
    GameplayEvent,
)

EXPORT_KEY = "synthetic-researcher-export-key-only"
HEADERS = {"Authorization": f"Bearer {EXPORT_KEY}"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def local_database(monkeypatch):
    monkeypatch.setenv("GAME_COLLECTION_EXPORT_KEY", EXPORT_KEY)
    monkeypatch.setitem(GameExportSettings.model_config, "env_file", None)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        GameSession.__table__,
        GameplayEvent.__table__,
        GameTaskAttempt.__table__,
        GameResult.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    factory = sessionmaker(bind=engine, autoflush=False)

    def override():
        with factory() as database:
            yield database

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    yield factory
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    engine.dispose()


@pytest.mark.parametrize("key,expected", [(None, 401), ("incorrect", 403)])
def test_unauthorized_download_never_opens_database(key, expected):
    def forbidden_connection():
        pytest.fail("authorization must run before database access")

    app.dependency_overrides[get_db] = forbidden_connection
    headers = {} if key is None else {"Authorization": f"Bearer {key}"}
    response = client.get("/api/v1/game/exports/collection", headers=headers)
    assert response.status_code == expected
    assert EXPORT_KEY not in response.text


@pytest.mark.parametrize("key", [None, "too-short"])
def test_download_is_disabled_until_researcher_key_is_configured(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("GAME_COLLECTION_EXPORT_KEY", raising=False)
    else:
        monkeypatch.setenv("GAME_COLLECTION_EXPORT_KEY", key)

    def forbidden_connection():
        pytest.fail("disabled export must not access the database")

    app.dependency_overrides[get_db] = forbidden_connection
    assert (
        client.get("/api/v1/game/exports/collection", headers=HEADERS).status_code
        == 503
    )


def test_csv_zip_matches_saved_source_and_does_not_change_records(local_database):
    created = client.post(
        "/api/v1/game/sessions",
        json={
            "student_id": "STU_TEST_EXPORT",
            "concept_id": "linear_equations",
            "learning_cycle_id": str(uuid.uuid4()),
            "assessment_phase": "pre_tutor",
        },
    )
    assert created.status_code == 201
    session_id = created.json()["game_session_id"]
    event = client.post(
        "/api/v1/game/events",
        json={
            "game_session_id": session_id,
            "task_id": "SYNTHETIC_E1",
            "event_type": "ANSWER_CORRECT",
            "event_timestamp": datetime.now(UTC).isoformat(),
            "event_payload": {
                "client_event_id": str(uuid.uuid4()),
                "question_prompt": "x + 3 = 7",
                "submitted_value": "4",
                "expected_response": "4",
                "answer_type": "final_value",
                "attempt_number": 1,
                "difficulty_level": "easy",
                "game_type": "hangman",
            },
        },
    )
    assert event.status_code == 201
    response = client.get("/api/v1/game/exports/collection", headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="game-collection-'
    )
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "game_sessions.csv",
            "student_answers.csv",
            "game_events.csv",
            "game_analytics.csv",
            "independent_assessment_labels.csv",
            "manifest.json",
        }
        answers = list(
            csv.DictReader(
                StringIO(archive.read("student_answers.csv").decode("utf-8-sig"))
            )
        )
        assert len(answers) == 1
        assert answers[0]["source_event_id"] == event.json()["id"]
        assert answers[0]["submitted_answer"] == "4"
        assert answers[0]["student_id_recorded"] == "STU_TEST_EXPORT"
        labels = list(
            csv.DictReader(
                StringIO(
                    archive.read("independent_assessment_labels.csv").decode(
                        "utf-8-sig"
                    )
                )
            )
        )
        assert labels[0]["independent_label"] == ""
        counts = json.loads(archive.read("manifest.json"))["counts"]
        assert counts["game_sessions"] == counts["student_answers"] == 1
        assert counts["incomplete_sessions"] == 1
    with local_database() as database:
        assert database.scalar(select(func.count(GameSession.id))) == 1
        assert database.scalar(select(GameSession.status)) == "in_progress"
        assert database.scalar(select(func.count(GameplayEvent.id))) == 1
        assert database.scalar(select(func.count(GameResult.id))) == 0


def test_empty_database_download_is_valid_zip():
    response = client.get("/api/v1/game/exports/collection", headers=HEADERS)
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        assert json.loads(archive.read("manifest.json"))["counts"]["game_sessions"] == 0


def test_postgres_download_uses_consistent_read_only_snapshot(monkeypatch):
    from types import SimpleNamespace
    from app.modules.game import collection_export

    statements = []
    database = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        connection=lambda: SimpleNamespace(exec_driver_sql=statements.append),
    )

    def export(selected, folder):
        assert selected is database
        assert statements == [
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        ]
        for name in (
            "game_sessions.csv",
            "student_answers.csv",
            "game_events.csv",
            "game_analytics.csv",
            "independent_assessment_labels.csv",
            "manifest.json",
        ):
            (folder / name).write_text("synthetic", encoding="utf-8")

    monkeypatch.setattr(collection_export, "export_game_data", export)
    content, name = collection_zip(database)
    assert content.startswith(b"PK") and name.endswith(".zip")
