from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.tutor.content_schemas import (
    MathSignPlanRequest,
    MathSignPlanResponse,
    TutorLessonResponse,
)
from app.modules.tutor.lesson_content import get_lesson
from app.modules.tutor.schemas import TutorStrategyRequest, TutorStrategyResponse
from app.modules.tutor.service import (
    DuplicateSessionConflictError,
    TutorStrategyService,
)
from app.modules.tutor.sign_planner import MathSignPlanner
from app.modules.tutor.adaptive_lesson import (
    AdaptiveLesson,
    Level,
    PracticeCheckRequest,
    PracticeCheckResponse,
    check_practice,
    plan_lesson,
    preview_lesson,
)


router = APIRouter(prefix="/api/v1/tutor", tags=["Tutor"])
service = TutorStrategyService()
sign_planner = MathSignPlanner()


@router.get("/grade10/{level}", response_model=AdaptiveLesson)
def preview_grade10(level: Level) -> AdaptiveLesson:
    return preview_lesson(level)


@router.post("/adaptive-lesson", response_model=AdaptiveLesson)
def adaptive_grade10(request: TutorStrategyRequest) -> AdaptiveLesson:
    """Read-only planning; existing /strategy remains the persistence endpoint."""
    try:
        return plan_lesson(request, service.model)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/practice/check", response_model=PracticeCheckResponse)
def check_grade10_practice(request: PracticeCheckRequest) -> PracticeCheckResponse:
    try:
        return check_practice(request)
    except KeyError as error:
        raise HTTPException(
            status_code=404, detail="Unknown practice question"
        ) from error


@router.get("/lessons/{concept_id}", response_model=TutorLessonResponse)
def read_lesson(concept_id: str) -> TutorLessonResponse:
    lesson = get_lesson(concept_id)
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson '{concept_id}' was not found",
        )
    return lesson


@router.post("/sign-plan", response_model=MathSignPlanResponse)
def create_sign_plan(request: MathSignPlanRequest) -> MathSignPlanResponse:
    plan = sign_planner.plan(
        instruction=request.instruction,
        expression=request.expression,
        context_actions=tuple(request.context_actions),
    )
    return MathSignPlanResponse(
        sign_actions=list(plan.sign_actions),
        playable_actions=list(plan.playable_actions),
        prototype_actions=list(plan.prototype_actions),
        unavailable_actions=list(plan.unavailable_actions),
        unsupported_actions=list(plan.unsupported_actions),
        unsupported_tokens=list(plan.unsupported_tokens),
        is_fully_supported=plan.is_fully_supported,
    )


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
