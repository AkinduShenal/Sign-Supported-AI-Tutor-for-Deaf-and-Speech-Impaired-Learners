from collections import Counter
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.quiz.diagnostic import (
    MappingEvidence,
    ResponseEvidence,
    calculate_diagnostic,
)
from app.modules.quiz.models import (
    MisconceptionMapping,
    QuizQuestion,
    QuizQuestionOption,
    QuizResponse,
    QuizResult,
    QuizSession,
)
from scripts.seed_quiz_phase2 import load_bank, seed_bank


def sample_responses(wrong_orders=(), error_code="inverse_operation"):
    return [
        ResponseEvidence(
            question_id=f"00000000-0000-4000-8000-{order:012d}",
            question_order=order,
            subconcept_code="two_step_equations" if order <= 4 else f"group_{order}",
            difficulty_level="easy"
            if order <= 4
            else "medium"
            if order <= 8
            else "hard",
            is_correct=order not in wrong_orders,
            response_time_sec=float(order),
            confidence_level="high" if order in wrong_orders else "medium",
            misconception_code=error_code if order in wrong_orders else None,
        )
        for order in range(1, 11)
    ]


def test_diagnostic_calculates_evidence_and_requires_repetition():
    mappings = {"inverse_operation": MappingEvidence(2, False)}
    single = calculate_diagnostic(sample_responses((1,)), mappings)
    assert single.questions_total == single.questions_attempted == 10
    assert single.correct_answers == 9
    assert single.quiz_accuracy == 0.9
    assert single.quiz_avg_response_time_sec == 5.5
    assert single.misconception_code == "none"
    assert single.repeated_error_count == 0
    assert single.weak_subconcept is None
    assert single.diagnostic_evidence["subconcept_performance"][
        "two_step_equations"
    ] == {
        "attempted": 4,
        "correct": 3,
        "incorrect": 1,
        "accuracy": 0.75,
    }

    repeated = calculate_diagnostic(sample_responses((1, 2)), mappings)
    assert repeated.misconception_code == "inverse_operation"
    assert repeated.repeated_error_count == 2
    assert repeated.weak_subconcept == "two_step_equations"
    assert repeated.confidence_pattern == "high_confidence_incorrect"
    assert (
        repeated.diagnostic_evidence["selected_pattern_status"]
        == "possible_unvalidated"
    )
    assert (
        repeated.diagnostic_evidence["difficulty_performance"]["easy"]["accuracy"]
        == 0.5
    )
    assert repeated.diagnostic_evidence["confidence_counts"]["incorrect"]["high"] == 2
    assert 0 <= repeated.quiz_mastery_score <= 1
    assert repeated.mastery_level in {"low", "medium", "high"}
    assert repeated.recommended_support_level in {"low", "medium", "high"}
    assert repeated.quiz_difficulty_level in {"beginner", "intermediate", "advanced"}


def test_mapping_threshold_and_supported_weak_area():
    rows = sample_responses((1, 2, 3))
    values = calculate_diagnostic(rows, {"inverse_operation": MappingEvidence(4, True)})
    assert values.misconception_code == "none"
    assert values.weak_subconcept == "two_step_equations"
    assert values.quiz_avg_response_time_sec == 5.5
    assert calculate_diagnostic(sample_responses(), {}).quiz_mastery_score == 1
    assert (
        calculate_diagnostic(
            sample_responses(tuple(range(1, 11))), {}
        ).quiz_mastery_score
        == 0
    )
    with pytest.raises(ValueError):
        calculate_diagnostic(rows[:9], {})


def test_confidence_states_time_evidence_and_no_time_mastery_penalty():
    rows = sample_responses((4, 5, 6))
    rows[0] = replace(rows[0], confidence_level="high")
    rows[1] = replace(rows[1], confidence_level="low")
    rows[2] = replace(rows[2], confidence_level="medium")
    rows[3] = replace(rows[3], confidence_level="low")
    rows[4] = replace(rows[4], confidence_level="high")
    rows[5] = replace(rows[5], confidence_level="medium")
    result = calculate_diagnostic(
        rows, {"inverse_operation": MappingEvidence(4, False)}
    )
    evidence = result.diagnostic_evidence
    assert evidence["confidence_correctness"] == {
        "high_correct": 1,
        "high_incorrect": 1,
        "medium_correct": 5,
        "medium_incorrect": 1,
        "low_correct": 1,
        "low_incorrect": 1,
    }
    assert [
        item["confidence_correctness_state"]
        for item in evidence["question_evidence"][:6]
    ] == [
        "secure_understanding",
        "fragile_understanding",
        "medium_confidence_correct",
        "knowledge_gap_signal",
        "possible_misconception_signal",
        "medium_confidence_incorrect",
    ]
    assert evidence["question_evidence"][0]["question_id"] == rows[0].question_id
    assert evidence["question_evidence"][0]["response_time_sec"] == 1.0
    assert evidence["question_evidence"][0]["misconception_code"] is None
    assert evidence["question_evidence"][4]["misconception_code"] == "inverse_operation"
    assert evidence["response_time_summary"]["overall_average_sec"] == 5.5
    assert evidence["response_time_summary"]["minimum_response_time_sec"] == 1.0
    assert evidence["response_time_summary"]["maximum_response_time_sec"] == 10.0
    assert (
        evidence["response_time_summary"]["by_subconcept"]["two_step_equations"] == 2.5
    )
    assert result.confidence_pattern == "mixed_inconsistent"
    assert result.misconception_code == "none"
    assert (
        calculate_diagnostic(
            [
                replace(row, response_time_sec=row.response_time_sec * 100)
                for row in rows
            ],
            {"inverse_operation": MappingEvidence(4, False)},
        ).quiz_mastery_score
        == result.quiz_mastery_score
    )


def test_confidence_insight_uses_significant_counts_without_changing_misconception_rule():
    rows = sample_responses((1, 2))
    high_wrong = calculate_diagnostic(
        rows, {"inverse_operation": MappingEvidence(3, False)}
    )
    assert high_wrong.confidence_pattern == "high_confidence_incorrect"
    assert (
        high_wrong.diagnostic_evidence["confidence_insight"]["kind"] == "high_incorrect"
    )
    assert high_wrong.misconception_code == "none"
    assert (
        calculate_diagnostic(
            rows, {"inverse_operation": MappingEvidence(2, False)}
        ).misconception_code
        == "inverse_operation"
    )
    low_right_rows = [
        replace(row, confidence_level="low") if row.question_order in (3, 4) else row
        for row in sample_responses()
    ]
    low_right = calculate_diagnostic(low_right_rows, {})
    assert low_right.confidence_pattern == "low_confidence_correct"
    assert low_right.diagnostic_evidence["confidence_insight"]["kind"] == "low_correct"
    assert (
        calculate_diagnostic(sample_responses(), {}).diagnostic_evidence[
            "confidence_insight"
        ]["kind"]
        == "neutral"
    )


def test_completed_session_analyzes_once_and_incomplete_or_empty_rejected():
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
            QuizResult.__table__,
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
        base = "/api/v1/quiz/sessions"
        questions = client.get("/api/v1/quiz/questions").json()
        assert len(questions) == 10
        assert Counter(q["difficulty_level"] for q in questions) == {
            "easy": 4,
            "medium": 4,
            "hard": 2,
        }
        assert client.post(f"{base}/unknown/analyze").status_code == 404
        empty = client.post(base, json={"student_id": "TEST-EMPTY"}).json()[
            "quiz_session_id"
        ]
        assert client.post(f"{base}/{empty}/analyze").status_code == 409
        assert client.post(f"{base}/{empty}/complete").status_code == 200
        assert client.post(f"{base}/{empty}/analyze").status_code == 409
        assert client.get(f"{base}/{empty}/result").status_code == 404

        session_id = client.post(base, json={"student_id": "TEST-DIAGNOSTIC"}).json()[
            "quiz_session_id"
        ]
        for order, question in enumerate(questions, 1):
            saved = client.post(
                f"{base}/{session_id}/responses",
                json={
                    "question_id": question["id"],
                    "selected_option_id": question["options"][0]["id"],
                    "response_time_sec": float(order),
                    "confidence_level": "medium",
                    "question_order": order,
                },
            )
            assert saved.status_code == 201, saved.text
        assert client.post(f"{base}/{session_id}/analyze").status_code == 409
        assert client.post(f"{base}/{session_id}/complete").status_code == 200
        first = client.post(f"{base}/{session_id}/analyze")
        assert first.status_code == 200, first.text
        result = first.json()
        assert result["confidence_insight"]["kind"] == "neutral"
        assert len(result["diagnostic_evidence"]["question_evidence"]) == 10
        assert (
            result["diagnostic_evidence"]["question_evidence"][0]["question_id"]
            == questions[0]["id"]
        )
        assert (
            result["diagnostic_evidence"]["question_evidence"][0]["response_time_sec"]
            == 1.0
        )
        with factory() as database:
            responses = database.scalars(
                select(QuizResponse).where(QuizResponse.quiz_session_id == session_id)
            ).all()
            assert result["correct_answers"] == sum(
                response.is_correct for response in responses
            )
            assert result["quiz_avg_response_time_sec"] == 5.5
            assert result["quiz_accuracy"] == result["correct_answers"] / 10
            assert (
                result["diagnostic_evidence"]["prototype_rule_version"] == "pp1-pre-v1"
            )
            assert (
                database.scalar(
                    select(func.count())
                    .select_from(QuizResult)
                    .where(QuizResult.quiz_session_id == session_id)
                )
                == 1
            )
        assert client.get(f"{base}/{session_id}/result").json() == result
        assert client.post(f"{base}/{session_id}/analyze").json() == result
        with factory() as database:
            saved = database.scalar(
                select(QuizResult).where(QuizResult.quiz_session_id == session_id)
            )
            old_evidence = dict(saved.diagnostic_evidence)
            for key in (
                "confidence_correctness",
                "question_evidence",
                "confidence_insight",
            ):
                old_evidence.pop(key)
            old_evidence["legacy_marker"] = True
            saved.diagnostic_evidence = old_evidence
            database.commit()
        enriched = client.post(f"{base}/{session_id}/analyze").json()
        assert enriched["diagnostic_evidence"]["legacy_marker"] is True
        assert len(enriched["diagnostic_evidence"]["question_evidence"]) == 10
        assert client.get(f"{base}/{session_id}/result").json() == enriched
        with factory() as database:
            assert (
                database.scalar(
                    select(func.count())
                    .select_from(QuizResult)
                    .where(QuizResult.quiz_session_id == session_id)
                )
                == 1
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
