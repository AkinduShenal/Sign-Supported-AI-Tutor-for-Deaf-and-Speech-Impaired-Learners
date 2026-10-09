from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.quiz.schemas import (
    AssessmentPhase,
    QuizAnswerSavedResponse,
    QuizAnswerSubmit,
    QuizQuestionResponse,
    QuizSessionCreate,
    QuizSessionDetailResponse,
    QuizSessionResponse,
)
from app.modules.quiz.service import (
    QuizConflictError,
    QuizInvalidAnswerError,
    QuizNotFoundError,
    QuizService,
)


router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz"])
service = QuizService()
Database = Annotated[Session, Depends(get_db)]


@router.get("/questions", response_model=list[QuizQuestionResponse])
def list_questions(
    database: Database,
    concept_id: Literal["linear_equations"] = "linear_equations",
    assessment_phase: AssessmentPhase = AssessmentPhase.PRE_TUTOR,
    difficulty_level: Literal["easy", "medium", "hard"] | None = None,
) -> list[QuizQuestionResponse]:
    return service.list_questions(
        database, concept_id, assessment_phase, difficulty_level
    )


@router.post(
    "/sessions",
    response_model=QuizSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    request: QuizSessionCreate, database: Database
) -> QuizSessionResponse:
    return service.create_session(database, request)


@router.get("/sessions/{quiz_session_id}", response_model=QuizSessionDetailResponse)
def get_session(quiz_session_id: str, database: Database) -> QuizSessionDetailResponse:
    try:
        return service.get_session(database, quiz_session_id)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/sessions/{quiz_session_id}/responses",
    response_model=QuizAnswerSavedResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_answer(
    quiz_session_id: str,
    request: QuizAnswerSubmit,
    database: Database,
) -> QuizAnswerSavedResponse:
    try:
        return service.submit_answer(database, quiz_session_id, request)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except QuizInvalidAnswerError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except QuizConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/sessions/{quiz_session_id}/complete",
    response_model=QuizSessionResponse,
)
def complete_session(quiz_session_id: str, database: Database) -> QuizSessionResponse:
    try:
        return service.complete_session(database, quiz_session_id)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except QuizConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
