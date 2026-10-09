from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
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


@router.post(
    "/sessions", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED
)
def create_session(
    request: CreateGameSessionRequest,
    database: Annotated[Session, Depends(get_db)],
) -> GameSessionResponse:
    return create_game_session(request, database)


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
