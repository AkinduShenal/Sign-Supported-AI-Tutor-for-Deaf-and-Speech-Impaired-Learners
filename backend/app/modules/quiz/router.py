from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.quiz.collection_export import quiz_collection_zip, require_quiz_export_access
from app.modules.quiz.diagnostic_service import QuizDiagnosticService
from app.modules.quiz.dynamic_ml_inference import (
    isolated_demo_enabled, predict_completed_dynamic_session,
)
from app.modules.quiz.schemas import (
    AssessmentPhase,
    QuizAnswerSavedResponse,
    QuizAnswerSubmit,
    QuizDiagnosticResponse,
    QuizDynamicMlPredictionResponse,
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
diagnostic_service = QuizDiagnosticService()
Database = Annotated[Session, Depends(get_db)]


@router.get("/exports/collection", dependencies=[Depends(require_quiz_export_access)])
def download_collection(database: Database) -> Response:
    try:
        content, filename = quiz_collection_zip(database)
    except (SQLAlchemyError, OSError) as error:
        raise HTTPException(503, "Quiz data could not be exported.") from error
    return Response(content=content, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


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
    try:
        return service.create_session(database, request)
    except QuizConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/sessions/{quiz_session_id}", response_model=QuizSessionDetailResponse)
def get_session(quiz_session_id: str, database: Database) -> QuizSessionDetailResponse:
    try:
        return service.get_session(database, quiz_session_id)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/sessions/{quiz_session_id}/questions", response_model=list[QuizQuestionResponse])
def list_session_questions(quiz_session_id: str, database: Database) -> list[QuizQuestionResponse]:
    try:
        return service.list_session_questions(database, quiz_session_id)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except QuizConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


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


@router.post(
    "/sessions/{quiz_session_id}/analyze", response_model=QuizDiagnosticResponse
)
def analyze_session(quiz_session_id: str, database: Database) -> QuizDiagnosticResponse:
    try:
        return diagnostic_service.analyze(database, quiz_session_id)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except QuizConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/sessions/{quiz_session_id}/result", response_model=QuizDiagnosticResponse)
def get_result(quiz_session_id: str, database: Database) -> QuizDiagnosticResponse:
    try:
        return diagnostic_service.get_result(database, quiz_session_id)
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/sessions/{quiz_session_id}/experimental-prediction",
    response_model=QuizDynamicMlPredictionResponse,
)
def get_experimental_prediction(
    quiz_session_id: str, database: Database,
) -> QuizDynamicMlPredictionResponse:
    if not isolated_demo_enabled(database):
        raise HTTPException(status_code=404, detail="Experimental prediction is unavailable")
    try:
        return QuizDynamicMlPredictionResponse.model_validate(
            predict_completed_dynamic_session(database, quiz_session_id)
        )
    except QuizNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
