from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.tutor.schemas import TutorStrategyRequest, TutorStrategyResponse
from app.modules.tutor.service import (
    DuplicateSessionConflictError,
    TutorStrategyService,
)


router = APIRouter(prefix="/api/v1/tutor", tags=["Tutor"])
service = TutorStrategyService()


@router.post("/strategy", response_model=TutorStrategyResponse)
def recommend_strategy(
    request: TutorStrategyRequest,
    database: Annotated[Session, Depends(get_db)],
) -> TutorStrategyResponse:
    try:
        return service.recommend(request, database)
    except DuplicateSessionConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
