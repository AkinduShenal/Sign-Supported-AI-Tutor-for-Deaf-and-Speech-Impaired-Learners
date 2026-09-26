from app.modules.tutor.schemas import TutorStrategyRequest, TutorStrategyResponse
from app.modules.tutor.strategy_model import RuleBasedStrategyModel


class TutorStrategyService:
    def __init__(self, model: RuleBasedStrategyModel | None = None) -> None:
        self.model = model or RuleBasedStrategyModel()

    def recommend(self, request: TutorStrategyRequest) -> TutorStrategyResponse:
        prediction = self.model.predict(request)

        return TutorStrategyResponse(
            student_id=request.student_id,
            concept_id=request.concept_id,
            recommended_strategy=prediction.strategy,
            confidence=prediction.confidence,
            preferred_mode=request.learner.preferred_mode,
            sign_support_required=request.learner.sign_support_required,
            model_version=self.model.version,
        )
