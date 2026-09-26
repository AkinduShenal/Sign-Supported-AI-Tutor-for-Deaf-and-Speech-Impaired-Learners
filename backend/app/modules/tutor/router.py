from fastapi import APIRouter

from app.modules.tutor.schemas import TutorStrategyRequest, TutorStrategyResponse
from app.modules.tutor.service import TutorStrategyService


router = APIRouter(prefix="/api/v1/tutor", tags=["Tutor"])
service = TutorStrategyService()


@router.post("/strategy", response_model=TutorStrategyResponse)
def recommend_strategy(request: TutorStrategyRequest) -> TutorStrategyResponse:
    return service.recommend(request)
