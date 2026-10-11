"""Persist a provisional diagnostic using completed, stored pre-tutor answers."""

from collections import Counter

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.quiz import repository
from app.modules.quiz.diagnostic import (
    MappingEvidence,
    ResponseEvidence,
    calculate_diagnostic,
)
from app.modules.quiz.diagnostic_rules import RULES
from app.modules.quiz.models import QuizResult
from app.modules.quiz.schemas import QuizDiagnosticResponse
from app.modules.quiz.service import QuizConflictError, QuizNotFoundError


class QuizDiagnosticService:
    def get_result(
        self, database: Session, quiz_session_id: str
    ) -> QuizDiagnosticResponse:
        session = repository.get_quiz_session(database, quiz_session_id)
        if session is None:
            raise QuizNotFoundError("Quiz session was not found")
        result = repository.get_quiz_result(database, quiz_session_id)
        if result is None:
            raise QuizNotFoundError("Diagnostic result was not found")
        return QuizDiagnosticResponse.model_validate(result)

    def analyze(
        self, database: Session, quiz_session_id: str
    ) -> QuizDiagnosticResponse:
        session = repository.get_quiz_session(
            database, quiz_session_id, for_update=True
        )
        if session is None:
            raise QuizNotFoundError("Quiz session was not found")
        if session.status != "completed" or session.completed_at is None:
            raise QuizConflictError("Quiz session must be completed before analysis")
        if (
            session.assessment_phase != "pre_tutor"
            or session.concept_id != "linear_equations"
        ):
            raise QuizConflictError(
                "Diagnostic analysis currently supports pre-tutor linear equations"
            )

        existing = repository.get_quiz_result(database, quiz_session_id)
        if existing is not None:
            return QuizDiagnosticResponse.model_validate(existing)

        rows = repository.get_diagnostic_rows(database, quiz_session_id)
        if len(rows) != RULES.expected_questions:
            raise QuizConflictError(
                "A completed official assessment requires ten saved responses"
            )
        if [response.question_order for response, _ in rows] != list(
            range(1, RULES.expected_questions + 1)
        ):
            raise QuizConflictError("Official response order is incomplete")
        if (
            len({response.question_id for response, _ in rows})
            != RULES.expected_questions
        ):
            raise QuizConflictError("Official responses must use distinct questions")
        if any(
            question.concept_id != session.concept_id
            or question.assessment_use not in ("pre", "both")
            or question.question_type != "multiple_choice"
            for _, question in rows
        ):
            raise QuizConflictError("Responses do not match the official question set")
        counts = Counter(question.difficulty_level for _, question in rows)
        if (
            tuple(counts[tier] for tier in ("easy", "medium", "hard"))
            != RULES.expected_difficulty_counts
        ):
            raise QuizConflictError(
                "Official question difficulty distribution is incomplete"
            )

        evidence = [
            ResponseEvidence(
                subconcept_code=question.subconcept_code,
                difficulty_level=question.difficulty_level,
                is_correct=response.is_correct,
                response_time_sec=response.response_time_sec,
                confidence_level=response.confidence_level,
                misconception_code=response.misconception_code,
            )
            for response, question in rows
        ]
        mappings = {
            item.misconception_code: MappingEvidence(
                item.minimum_occurrences, item.teacher_validated
            )
            for item in repository.get_misconception_mappings(
                database,
                {
                    item.misconception_code
                    for item in evidence
                    if item.misconception_code
                },
            )
        }
        values = calculate_diagnostic(evidence, mappings)
        result = QuizResult(
            quiz_session_id=session.quiz_session_id,
            student_id=session.student_id,
            concept_id=session.concept_id,
            learning_cycle_id=session.learning_cycle_id,
            assessment_phase=session.assessment_phase,
            weak_concept=session.concept_id,
            quiz_attempt_count=session.quiz_attempt_number,
            completed_at=session.completed_at,
            **vars(values),
        )
        try:
            database.add(result)
            database.commit()
            database.refresh(result)
        except IntegrityError:
            database.rollback()
            existing = repository.get_quiz_result(database, quiz_session_id)
            if existing is not None:
                return QuizDiagnosticResponse.model_validate(existing)
            raise
        except Exception:
            database.rollback()
            raise
        return QuizDiagnosticResponse.model_validate(result)
