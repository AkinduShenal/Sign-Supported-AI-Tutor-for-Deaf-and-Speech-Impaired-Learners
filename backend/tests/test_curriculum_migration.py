"""Exercise the hand-written revision rather than only ORM create_all."""

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.curriculum import models as curriculum_models  # noqa: F401
from app.modules.game.models import GameResult, GameSession

TABLE_NAMES = {
    "curriculum_versions",
    "curriculum_units",
    "math_concepts",
    "curriculum_concepts",
    "curriculum_documents",
    "concept_content",
}


def _scripts():
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "alembic")
    )
    return ScriptDirectory.from_config(config)


def test_curriculum_revision_follows_existing_head():
    scripts = _scripts()
    assert scripts.get_heads() == ["20261011_0006"]
    assert scripts.get_revision("20261011_0006").down_revision == "20261009_0005"


def test_revision_creates_six_tables_and_reverses_only_its_own_objects():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    revision = _scripts().get_revision("20261011_0006").module
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(
            text("CREATE TABLE existing_component (id INTEGER PRIMARY KEY, value TEXT)")
        )
        connection.execute(
            text("INSERT INTO existing_component VALUES (1, 'preserve')")
        )
        context = MigrationContext.configure(
            connection, opts={"target_metadata": Base.metadata}
        )
        with Operations.context(context):
            revision.upgrade()
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == TABLE_NAMES | {"existing_component"}
        assert len(inspector.get_indexes("concept_content")) == 5
        source_fk = next(
            fk
            for fk in inspector.get_foreign_keys("concept_content")
            if fk["constrained_columns"] == ["source_document_id"]
        )
        assert source_fk["options"]["ondelete"] == "SET NULL"
        version_fk = next(
            fk
            for fk in inspector.get_foreign_keys("curriculum_concepts")
            if fk["constrained_columns"] == ["curriculum_version_id", "unit_id"]
        )
        assert version_fk["referred_columns"] == ["curriculum_version_id", "id"]
        assert len(inspector.get_check_constraints("concept_content")) == 7
        with Operations.context(context):
            revision.downgrade()
        assert inspect(connection).get_table_names() == ["existing_component"]
        assert (
            connection.execute(
                text("SELECT value FROM existing_component")
            ).scalar_one()
            == "preserve"
        )
    engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("CURRICULUM_MIGRATION_TEST_DATABASE_URL"),
    reason="Full PostgreSQL chain requires an explicitly supplied disposable local database",
)
def test_postgres_full_chain_preserves_existing_game_data():
    url = make_url(os.environ["CURRICULUM_MIGRATION_TEST_DATABASE_URL"])
    if url.host not in {"localhost", "127.0.0.1", "::1"} or not (
        url.database or ""
    ).startswith("curriculum_test_"):
        pytest.fail(
            "Migration test requires a disposable local curriculum_test_* database"
        )
    engine = create_engine(url)
    backend = Path(__file__).parents[1]
    environment = dict(
        os.environ, DATABASE_URL=url.render_as_string(hide_password=False)
    )

    def migrate(direction, revision):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", direction, revision],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def existing_schema():
        inspector = inspect(engine)
        return json.dumps(
            {
                name: {
                    "columns": inspector.get_columns(name),
                    "pk": inspector.get_pk_constraint(name),
                    "unique": inspector.get_unique_constraints(name),
                    "checks": inspector.get_check_constraints(name),
                    "fks": inspector.get_foreign_keys(name),
                    "indexes": inspector.get_indexes(name),
                }
                for name in inspector.get_table_names()
                if name not in TABLE_NAMES and name != "alembic_version"
            },
            sort_keys=True,
            default=str,
        )

    def game_rows():
        with engine.connect() as connection:
            return (
                connection.execute(
                    text(
                        "SELECT to_jsonb(result)::text FROM game_results AS result ORDER BY id"
                    )
                )
                .scalars()
                .all()
            )

    try:
        assert inspect(engine).get_table_names() == [], "Use a new empty test database"
        migrate("upgrade", "20261009_0005")
        with Session(engine) as database:
            session = GameSession(
                game_session_id="migration-test-session",
                student_id="migration-test-student",
                concept_id="legacy_unknown_concept",
                learning_cycle_id=uuid.uuid4(),
                assessment_phase="pre_tutor",
            )
            database.add(session)
            database.flush()
            database.add(
                GameResult(
                    game_session_id=session.game_session_id,
                    student_id=session.student_id,
                    concept_id=session.concept_id,
                    tasks_total=6,
                    tasks_attempted=6,
                    tasks_completed=6,
                    successful_tasks=5,
                    game_success_rate=5 / 6,
                    game_completion_rate=1,
                    game_avg_attempts_per_task=1.5,
                    game_hint_rate=1 / 6,
                    game_difficulty_level="intermediate",
                    game_active_time_sec=60,
                    completed_at=datetime.now(UTC),
                    engagement_level="medium",
                    behavioral_difficulty="medium",
                    hint_dependency=1 / 6,
                    game_mastery_score=5 / 6,
                )
            )
            database.commit()
        before_schema, before_rows = existing_schema(), game_rows()
        migrate("upgrade", "head")
        assert TABLE_NAMES.issubset(inspect(engine).get_table_names())
        assert existing_schema() == before_schema and game_rows() == before_rows
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == "20261011_0006"
            )
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "compare_server_default": True,
                    "include_object": lambda obj, name, kind, reflected, other: (
                        kind != "table" or name in TABLE_NAMES
                    ),
                },
            )
            assert compare_metadata(context, Base.metadata) == []
        migrate("downgrade", "20261009_0005")
        assert not TABLE_NAMES.intersection(inspect(engine).get_table_names())
        assert existing_schema() == before_schema and game_rows() == before_rows
        migrate("upgrade", "head")
        assert existing_schema() == before_schema and game_rows() == before_rows
    finally:
        engine.dispose()
