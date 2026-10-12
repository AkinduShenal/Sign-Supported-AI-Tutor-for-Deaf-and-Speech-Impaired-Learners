"""Actual revisions, content semantics, preservation and opt-in local PostgreSQL."""

import ast
import json
import os
import re
import subprocess
import sys
import uuid
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, create_engine, event, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.curriculum.models import CurriculumConcept, CurriculumDocument
from app.modules.game.content_models import GameActivity, GameActivityVariant
from app.modules.game.models import GameResult, GameSession
from app.modules.quiz.models import QuizResult
from app.modules.tutor.models import TutorStrategyPrediction
from scripts.seed_equations_curriculum import (
    CURRICULUM_TABLES,
    load_manifest as curriculum_manifest,
    seed_curriculum,
)
from scripts.seed_equations_game_activities import (
    TABLE_NAMES,
    SeedConflictError,
    load_manifest,
    seed_game_activities,
    validate_manifest,
)

BACKEND = Path(__file__).parents[1]
POSTGRES_URL = os.environ.get("GAME_CONTENT_TEST_DATABASE_URL")


def scripts():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    return ScriptDirectory.from_config(config)


def local_engine(raw):
    url = make_url(raw)
    if url.host not in {"localhost", "127.0.0.1", "::1"} or not (
        url.database or ""
    ).startswith("game_content_test_"):
        pytest.fail("Only disposable local game_content_test_* databases are allowed")
    return create_engine(url)


@pytest.fixture(params=["sqlite"] + (["postgresql"] if POSTGRES_URL else []))
def database(request):
    engine = (
        local_engine(POSTGRES_URL)
        if request.param == "postgresql"
        else create_engine("sqlite+pysqlite:///:memory:")
    )
    if request.param == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_fks(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    assert inspect(engine).get_table_names() == [], "Use an empty disposable DB"
    Base.metadata.create_all(
        engine,
        tables=[
            t
            for t in Base.metadata.sorted_tables
            if t.name not in (*TABLE_NAMES, *CURRICULUM_TABLES)
        ],
    )
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        scripts().get_revision("20261011_0006").module.upgrade()
        scripts().get_revision("20261011_0007").module.upgrade()
    try:
        with Session(engine) as session:
            seed_curriculum(session, curriculum_manifest())
            session.commit()
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def snapshot(database, names, legacy_postgres=False):
    if legacy_postgres:
        quote = database.get_bind().dialect.identifier_preparer.quote
        return {
            name: database.execute(
                text(
                    f"SELECT to_jsonb(t)::text FROM {quote(name)} AS t ORDER BY to_jsonb(t)::text"
                )
            )
            .scalars()
            .all()
            for name in names
        }
    return {
        name: database.execute(
            select(Base.metadata.tables[name]).order_by(
                *Base.metadata.tables[name].primary_key
            )
        ).all()
        for name in names
    }


def populate_evidence(database, legacy_quiz=False):
    now = datetime.now(UTC)
    session = GameSession(
        game_session_id="old-session",
        student_id="old-student",
        concept_id="linear_equations",
        learning_cycle_id=uuid.uuid4(),
        assessment_phase="pre_tutor",
    )
    database.add(session)
    database.flush()
    game = GameResult(
        game_session_id=session.game_session_id,
        student_id=session.student_id,
        concept_id=session.concept_id,
        tasks_total=6,
        tasks_attempted=6,
        tasks_completed=6,
        successful_tasks=5,
        game_success_rate=5 / 6,
        game_completion_rate=1,
        game_avg_attempts_per_task=1,
        game_hint_rate=0,
        game_difficulty_level="beginner",
        game_active_time_sec=60,
        completed_at=now,
        engagement_level="medium",
        behavioral_difficulty="medium",
        hint_dependency=0,
        game_mastery_score=5 / 6,
    )
    quiz = QuizResult(
        quiz_session_id="old-quiz",
        student_id=session.student_id,
        concept_id=session.concept_id,
        weak_concept="none",
        quiz_mastery_score=1,
        recommended_support_level="low",
        questions_total=1,
        questions_attempted=1,
        correct_answers=1,
        quiz_accuracy=1,
        quiz_avg_response_time_sec=5,
        quiz_hint_rate=0,
        misconception_code="none",
        quiz_difficulty_level="beginner",
        quiz_attempt_count=1,
        completed_at=now,
    )
    database.add(game)
    if legacy_quiz:
        # Applied history lacks newer Quiz fields. Seed its actual historical
        # shape rather than hiding that unrelated migration gap with new DDL.
        quiz.id = uuid.uuid4()
        table = Table("quiz_results", MetaData(), autoload_with=database.connection())
        database.execute(
            table.insert().values(
                **{key: value for key, value in vars(quiz).items() if key in table.c}
            )
        )
    else:
        database.add(quiz)
    database.flush()
    database.add(
        TutorStrategyPrediction(
            student_id=session.student_id,
            concept_id=session.concept_id,
            quiz_result_id=quiz.id,
            game_result_id=game.id,
            primary_strategy="step_by_step",
            confidence=0.5,
            model_version="test",
            preferred_mode="visual",
            sign_support_required=True,
            input_snapshot={"preserve": True},
        )
    )
    database.commit()


def test_seed_counts_references_idempotency_and_preservation(database):
    populate_evidence(database)
    existing = [n for n in Base.metadata.tables if n not in TABLE_NAMES]
    before = snapshot(database, existing)
    statements = []

    def capture(_, __, statement, ___, ____, _____):
        statements.append(statement)

    event.listen(database.get_bind(), "before_cursor_execute", capture)
    try:
        first = seed_game_activities(database, load_manifest())
        database.commit()
        seeded = snapshot(database, TABLE_NAMES)
        second = seed_game_activities(database, load_manifest())
        database.commit()
    finally:
        event.remove(database.get_bind(), "before_cursor_execute", capture)
    assert first["inserted"] == dict(zip(TABLE_NAMES, (8, 18)))
    assert second["inserted"] == dict.fromkeys(TABLE_NAMES, 0)
    assert second["reused"] == dict(zip(TABLE_NAMES, (8, 18)))
    assert snapshot(database, TABLE_NAMES) == seeded
    assert snapshot(database, existing) == before
    activities = {a.activity_id: a for a in database.scalars(select(GameActivity))}
    variants = database.scalars(select(GameActivityVariant)).all()
    assert Counter(activities[v.activity_id].difficulty_level for v in variants) == {
        "easy": 6,
        "medium": 6,
        "hard": 6,
    }
    assert all(
        database.get(CurriculumConcept, a.curriculum_concept_id)
        for a in activities.values()
    )
    assert all(v.status == "draft" and v.prompt_si is None for v in variants)
    assert all(
        a.status == "draft" and a.title_si is None and a.instruction_si is None
        for a in activities.values()
    )
    assert sum(v.source_document_id is not None for v in variants) == 5
    assert all(not a.activity_config["essential_audio"] for a in activities.values())
    writes = [
        s
        for s in statements
        if s.lstrip()
        .upper()
        .startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"))
    ]
    assert len(writes) == 26 and all(
        any(s.startswith(f"INSERT INTO {n} ") for n in TABLE_NAMES) for s in writes
    )


def test_conflict_rolls_back_entire_import_and_preserves_promotions(database):
    manifest = load_manifest()
    seed_game_activities(database, manifest)
    database.commit()
    row = database.get(GameActivityVariant, "LEQ_BANK_E_001")
    row.status = "reviewed"
    database.commit()
    seed_game_activities(database, manifest)
    database.commit()
    assert row.status == "reviewed"
    before = snapshot(database, TABLE_NAMES)
    changed = deepcopy(manifest)
    changed["variants"][-1]["prompt_en"] += " Conflicting revision."
    # Missing early row would be inserted before the late conflict; rollback restores it.
    database.delete(row)
    database.commit()
    before = snapshot(database, TABLE_NAMES)
    database.rollback()
    with pytest.raises(SeedConflictError, match="LEQ_BANK_H_006"):
        with database.begin():
            seed_game_activities(database, changed)
    assert snapshot(database, TABLE_NAMES) == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m["variants"].pop(),
        lambda m: m["variants"][0].update(variant_id="LEQ_E_001"),
        lambda m: m["variants"][0].update(activity_id="unknown"),
        lambda m: m["variants"][0].update(variant_version=0),
        lambda m: m["variants"][0].update(status="approved"),
        lambda m: m["variants"][0]["answer_key"].update(final_answer="99"),
        lambda m: m["variants"][0]["question_config"]["steps"][0].update(step_number=2),
        lambda m: m["variants"][0]["question_config"]["steps"][0].update(choices=[]),
        lambda m: m["variants"][0]["question_config"].update(essential_audio=True),
        lambda m: m["activities"][0]["activity_config"].update(essential_audio=True),
        lambda m: m["variants"][14].update(source_page_start=0),
        lambda m: m["variants"][14].update(source_page_end=0),
        lambda m: m["variants"][14].update(source_page_start=3, source_page_end=2),
        lambda m: m["variants"][0].update(source_language="en"),
        lambda m: m["variants"][0]["question_config"].update(javascript="alert(1)"),
        lambda m: m["activities"][0].update(concept_id="new_concept"),
    ],
)
def test_invalid_manifest_rejected(mutation):
    manifest = deepcopy(load_manifest())
    mutation(manifest)
    with pytest.raises(ValueError):
        validate_manifest(manifest)


def test_mathematical_answers_choices_and_verified_pages():
    # Independent arithmetic checks, including denominator and story semantics.
    checks = [
        lambda x: x + 3 == 7,
        lambda x: x + 5 == 12,
        lambda x: x - 4 == 6,
        lambda x: x - 7 == 5,
        lambda x: 3 * x == 12,
        lambda x: x / 4 == 3,
        lambda x: 2 * x + 8 == x + 12,
        lambda x: 3 * x - 5 == x + 9,
        lambda x: 2 * (x - 3) == 8,
        lambda x: 3 * (x + 2) == 18,
        lambda x: 2 * x + 5 == 17,
        lambda x: 4 * x - 7 == 13,
        lambda x: x / 2 + 3 == 7,
        lambda x: (x - 2) / 3 == 4,
        lambda x: 12 / x - 12 / (2 * x) == 2,
        lambda x: 3 / (x + 2) == Fraction(1, 2),
        lambda x: 60 / x - 3 == 2,
        lambda x: 270 / (x + 1) == 45,
    ]
    expected = [4, 7, 10, 12, 4, 12, 4, 7, 7, 4, 6, 5, 8, 14, 3, 4, 12, 5]
    manifest = load_manifest()

    def arithmetic(expression, x):
        # Test-only arithmetic interpreter: no eval, calls or attributes.
        expression = re.sub(r"(?<=\d)(?=[x(])", "*", expression.strip())

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                return Fraction(node.value)
            if isinstance(node, ast.Name) and node.id == "x":
                return x
            if isinstance(node, ast.BinOp):
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    return left / right
            raise AssertionError("Unsupported mathematical expression in test")

        return visit(ast.parse(expression, mode="eval").body)

    for variant, check, answer in zip(
        manifest["variants"], checks, expected, strict=True
    ):
        assert Fraction(variant["answer_key"]["final_answer"]) == answer
        assert check(Fraction(answer))
        for step in variant["question_config"]["steps"]:
            for equation in (step["equation"], step["result_equation"]):
                left, right = equation.split("=")
                assert arithmetic(left, Fraction(answer)) == arithmetic(
                    right, Fraction(answer)
                )
        numeric = [
            Fraction(c["label"])
            for c in variant["question_config"]["steps"][-1]["choices"]
        ]
        assert sum(check(value) for value in numeric) == 1
    assert [
        (v["source_page_start"], v["source_page_end"])
        for v in manifest["variants"][-4:]
    ] == [(1, 2), (3, 3), (3, 3), (4, 4)]
    assert all(len(v["question_config"]["steps"]) > 1 for v in manifest["variants"][6:])


def test_constraints_foreign_keys_and_default_values(database):
    inspector = inspect(database.get_bind())
    assert [len(inspector.get_columns(n)) for n in TABLE_NAMES] == [13, 13]
    assert [len(inspector.get_check_constraints(n)) for n in TABLE_NAMES] == [3, 5]
    assert all(len(inspector.get_indexes(n)) == 3 for n in TABLE_NAMES)
    for name in TABLE_NAMES:
        assert all(
            c["nullable"]
            == (
                c["name"]
                in {
                    "title_si",
                    "instruction_si",
                    "prompt_si",
                    "source_document_id",
                    "source_page_start",
                    "source_page_end",
                }
            )
            for c in inspector.get_columns(name)
        )
    seed_game_activities(database, load_manifest())
    database.commit()
    activity = database.get(GameActivity, "LEQ_BASIC_ADD_SUB")
    assert activity.created_at and activity.updated_at
    # Exercise actual DB checks, separate from the manifest validation.
    for model, key, field, value in [
        (GameActivity, activity.activity_id, "difficulty_level", "invalid"),
        (GameActivity, activity.activity_id, "activity_version", 0),
        (GameActivity, activity.activity_id, "status", "invalid"),
        (GameActivity, activity.activity_id, "curriculum_concept_id", uuid.uuid4()),
        (GameActivityVariant, "LEQ_BANK_E_001", "activity_id", "missing"),
        (GameActivityVariant, "LEQ_BANK_E_001", "variant_version", 0),
        (GameActivityVariant, "LEQ_BANK_E_001", "source_page_start", 0),
        (GameActivityVariant, "LEQ_BANK_E_001", "source_page_end", -1),
        (GameActivityVariant, "LEQ_BANK_E_001", "source_document_id", uuid.uuid4()),
    ]:
        with pytest.raises(IntegrityError), database.begin_nested():
            setattr(database.get(model, key), field, value)
            database.flush()
    with pytest.raises(IntegrityError), database.begin_nested():
        variant = database.get(GameActivityVariant, "LEQ_BANK_E_001")
        variant.source_page_start = 3
        variant.source_page_end = 2
        database.flush()
    with pytest.raises(IntegrityError), database.begin_nested():
        database.delete(database.get(GameActivity, activity.activity_id))
        database.flush()
    with pytest.raises(IntegrityError), database.begin_nested():
        database.delete(database.get(CurriculumConcept, activity.curriculum_concept_id))
        database.flush()
    variant = database.get(GameActivityVariant, "LEQ_BANK_H_004")
    source_id = variant.source_document_id
    # Curriculum content also uses SET NULL, so removing its source must preserve variants.
    database.delete(database.get(CurriculumDocument, source_id))
    database.flush()
    database.expire_all()
    assert (
        database.get(GameActivityVariant, variant.variant_id).source_document_id is None
    )
    database.rollback()
    mapping = activity.curriculum_concept_id
    database.execute(
        text(
            "INSERT INTO game_activity_bank (activity_id,curriculum_concept_id,difficulty_level,activity_type,title_en,instruction_en) VALUES (:id,:concept,'easy','future_renderer','Default check','Solve')"
        ),
        {
            "id": "DEFAULT_CHECK",
            "concept": mapping.hex
            if database.get_bind().dialect.name == "sqlite"
            else mapping,
        },
    )
    database.flush()
    default = database.get(GameActivity, "DEFAULT_CHECK")
    assert (default.activity_config, default.activity_version, default.status) == (
        {},
        1,
        "draft",
    )


def test_cli_validation_opens_no_database():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed_equations_game_activities"],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": "invalid-on-purpose"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "No database connection" in result.stdout


def test_missing_prerequisite_fails_without_any_bank_inserts(database):
    mapping = database.scalar(
        select(CurriculumConcept).filter_by(concept_id="bracket_equation")
    )
    mapping.status = "inactive"
    database.commit()
    with pytest.raises(SeedConflictError, match="mappings"):
        seed_game_activities(database, load_manifest())
    assert not database.scalars(select(GameActivity)).all()
    assert not database.scalars(select(GameActivityVariant)).all()


def test_revision_rollback_removes_only_its_own_tables(database):
    populate_evidence(database)
    existing = [n for n in Base.metadata.tables if n not in TABLE_NAMES]
    before = snapshot(database, existing)
    database.rollback()
    seed_game_activities(database, load_manifest())
    database.commit()
    with (
        database.get_bind().begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        scripts().get_revision("20261011_0007").module.downgrade()
        assert not set(TABLE_NAMES).intersection(inspect(connection).get_table_names())
        scripts().get_revision("20261011_0007").module.upgrade()
    assert snapshot(database, existing) == before


@pytest.mark.skipif(
    not os.environ.get("GAME_CONTENT_MIGRATION_TEST_DATABASE_URL"),
    reason="Requires explicitly supplied disposable local PostgreSQL",
)
def test_full_chain_populated_upgrade_and_schema_equivalence(monkeypatch):
    raw = os.environ["GAME_CONTENT_MIGRATION_TEST_DATABASE_URL"]
    engine = local_engine(raw)
    assert inspect(engine).get_table_names() == [], "Use a new empty DB"

    from app.core.config import settings

    monkeypatch.setattr(settings, "database_url", raw)
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))

    def migrate(revision):
        command.upgrade(config, revision)

    def schema():
        inspector = inspect(engine)
        return json.dumps(
            {
                n: {
                    "columns": inspector.get_columns(n),
                    "pk": inspector.get_pk_constraint(n),
                    "checks": inspector.get_check_constraints(n),
                    "fks": inspector.get_foreign_keys(n),
                    "indexes": inspector.get_indexes(n),
                    "unique": inspector.get_unique_constraints(n),
                }
                for n in inspector.get_table_names()
                if n not in (*TABLE_NAMES, "alembic_version")
            },
            sort_keys=True,
            default=str,
        )

    try:
        migrate("20261011_0006")
        with Session(engine) as database:
            seed_curriculum(database, curriculum_manifest())
            database.commit()
            populate_evidence(database, legacy_quiz=True)
            existing = [
                n for n in inspect(engine).get_table_names() if n != "alembic_version"
            ]
            before = snapshot(database, existing, legacy_postgres=True)
        old_schema = schema()
        migrate("head")
        assert set(inspect(engine).get_table_names()) == set(existing) | set(
            TABLE_NAMES
        ) | {"alembic_version"}
        assert schema() == old_schema
        with Session(engine) as database:
            seed_game_activities(database, load_manifest())
            database.commit()
            seed_game_activities(database, load_manifest())
            database.commit()
            assert snapshot(database, existing, legacy_postgres=True) == before
            assert (
                database.scalar(text("SELECT version_num FROM alembic_version"))
                == "20261011_0007"
            )
        with engine.connect() as connection:
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
    finally:
        engine.dispose()
