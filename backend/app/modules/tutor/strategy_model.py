from dataclasses import dataclass

from app.modules.tutor.schemas import (
    MisconceptionCode,
    TutorStrategyRequest,
    TutoringStrategy,
)


@dataclass(frozen=True)
class StrategyPrediction:
    strategy: TutoringStrategy
    confidence: float


class RuleBasedStrategyModel:
    """Temporary baseline that will later be replaced by a trained model."""

    version = "rule-based-v0"

    def predict(self, request: TutorStrategyRequest) -> StrategyPrediction:
        quiz = request.quiz
        game = request.game
        learner = request.learner

        performance_score = (
            learner.prior_mastery_score
            + quiz.quiz_accuracy
            + game.game_success_rate
            + game.game_completion_rate
        ) / 4
        hint_dependency = (quiz.quiz_hint_rate + game.game_hint_rate) / 2

        if (
            performance_score >= 0.8
            and hint_dependency <= 0.25
            and game.game_avg_attempts_per_task <= 1.5
        ):
            return StrategyPrediction(TutoringStrategy.ADVANCED_CHALLENGE, 1.0)

        if quiz.misconception_code == MisconceptionCode.CONCEPT_CONFUSION:
            return StrategyPrediction(TutoringStrategy.CONCEPTUAL_EXPLANATION, 1.0)

        if performance_score < 0.5:
            return StrategyPrediction(TutoringStrategy.STEP_BY_STEP, 1.0)

        if quiz.misconception_code in {
            MisconceptionCode.INVERSE_OPERATION,
            MisconceptionCode.SIGN_ERROR,
            MisconceptionCode.ARITHMETIC_ERROR,
        }:
            return StrategyPrediction(TutoringStrategy.WORKED_EXAMPLE_BASED, 1.0)

        if hint_dependency >= 0.5 or game.game_avg_attempts_per_task >= 2.0:
            return StrategyPrediction(TutoringStrategy.PROGRESSIVE_HINTS, 1.0)

        return StrategyPrediction(TutoringStrategy.WORKED_EXAMPLE_BASED, 1.0)
