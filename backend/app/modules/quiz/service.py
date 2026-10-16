import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.quiz import repository
from app.modules.quiz.diagnostic_rules import RULES
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
        session_id = f"QUIZ-{request.client_session_id or uuid.uuid4()}"
        existing = repository.get_quiz_session(database, session_id)
        if existing is not None:
            return self._matching_session(existing, request)
        session = QuizSession(
            quiz_session_id=session_id,
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
        except IntegrityError:
            database.rollback()
            existing = repository.get_quiz_session(database, session_id)
            if existing is None:
                raise
            return self._matching_session(existing, request)
        except Exception:
            database.rollback()
            raise
        return QuizSessionResponse.model_validate(session, from_attributes=True)

    @staticmethod
    def _matching_session(session: QuizSession, request: QuizSessionCreate) -> QuizSessionResponse:
        if (
            session.student_id != request.student_id
            or session.concept_id != request.concept_id
            or session.assessment_phase != request.assessment_phase.value
            or session.quiz_attempt_number != request.quiz_attempt_number
            or session.display_language != request.display_language.value
            or (request.learning_cycle_id is not None and session.learning_cycle_id != request.learning_cycle_id)
        ):
            raise QuizConflictError("client_session_id belongs to different Quiz session data")
        return QuizSessionResponse.model_validate(session, from_attributes=True)

    @staticmethod
    def _saved_response(database: Session, response: QuizResponse) -> QuizAnswerSavedResponse:
        correct_option = None
        if not response.is_correct:
            correct_options = [
                option
                for option in repository.get_options_for_questions(
                    database, [response.question_id]
                )
                if option.is_correct
            ]
            if len(correct_options) == 1:
                option = correct_options[0]
                correct_option = QuizQuestionOptionResponse(
                    id=option.id,
                    option_code=option.option_code,
                    option_text_en=option.option_text_en,
                    option_text_si=option.option_text_si,
                )
        return QuizAnswerSavedResponse(
            response_id=response.id,
            quiz_session_id=response.quiz_session_id,
            question_id=response.question_id,
            question_order=response.question_order,
            selected_option_id=response.selected_option_id,
            response_time_sec=response.response_time_sec,
            confidence_level=response.confidence_level,
            answered_at=response.answered_at.replace(tzinfo=response.answered_at.tzinfo or timezone.utc),
            is_correct=response.is_correct,
            correct_option=correct_option,
        )

    @staticmethod
    def _matching_response(database: Session, response: QuizResponse, request: QuizAnswerSubmit) -> QuizAnswerSavedResponse:
        requested_time = request.client_action_at
        if requested_time is not None:
            requested_time = requested_time.replace(tzinfo=requested_time.tzinfo or timezone.utc).astimezone(timezone.utc)
        saved_time = response.answered_at.replace(tzinfo=response.answered_at.tzinfo or timezone.utc).astimezone(timezone.utc)
        if (
            response.selected_option_id != request.selected_option_id
            or response.response_time_sec != request.response_time_sec
            or response.confidence_level != request.confidence_level.value
            or response.question_order != request.question_order
            or (requested_time is not None and saved_time != requested_time)
        ):
            raise QuizConflictError("Question already has different saved evidence")
        return QuizService._saved_response(database, response)

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
        existing = repository.get_quiz_response(database, quiz_session_id, request.question_id)
        if existing is not None:
            return self._matching_response(database, existing, request)
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
            **({"answered_at": request.client_action_at} if request.client_action_at is not None else {}),
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
                existing = repository.get_quiz_response(database, quiz_session_id, question.id)
                if existing is not None:
                    return self._matching_response(database, existing, request)
                raise QuizConflictError("This question already has an official response") from error
            raise
        except Exception:
            database.rollback()
            raise
        return self._saved_response(database, response)

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
        if session.status == "completed":
            return QuizSessionResponse.model_validate(session, from_attributes=True)
        if session.status != "in_progress":
            raise QuizConflictError("Quiz session is no longer in progress")
        rows = repository.get_diagnostic_rows(database, quiz_session_id)
        expected = dict(zip(("easy", "medium", "hard"), RULES.expected_difficulty_counts))
        use = "pre" if session.assessment_phase == "pre_tutor" else "post"
        bank = repository.get_questions(database, session.concept_id, use)
        if (
            len(rows) != RULES.expected_questions
            or len(bank) != RULES.expected_questions
            or {response.question_id for response, _ in rows} != {question.id for question in bank}
            or {response.question_order for response, _ in rows} != set(range(1, RULES.expected_questions + 1))
            or Counter(question.difficulty_level for _, question in rows) != expected
            or any(question.concept_id != session.concept_id or question.assessment_use not in (use, "both") for _, question in rows)
        ):
            raise QuizConflictError("Saved Quiz assessment is incomplete or does not match the configured question plan")
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
