from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.game.collection_export import collection_zip, require_export_access
from app.modules.game.schemas import (
    CreateGameSessionRequest,
    GameplayEventRequest,
    GameplayEventResponse,
    GameResultResponse,
    GameSessionResponse,
    GameTaskAttemptRequest,
    GameTaskAttemptResponse,
    VariantUsageResponse,
)
from app.modules.game.service import (
    GameEvidenceConflictError,
    GameResultNotFoundError,
    GameSessionNotFoundError,
    complete_game_session,
    create_game_session,
    get_game_result,
    get_variant_usage_counts,
    record_game_event,
    save_task_attempt,
)


router = APIRouter(prefix="/api/v1/game", tags=["Game"])


@router.get("/exports/collection", dependencies=[Depends(require_export_access)])
def download_collection(
    database: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        content, filename = collection_zip(database)
    except (SQLAlchemyError, OSError) as error:
        raise HTTPException(503, "Game data could not be exported. Please retry later.") from error
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/sessions", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED
)
def create_session(
    request: CreateGameSessionRequest,
    database: Annotated[Session, Depends(get_db)],
) -> GameSessionResponse:
    try:
        return create_game_session(request, database)
    except GameEvidenceConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/events", response_model=GameplayEventResponse, status_code=status.HTTP_201_CREATED
)
def create_event(
    request: GameplayEventRequest,
    database: Annotated[Session, Depends(get_db)],
) -> GameplayEventResponse:
    try:
        return record_game_event(request, database)
    except GameSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except GameEvidenceConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/task-attempts",
    response_model=GameTaskAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task_attempt(
    request: GameTaskAttemptRequest,
    database: Annotated[Session, Depends(get_db)],
) -> GameTaskAttemptResponse:
    try:
        return save_task_attempt(request, database)
    except GameSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except GameEvidenceConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/sessions/{game_session_id}/complete", response_model=GameSessionResponse)
def complete_session(
    game_session_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> GameSessionResponse:
    try:
        return complete_game_session(game_session_id, database)
    except GameSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except GameEvidenceConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/variant-usage", response_model=VariantUsageResponse)
def read_variant_usage(
    student_id: str,
    concept_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> VariantUsageResponse:
    return VariantUsageResponse(
        usage_counts=get_variant_usage_counts(student_id, concept_id, database)
    )


@router.get("/results/{game_session_id}", response_model=GameResultResponse)
def read_game_result(
    game_session_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> GameResultResponse:
    try:
        return get_game_result(game_session_id, database)
    except GameResultNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
