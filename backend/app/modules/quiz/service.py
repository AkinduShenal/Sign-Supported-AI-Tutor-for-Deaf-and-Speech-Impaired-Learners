import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.quiz import repository
from app.modules.quiz.models import QuizResponse, QuizSession
from app.modules.quiz.schemas import (
    AssessmentPhase,
    QuizAnswerSavedResponse,
    QuizAnswerSubmit,
    QuizQuestionOptionResponse,
    QuizQuestionResponse,
    QuizSessionCreate,
    QuizSessionDetailResponse,
    QuizSessionResponse,
)


class QuizNotFoundError(ValueError):
    pass


class QuizConflictError(ValueError):
    pass


class QuizInvalidAnswerError(ValueError):
    pass


class QuizService:
    def list_questions(
        self,
        database: Session,
        concept_id: str,
        assessment_phase: AssessmentPhase,
        difficulty_level: str | None = None,
    ) -> list[QuizQuestionResponse]:
        assessment_use = (
            "pre" if assessment_phase == AssessmentPhase.PRE_TUTOR else "post"
        )
        questions = repository.get_questions(
            database,
            concept_id,
            assessment_use,
            difficulty_level,
        )
        options_by_question = defaultdict(list)
        for option in repository.get_options_for_questions(
            database,
            [question.id for question in questions],
        ):
            options_by_question[option.question_id].append(
                QuizQuestionOptionResponse(
                    id=option.id,
                    option_code=option.option_code,
                    option_text_en=option.option_text_en,
                    option_text_si=option.option_text_si,
                )
            )
        return [
            QuizQuestionResponse(
                id=question.id,
                question_code=question.question_code,
                concept_id=question.concept_id,
                subconcept_code=question.subconcept_code,
                question_type=question.question_type,
                question_text_en=question.question_text_en,
                question_text_si=question.question_text_si,
                difficulty_level=question.difficulty_level,
                options=options_by_question[question.id],
            )
            for question in questions
        ]

    def create_session(
        self,
        database: Session,
        request: QuizSessionCreate,
    ) -> QuizSessionResponse:
        session = QuizSession(
            quiz_session_id=f"QUIZ-{uuid.uuid4()}",
            student_id=request.student_id,
            concept_id=request.concept_id,
            learning_cycle_id=request.learning_cycle_id or uuid.uuid4(),
            assessment_phase=request.assessment_phase.value,
            quiz_attempt_number=request.quiz_attempt_number,
            display_language=request.display_language.value,
            status="in_progress",
        )
        try:
            repository.create_quiz_session(database, session)
            database.commit()
            database.refresh(session)
        except Exception:
            database.rollback()
            raise
        return QuizSessionResponse.model_validate(session, from_attributes=True)

    def submit_answer(
        self,
        database: Session,
        quiz_session_id: str,
        request: QuizAnswerSubmit,
    ) -> QuizAnswerSavedResponse:
        session = repository.get_quiz_session(
            database, quiz_session_id, for_update=True
        )
        if session is None:
            raise QuizNotFoundError("Quiz session was not found")
        if session.status != "in_progress":
            raise QuizConflictError("Quiz session is no longer in progress")
        question = repository.get_question_by_id(database, request.question_id)
        if question is None:
            raise QuizNotFoundError("Quiz question was not found")
        expected_use = "pre" if session.assessment_phase == "pre_tutor" else "post"
        if (
            question.concept_id != session.concept_id
            or question.assessment_use not in (expected_use, "both")
            or question.question_type != "multiple_choice"
            or not question.is_active
        ):
            raise QuizInvalidAnswerError("Question is not available for this session")
        option = repository.get_option_by_id(database, request.selected_option_id)
        if option is None or option.question_id != question.id:
            raise QuizInvalidAnswerError(
                "Selected option does not belong to the question"
            )
        if (
            repository.get_quiz_response(database, quiz_session_id, question.id)
            is not None
        ):
            raise QuizConflictError("This question already has an official response")

        response = QuizResponse(
            quiz_session_id=quiz_session_id,
            question_id=question.id,
            selected_option_id=option.id,
            answer_text=None,
            is_correct=option.is_correct,
            response_time_sec=request.response_time_sec,
            confidence_level=request.confidence_level.value,
            misconception_code=option.misconception_code,
            question_order=request.question_order,
        )
        try:
            repository.save_quiz_response(database, response)
            database.commit()
        except IntegrityError as error:
            database.rollback()
            constraint_name = getattr(
                getattr(error.orig, "diag", None), "constraint_name", None
            )
            sqlite_duplicate = (
                "UNIQUE constraint failed: quiz_responses.quiz_session_id, "
                "quiz_responses.question_id"
            ) in str(error.orig)
            if (
                constraint_name == "quiz_responses_quiz_session_id_question_id_key"
                or sqlite_duplicate
            ):
                raise QuizConflictError(
                    "This question already has an official response"
                ) from error
            raise
        except Exception:
            database.rollback()
            raise
        return QuizAnswerSavedResponse(
            response_id=response.id,
            quiz_session_id=quiz_session_id,
            question_id=question.id,
            question_order=response.question_order,
        )

    def get_session(
        self, database: Session, quiz_session_id: str
    ) -> QuizSessionDetailResponse:
        session = repository.get_quiz_session(database, quiz_session_id)
        if session is None:
            raise QuizNotFoundError("Quiz session was not found")
        return QuizSessionDetailResponse(
            **QuizSessionResponse.model_validate(
                session, from_attributes=True
            ).model_dump(),
            responses_saved=len(
                repository.get_session_responses(database, quiz_session_id)
            ),
        )

    def complete_session(
        self,
        database: Session,
        quiz_session_id: str,
    ) -> QuizSessionResponse:
        session = repository.get_quiz_session(
            database, quiz_session_id, for_update=True
        )
        if session is None:
            raise QuizNotFoundError("Quiz session was not found")
        if session.status != "in_progress":
            raise QuizConflictError("Quiz session is no longer in progress")
        try:
            repository.complete_quiz_session(
                database, session, datetime.now(timezone.utc)
            )
            database.commit()
            database.refresh(session)
        except Exception:
            database.rollback()
            raise
        return QuizSessionResponse.model_validate(session, from_attributes=True)
