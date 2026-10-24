"""Local SQLite coverage for the draft dynamic Quiz. No configured DB is used."""

import importlib.util
import itertools
import re
import uuid
from collections import Counter
from fractions import Fraction
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.quiz.models import (
    MisconceptionMapping, QuizQuestion, QuizQuestionOption, QuizResponse,
    QuizResult, QuizSession, QuizSessionQuestion,
)
from scripts.generate_quiz_dynamic_bank import BANK_VERSION, build_bank
from scripts.seed_quiz_dynamic import load_bank, seed_bank, require_local_url
from scripts.seed_quiz_phase2 import load_bank as load_fixed, seed_bank as seed_fixed

TABLES = [model.__table__ for model in (
    MisconceptionMapping, QuizQuestion, QuizQuestionOption, QuizSession,
    QuizSessionQuestion, QuizResponse, QuizResult,
)]


def _evaluate(side: str, value: int) -> Fraction:
    expression = side.replace("÷", "/")
    expression = re.sub(r"(\d)x", r"\1*x", expression).replace("x", str(value))
    expression = re.sub(r"(\d)\(", r"\1*(", expression)
    # Only generated integer equations reach this eval; reject any other tokens.
    assert re.fullmatch(r"[0-9+*()/ -]+", expression)
    return Fraction(eval(expression, {"__builtins__": {}}, {}))


def test_bank_math_blueprint_and_draft_status():
    bank = load_bank()
    assert bank == build_bank()
    assert len(bank) == len({q["question_code"] for q in bank}) == 60
    assert Counter(q["logical_slot"] for q in bank) == {f"S{i:02d}": 6 for i in range(1, 11)}
    assert Counter(q["difficulty_level"] for q in bank) == {"easy": 24, "medium": 24, "hard": 12}
    original = load_fixed()["questions"]
    for q in bank:
        slot = int(q["logical_slot"][1:])
        assert q["subconcept_code"] == original[slot-1]["subconcept"]
        assert q["difficulty_level"] == original[slot-1]["difficulty"]
        assert q["teacher_validated"] is False and q["bank_version"] == BANK_VERSION
        assert q["review_status"] == "DRAFT_REVIEW" and q["research_use"] == "DEVELOPMENT_ONLY"
        lhs, rhs = q["question_text_en"].removeprefix("Solve ").removesuffix(".").split(" = ")
        correct = int(q["answer"])
        assert _evaluate(lhs, correct) == _evaluate(rhs, correct)
        assert all(_evaluate(lhs, wrong) != _evaluate(rhs, wrong)
                   for wrong in range(correct-25, correct+26) if wrong != correct)
        options = q["options"]
        assert len(options) == len({o["text"] for o in options}) == 4
        assert [o["text"] for o in options if o["is_correct"]] == [q["answer"]]


def test_import_rejects_remote_and_is_repeat_safe():
    require_local_url("sqlite:///:memory:")
    try:
        require_local_url("postgresql+psycopg://u:p@db.example.com/research")
        assert False, "remote URL was accepted"
    except ValueError:
        pass
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=TABLES)
    with Session(engine) as database:
        with database.begin():
            assert seed_fixed(database, load_fixed()) == (10, 0)
            assert seed_bank(database, load_bank()) == (60, 0)
        with database.begin():
            assert seed_bank(database, load_bank()) == (0, 60)
        assert database.scalar(select(QuizQuestion).where(QuizQuestion.question_code == "DEV-PRE-LE-01"))
        assert len(database.scalars(select(QuizQuestion)).all()) == 70
    engine.dispose()


def test_dynamic_sessions_are_saved_scored_and_independent(monkeypatch):
    monkeypatch.setattr(settings, "quiz_dynamic_dev_enabled", True)
    choices = itertools.count()
    monkeypatch.setattr("app.modules.quiz.service.secrets.choice",
                        lambda group: group[(next(choices) // 10) % len(group)])
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=TABLES)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database, database.begin():
        seed_fixed(database, load_fixed())
        seed_bank(database, load_bank())

    def override():
        with factory() as database:
            yield database

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        assert len(client.get("/api/v1/quiz/questions").json()) == 10
        sessions = []
        for number in range(2):
            request = {"student_id": f"STU_{number+1:03d}", "client_session_id": str(uuid.uuid4()),
                       "bank_mode": "dynamic_dev", "assessment_phase": "pre_tutor"}
            created = client.post("/api/v1/quiz/sessions", json=request)
            assert created.status_code == 201, created.text
            assert client.post("/api/v1/quiz/sessions", json=request).json() == created.json()
            sid = created.json()["quiz_session_id"]
            questions = client.get(f"/api/v1/quiz/sessions/{sid}/questions").json()
            assert len(questions) == 10
            assert all("is_correct" not in option and "misconception_code" not in option
                       for question in questions for option in question["options"])
            assert Counter(q["difficulty_level"] for q in questions) == {"easy": 4, "medium": 4, "hard": 2}
            assert len({q["question_code"].split("-V")[0] for q in questions}) == 10
            assert questions == client.get(f"/api/v1/quiz/sessions/{sid}/questions").json()
            sessions.append((sid, questions))
        first, second = sessions
        assert [q["id"] for q in first[1]] != [q["id"] for q in second[1]]
        assert client.post(f"/api/v1/quiz/sessions/{second[0]}/complete").status_code == 409
        fixed = client.post("/api/v1/quiz/sessions", json={"student_id": "STU_010",
            "client_session_id": str(uuid.uuid4())})
        assert fixed.status_code == 201
        fixed_rejects_draft = client.post(f"/api/v1/quiz/sessions/{fixed.json()['quiz_session_id']}/responses", json={
            "question_id": first[1][0]["id"], "selected_option_id": first[1][0]["options"][0]["id"],
            "question_order": 1, "response_time_sec": 1.0, "confidence_level": "low",
        })
        assert fixed_rejects_draft.status_code == 422
        outsider = next(q for q in second[1] if q["id"] not in {item["id"] for item in first[1]})
        wrong_session = client.post(f"/api/v1/quiz/sessions/{first[0]}/responses", json={
            "question_id": outsider["id"], "selected_option_id": outsider["options"][0]["id"],
            "question_order": 1, "response_time_sec": 1.2, "confidence_level": "low",
        })
        assert wrong_session.status_code == 422
        wrong_order = client.post(f"/api/v1/quiz/sessions/{first[0]}/responses", json={
            "question_id": first[1][0]["id"], "selected_option_id": first[1][0]["options"][0]["id"],
            "question_order": 2, "response_time_sec": 1.2, "confidence_level": "low",
        })
        assert wrong_order.status_code == 422
        for order, question in enumerate(first[1], 1):
            option = question["options"][0]
            result = client.post(f"/api/v1/quiz/sessions/{first[0]}/responses", json={
                "question_id": question["id"], "selected_option_id": option["id"],
                "question_order": order, "response_time_sec": order + 0.25, "confidence_level": "medium",
            })
            assert result.status_code == 201, result.text
            assert result.json()["response_time_sec"] == order + 0.25
            assert result.json()["confidence_level"] == "medium"
        complete = client.post(f"/api/v1/quiz/sessions/{first[0]}/complete")
        assert complete.status_code == 200, complete.text
        monkeypatch.setattr(settings, "quiz_dynamic_dev_enabled", False)
        assert client.get(f"/api/v1/quiz/sessions/{first[0]}/questions").status_code == 200
        disabled = client.post("/api/v1/quiz/sessions", json={"student_id": "STU_003",
            "client_session_id": str(uuid.uuid4()), "bank_mode": "dynamic_dev"})
        assert disabled.status_code == 409
        with factory() as database:
            assert len(database.scalars(select(QuizSessionQuestion).where(QuizSessionQuestion.quiz_session_id == first[0])).all()) == 10
            assert len(database.scalars(select(QuizResponse).where(QuizResponse.quiz_session_id == first[0])).all()) == 10
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        engine.dispose()


def test_migration_upgrades_legacy_quiz_tables_locally():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=TABLES)
    with Session(engine) as database, database.begin():
        database.add(QuizQuestion(question_code="HISTORIC-1", concept_id="linear_equations",
                                  subconcept_code="one_step_addition", question_type="multiple_choice",
                                  question_text_en="Solve x+1=2", question_text_si="x+1=2",
                                  difficulty_level="easy", assessment_use="pre", teacher_validated=True,
                                  is_active=True))
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE quiz_session_questions")
        connection.exec_driver_sql("ALTER TABLE quiz_sessions DROP COLUMN bank_version")
        connection.exec_driver_sql("DROP INDEX ix_quiz_questions_bank_slot")
        connection.exec_driver_sql("ALTER TABLE quiz_questions DROP COLUMN logical_slot")
        connection.exec_driver_sql("ALTER TABLE quiz_questions DROP COLUMN bank_version")
        path = Path(__file__).parents[1] / "alembic" / "versions" / "20261021_0008_add_dynamic_quiz_selection.py"
        spec = importlib.util.spec_from_file_location("quiz_dynamic_migration", path)
        migration = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(migration)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
    assert "bank_version" in {col["name"] for col in inspect(engine).get_columns("quiz_questions")}
    assert "quiz_session_questions" in inspect(engine).get_table_names()
    with Session(engine) as database:
        assert database.scalar(select(QuizQuestion).where(QuizQuestion.question_code == "HISTORIC-1"))
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
    assert "bank_version" not in {col["name"] for col in inspect(engine).get_columns("quiz_questions")}
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM quiz_questions WHERE question_code = 'HISTORIC-1'")) == 1
    engine.dispose()
