"""CLI verification with empty synthetic local databases; no production reads."""

import csv
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.db.base import Base
from app.modules.game.models import (
    GameResult,
    GameSession,
    GameTaskAttempt,
    GameplayEvent,
)
from scripts import export_game_collection as exporter


@pytest.fixture
def local_url(tmp_path):
    url = f"sqlite+pysqlite:///{(tmp_path / 'synthetic-empty.sqlite').as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(
        engine,
        tables=[
            GameSession.__table__,
            GameplayEvent.__table__,
            GameTaskAttempt.__table__,
            GameResult.__table__,
        ],
    )
    engine.dispose()
    return url


def test_one_command_uses_configured_url_and_creates_distinct_exports(
    monkeypatch, tmp_path, local_url, capsys
):
    monkeypatch.setenv("DATABASE_URL", local_url)
    monkeypatch.setattr(exporter, "DEFAULT_EXPORT_ROOT", tmp_path / "exports")
    monkeypatch.setattr(sys, "argv", ["export_game_collection"])
    destinations = []
    for _ in range(2):
        exporter.main()
        report = json.loads(capsys.readouterr().out)
        assert report["game_sessions"] == report["student_answers"] == 0
        output = Path(report["output_dir"])
        destinations.append(output)
        assert output.parent == tmp_path / "exports"
        assert {p.name for p in output.iterdir()} == {
            "game_sessions.csv",
            "student_answers.csv",
            "game_events.csv",
            "game_analytics.csv",
            "independent_assessment_labels.csv",
            "manifest.json",
        }
        with (output / "student_answers.csv").open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            assert next(csv.reader(handle)) == list(exporter.ANSWER_FIELDS)
    assert destinations[0] != destinations[1]


def test_explicit_flags_override_settings(monkeypatch, tmp_path, local_url, capsys):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://unused:secret@invalid.example/db"
    )
    output = tmp_path / "explicit"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_game_collection",
            "--database-url",
            local_url,
            "--output-dir",
            str(output),
        ],
    )
    exporter.main()
    assert json.loads(capsys.readouterr().out)["output_dir"] == str(output)


def test_database_url_is_loaded_from_env_file(monkeypatch, tmp_path, local_url, capsys):
    from app.core.config import Settings

    env_file = tmp_path / ".env"
    env_file.write_text(f"DATABASE_URL={local_url}\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)
    monkeypatch.setattr(exporter, "DEFAULT_EXPORT_ROOT", tmp_path / "exports")
    monkeypatch.setattr(sys, "argv", ["export_game_collection"])
    exporter.main()
    assert json.loads(capsys.readouterr().out)["game_sessions"] == 0


def test_existing_export_is_preserved_before_any_connection(monkeypatch, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "student_answers.csv"
    marker.write_text("preserve original evidence", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_game_collection",
            "--database-url",
            "sqlite://",
            "--output-dir",
            str(output),
        ],
    )
    monkeypatch.setattr(
        exporter,
        "create_engine",
        lambda _: pytest.fail("must refuse before connecting"),
    )
    with pytest.raises(SystemExit) as error:
        exporter.main()
    assert error.value.code == 2
    assert marker.read_text(encoding="utf-8") == "preserve original evidence"


def test_configured_remote_url_requires_opt_in_without_exposing_credentials(
    monkeypatch, capsys
):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://person:private-password@remote.example/db"
    )
    monkeypatch.setattr(sys, "argv", ["export_game_collection"])
    monkeypatch.setattr(
        exporter,
        "create_engine",
        lambda _: pytest.fail("remote database must not be contacted"),
    )
    with pytest.raises(SystemExit) as error:
        exporter.main()
    assert error.value.code == 2
    text = capsys.readouterr()
    assert "--allow-remote-read" in text.err
    assert "private-password" not in text.err + text.out


def test_remote_opt_in_is_supported_with_mocked_local_transport(
    monkeypatch, tmp_path, local_url, capsys
):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://person:private-password@remote.example/db"
    )
    output = tmp_path / "mock-remote"
    monkeypatch.setattr(
        sys,
        "argv",
        ["export_game_collection", "--allow-remote-read", "--output-dir", str(output)],
    )
    # Exercise the remote guard while routing every connection to local SQLite.
    monkeypatch.setattr(exporter, "create_engine", lambda _: create_engine(local_url))
    exporter.main()
    text = capsys.readouterr()
    assert json.loads(text.out)["game_sessions"] == 0
    assert "private-password" not in text.out + text.err


def test_postgres_export_sets_read_only_transaction(monkeypatch, tmp_path, capsys):
    from types import SimpleNamespace

    statements = []
    disposed = []
    engine = SimpleNamespace(
        dialect=SimpleNamespace(name="postgresql"),
        dispose=lambda: disposed.append(True),
    )

    class FakeSession:
        def __init__(self, selected_engine):
            assert selected_engine is engine

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def connection(self):
            return SimpleNamespace(exec_driver_sql=statements.append)

    def export(database, output):
        assert isinstance(database, FakeSession)
        assert statements == ["SET TRANSACTION READ ONLY"]
        assert output.is_dir()
        return {"game_sessions": 0}

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "export_game_collection",
            "--database-url",
            "postgresql+psycopg://test@127.0.0.1/test",
            "--output-dir",
            str(tmp_path / "readonly"),
        ],
    )
    monkeypatch.setattr(exporter, "create_engine", lambda _: engine)
    monkeypatch.setattr(exporter, "Session", FakeSession)
    monkeypatch.setattr(exporter, "export_game_data", export)
    exporter.main()
    assert json.loads(capsys.readouterr().out)["game_sessions"] == 0
    assert disposed == [True]
