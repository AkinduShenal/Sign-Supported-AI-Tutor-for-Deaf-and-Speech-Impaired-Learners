from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.tutor.content_schemas import TutorLessonResponse
from app.modules.tutor.lesson_content import get_lesson
from app.modules.tutor.schemas import TutorStrategyRequest, TutorStrategyResponse
from app.modules.tutor.service import (
    DuplicateSessionConflictError,
    TutorStrategyService,
)


router = APIRouter(prefix="/api/v1/tutor", tags=["Tutor"])
service = TutorStrategyService()


@router.get("/lessons/{concept_id}", response_model=TutorLessonResponse)
def read_lesson(concept_id: str) -> TutorLessonResponse:
    lesson = get_lesson(concept_id)
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson '{concept_id}' was not found",
        )
    return lesson


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
