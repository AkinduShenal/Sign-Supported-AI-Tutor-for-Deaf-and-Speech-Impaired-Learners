"""Batch 2 seeding on enforced SQLite FKs and optional disposable local PostgreSQL."""

import os
import subprocess
import sys
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.curriculum.models import (
    ConceptContent,
    CurriculumConcept,
    CurriculumDocument,
    CurriculumUnit,
    CurriculumVersion,
    MathConcept,
)
from app.modules.game.models import GameResult, GameSession
from app.modules.quiz.models import QuizResult
from app.modules.tutor.models import TutorStrategyPrediction
from scripts.seed_equations_curriculum import (
    CONCEPT_TYPES,
    CURRICULUM_TABLES,
    VERSION_CODE,
    SeedConflictError,
    load_manifest,
    seed_curriculum,
    validate_manifest,
)

POSTGRES_URL = os.environ.get("CURRICULUM_SEED_TEST_DATABASE_URL")


@pytest.fixture(params=["sqlite"] + (["postgresql"] if POSTGRES_URL else []))
def database(request):
    if request.param == "postgresql":
        url = make_url(POSTGRES_URL)
        if url.host not in {"localhost", "127.0.0.1", "::1"} or not (
            url.database or ""
        ).startswith("curriculum_test_"):
            pytest.fail("Seed tests require a disposable local curriculum_test_* DB")
        engine = create_engine(url)
    else:
        engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(
        engine,
        tables=[
            table
            for table in Base.metadata.sorted_tables
            if table.name
            not in (*CURRICULUM_TABLES, "game_activity_bank", "game_activity_variants")
        ],
    )
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "alembic")
    )
    revision = ScriptDirectory.from_config(config).get_revision("20261011_0006").module
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            revision.upgrade()
    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def snapshot(database, names=CURRICULUM_TABLES):
    return {
        name: database.execute(
            select(Base.metadata.tables[name]).order_by(
                *Base.metadata.tables[name].primary_key
            )
        ).all()
        for name in names
    }


def test_first_seed_has_expected_structure_documents_and_traceable_content(database):
    manifest = load_manifest()
    before_tables = inspect(database.get_bind()).get_table_names()
    report = seed_curriculum(database, manifest)
    database.commit()
    assert list(report["inserted"].values()) == [1, 1, 10, 10, 2, 11]
    assert not any(report["reused"].values())
    assert inspect(database.get_bind()).get_table_names() == before_tables
    assert "game_activity_bank" not in before_tables
    assert "game_activity_variants" not in before_tables
    version = database.scalar(select(CurriculumVersion))
    assert version.version_code == VERSION_CODE and version.grade_level == 10
    assert version.subject_code == "mathematics" and version.status == "active"
    assert version.start_year is None and version.end_year is None
    unit = database.scalar(select(CurriculumUnit))
    assert unit.curriculum_version_id == version.id and unit.unit_code == "EQUATIONS"
    assert unit.sequence_order == 15 and unit.unit_name_si == "සමීකරණ"
    concepts = database.scalars(select(MathConcept)).all()
    assert {row.concept_id: row.concept_type for row in concepts} == CONCEPT_TYPES
    mappings = database.scalars(
        select(CurriculumConcept).order_by(CurriculumConcept.sequence_order)
    ).all()
    assert [row.concept_id for row in mappings] == list(CONCEPT_TYPES)
    assert all(
        row.unit_id == unit.id and row.curriculum_version_id == version.id
        for row in mappings
    )
    documents = {row.id: row for row in database.scalars(select(CurriculumDocument))}
    assert {row.language_code for row in documents.values()} == {"en", "si"}
    assert all(
        row.file_path.startswith("curriculum/") and row.document_type == "lesson_pdf"
        for row in documents.values()
    )
    mapping_ids = {row.id for row in mappings}
    content = database.scalars(select(ConceptContent)).all()
    assert len(content) == 11
    assert all(row.curriculum_concept_id in mapping_ids for row in content)
    assert all(row.source_document_id in documents for row in content)
    assert all(
        documents[row.source_document_id].language_code == row.language_code
        for row in content
    )
    assert all(
        1 <= row.source_page_start <= row.source_page_end <= 10 for row in content
    )
    assert all(row.status == "draft" and "\ufffd" not in row.content for row in content)
    assert sum(row.language_code == "si" for row in content) == 3


def test_second_seed_preserves_all_values_ids_and_timestamps(database):
    manifest = load_manifest()
    seed_curriculum(database, manifest)
    database.commit()
    before = snapshot(database)
    report = seed_curriculum(database, manifest)
    database.commit()
    assert not any(report["inserted"].values())
    assert list(report["reused"].values()) == [1, 1, 10, 10, 2, 11]
    assert snapshot(database) == before


def test_existing_natural_key_with_different_uuid_is_reused(database):
    manifest = load_manifest()
    existing_id = uuid.uuid4()
    database.add(CurriculumVersion(id=existing_id, **manifest["version"]))
    database.commit()
    report = seed_curriculum(database, manifest)
    database.commit()
    assert report["inserted"]["curriculum_versions"] == 0
    assert report["reused"]["curriculum_versions"] == 1
    assert database.scalar(select(CurriculumUnit)).curriculum_version_id == existing_id


def test_conflict_rolls_back_the_entire_seed(database):
    database.add(
        MathConcept(
            concept_id="quadratic_equations",
            name_en="Team-owned wording",
            concept_type="subtopic",
        )
    )
    database.commit()
    before = snapshot(database)
    database.rollback()
    with pytest.raises(SeedConflictError, match="math_concepts"):
        with database.begin():
            seed_curriculum(database, load_manifest())
    assert snapshot(database) == before


@pytest.mark.parametrize("status", ["reviewed", "approved"])
def test_teacher_promoted_content_is_preserved(database, status):
    manifest = load_manifest()
    seed_curriculum(database, manifest)
    database.commit()
    row = database.scalar(select(ConceptContent))
    row.status = status
    database.commit()
    before = snapshot(database)
    seed_curriculum(database, manifest)
    database.commit()
    assert snapshot(database) == before


def test_edited_content_is_not_overwritten(database):
    manifest = load_manifest()
    seed_curriculum(database, manifest)
    database.commit()
    row = database.scalar(select(ConceptContent))
    row.content = "Teacher's revised explanation; preserve it."
    database.commit()
    before = snapshot(database)
    # snapshot starts a read transaction; explicitly finish it before begin().
    database.rollback()
    with pytest.raises(SeedConflictError, match="concept_content"):
        with database.begin():
            seed_curriculum(database, manifest)
    assert snapshot(database) == before


def test_seed_preserves_populated_game_quiz_tutor_tables_and_creates_no_schema(
    database,
):
    now = datetime.now(UTC)
    session = GameSession(
        game_session_id="seed-test-existing",
        student_id="existing",
        concept_id="linear_equations",
        learning_cycle_id=uuid.uuid4(),
        assessment_phase="pre_tutor",
    )
    database.add(session)
    database.flush()
    game = GameResult(
        game_session_id=session.game_session_id,
        student_id="existing",
        concept_id="linear_equations",
        engagement_level="medium",
        behavioral_difficulty="low",
        hint_dependency=0.0,
        game_mastery_score=1.0,
        tasks_total=1,
        tasks_attempted=1,
        tasks_completed=1,
        successful_tasks=1,
        game_success_rate=1.0,
        game_completion_rate=1.0,
        game_avg_attempts_per_task=1.0,
        game_hint_rate=0.0,
        game_difficulty_level="beginner",
        game_active_time_sec=10,
        completed_at=now,
    )
    quiz = QuizResult(
        quiz_session_id="seed-test-quiz",
        student_id="existing",
        concept_id="linear_equations",
        weak_concept="none",
        quiz_mastery_score=1.0,
        recommended_support_level="low",
        questions_total=1,
        questions_attempted=1,
        correct_answers=1,
        quiz_accuracy=1.0,
        quiz_avg_response_time_sec=5.0,
        quiz_hint_rate=0.0,
        misconception_code="none",
        quiz_difficulty_level="beginner",
        quiz_attempt_count=1,
        completed_at=now,
    )
    database.add_all([game, quiz])
    database.flush()
    database.add(
        TutorStrategyPrediction(
            student_id="existing",
            concept_id="linear_equations",
            quiz_result_id=quiz.id,
            game_result_id=game.id,
            primary_strategy="step_by_step",
            confidence=0.5,
            model_version="synthetic-test",
            preferred_mode="visual",
            sign_support_required=True,
            input_snapshot={"synthetic": True},
        )
    )
    database.commit()
    other_tables = [
        name
        for name in inspect(database.get_bind()).get_table_names()
        if name not in CURRICULUM_TABLES
    ]
    before = snapshot(database, other_tables)
    statements = []

    def capture(_, __, statement, ___, ____, _____):
        statements.append(statement)

    event.listen(database.get_bind(), "before_cursor_execute", capture)
    try:
        seed_curriculum(database, load_manifest())
        database.commit()
        seed_curriculum(database, load_manifest())
        database.commit()
    finally:
        event.remove(database.get_bind(), "before_cursor_execute", capture)
    assert snapshot(database, other_tables) == before
    assert not any(
        statement.lstrip()
        .upper()
        .startswith(("CREATE", "ALTER", "DROP", "DELETE", "UPDATE"))
        for statement in statements
    )
    inserts = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("INSERT")
    ]
    assert all(
        any(f"INSERT INTO {name} " in statement for name in CURRICULUM_TABLES)
        for statement in inserts
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_page_start", 0),
        ("source_page_end", 11),
        ("language_code", "fr"),
        ("status", "approved"),
        ("content", "\ufffd"),
        ("content_type", "game_question"),
    ],
)
def test_invalid_content_is_rejected_before_writing(field, value):
    manifest = deepcopy(load_manifest())
    manifest["content"][0][field] = value
    with pytest.raises(ValueError):
        validate_manifest(manifest)


def test_duplicate_content_key_and_unsafe_document_path_rejected():
    manifest = deepcopy(load_manifest())
    manifest["content"].append(deepcopy(manifest["content"][0]))
    with pytest.raises(ValueError, match="duplicated"):
        validate_manifest(manifest)
    manifest = deepcopy(load_manifest())
    manifest["documents"][0]["record"]["file_path"] = "C:\\private\\lesson.pdf"
    with pytest.raises(ValueError, match="portable"):
        validate_manifest(manifest)


def test_cli_dry_run_does_not_load_database_credentials():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed_equations_curriculum"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": "invalid-on-purpose"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "no database connection" in result.stdout
