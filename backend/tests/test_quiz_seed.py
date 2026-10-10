from collections import Counter

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.quiz.models import (
    MisconceptionMapping,
    QuizQuestion,
    QuizQuestionOption,
    QuizResponse,
    QuizSession,
)
from scripts.seed_quiz_phase2 import load_bank, seed_bank


def test_review_pending_seed_is_repeat_safe_and_has_exact_distribution():
    bank = load_bank()
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            MisconceptionMapping.__table__,
            QuizQuestion.__table__,
            QuizQuestionOption.__table__,
        ],
    )
    with Session(engine) as database:
        with database.begin():
            assert seed_bank(database, bank) == (10, 0)
        with database.begin():
            assert seed_bank(database, bank) == (0, 10)
        questions = database.scalars(select(QuizQuestion)).all()
        options = database.scalars(select(QuizQuestionOption)).all()
        assert len(questions) == 10
        assert len(options) == 40
        assert Counter(question.difficulty_level for question in questions) == {
            "easy": 4,
            "medium": 4,
            "hard": 2,
        }
        assert all(
            question.question_text_en
            and question.question_text_si
            and question.assessment_use == "pre"
            and not question.teacher_validated
            and "review pending" in question.source_ref_en
            for question in questions
        )
        assert sum(option.is_correct for option in options) == 10
    engine.dispose()


def test_ten_question_api_flow_stores_responses_and_completes_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            MisconceptionMapping.__table__,
            QuizQuestion.__table__,
            QuizQuestionOption.__table__,
            QuizSession.__table__,
            QuizResponse.__table__,
        ],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database, database.begin():
        seed_bank(database, load_bank())

    def override_get_db():
        with factory() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        questions_response = client.get(
            "/api/v1/quiz/questions",
            params={"concept_id": "linear_equations", "assessment_phase": "pre_tutor"},
        )
        assert questions_response.status_code == 200
        questions = questions_response.json()
        assert len(questions) == 10
        assert all(len(question["options"]) == 4 for question in questions)
        session_response = client.post(
            "/api/v1/quiz/sessions",
            json={
                "student_id": "PHASE2-TEST",
                "concept_id": "linear_equations",
                "assessment_phase": "pre_tutor",
                "display_language": "bilingual",
            },
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["quiz_session_id"]
        for order, question in enumerate(questions, 1):
            saved = client.post(
                f"/api/v1/quiz/sessions/{session_id}/responses",
                json={
                    "question_id": question["id"],
                    "selected_option_id": question["options"][0]["id"],
                    "response_time_sec": order + 0.25,
                    "confidence_level": "medium",
                    "question_order": order,
                },
            )
            assert saved.status_code == 201, saved.text
            assert saved.json()["saved"] is True
            assert "is_correct" not in saved.json()
        completed = client.post(f"/api/v1/quiz/sessions/{session_id}/complete")
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"
        with factory() as database:
            responses = database.scalars(
                select(QuizResponse).where(QuizResponse.quiz_session_id == session_id)
            ).all()
            assert len(responses) == 10
            assert {response.question_order for response in responses} == set(
                range(1, 11)
            )
            assert all(response.confidence_level == "medium" for response in responses)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
