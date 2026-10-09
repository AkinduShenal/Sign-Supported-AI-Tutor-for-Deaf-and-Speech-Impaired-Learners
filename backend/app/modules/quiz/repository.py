import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.quiz.models import (
    QuizQuestion,
    QuizQuestionOption,
    QuizResponse,
    QuizSession,
)


def get_questions(
    database: Session,
    concept_id: str,
    assessment_use: str,
    difficulty_level: str | None = None,
) -> list[QuizQuestion]:
    query = select(QuizQuestion).where(
        QuizQuestion.concept_id == concept_id,
        QuizQuestion.assessment_use.in_((assessment_use, "both")),
        QuizQuestion.question_type == "multiple_choice",
        QuizQuestion.is_active.is_(True),
    )
    if difficulty_level is not None:
        query = query.where(QuizQuestion.difficulty_level == difficulty_level)
    return list(database.scalars(query.order_by(QuizQuestion.question_code)))


def get_options_for_questions(
    database: Session,
    question_ids: list[uuid.UUID],
) -> list[QuizQuestionOption]:
    if not question_ids:
        return []
    return list(
        database.scalars(
            select(QuizQuestionOption)
            .where(QuizQuestionOption.question_id.in_(question_ids))
            .order_by(QuizQuestionOption.question_id, QuizQuestionOption.option_code)
        )
    )


def get_question_by_id(
    database: Session, question_id: uuid.UUID
) -> QuizQuestion | None:
    return database.get(QuizQuestion, question_id)


def get_option_by_id(
    database: Session, option_id: uuid.UUID
) -> QuizQuestionOption | None:
    return database.get(QuizQuestionOption, option_id)


def create_quiz_session(database: Session, session: QuizSession) -> QuizSession:
    database.add(session)
    database.flush()
    return session


def get_quiz_session(
    database: Session,
    quiz_session_id: str,
    *,
    for_update: bool = False,
) -> QuizSession | None:
    query = select(QuizSession).where(QuizSession.quiz_session_id == quiz_session_id)
    if for_update:
        query = query.with_for_update()
    return database.scalar(query)


def get_quiz_response(
    database: Session,
    quiz_session_id: str,
    question_id: uuid.UUID,
) -> QuizResponse | None:
    return database.scalar(
        select(QuizResponse).where(
            QuizResponse.quiz_session_id == quiz_session_id,
            QuizResponse.question_id == question_id,
        )
    )


def save_quiz_response(database: Session, response: QuizResponse) -> QuizResponse:
    database.add(response)
    database.flush()
    return response


def get_session_responses(
    database: Session, quiz_session_id: str
) -> list[QuizResponse]:
    return list(
        database.scalars(
            select(QuizResponse)
            .where(QuizResponse.quiz_session_id == quiz_session_id)
            .order_by(QuizResponse.question_order)
        )
    )


def complete_quiz_session(
    database: Session,
    session: QuizSession,
    completed_at: datetime,
) -> QuizSession:
    session.status = "completed"
    session.completed_at = completed_at
    database.flush()
    return session
