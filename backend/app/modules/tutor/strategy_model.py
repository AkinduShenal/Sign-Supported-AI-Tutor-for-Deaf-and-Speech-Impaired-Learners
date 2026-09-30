from dataclasses import dataclass

from app.modules.tutor.schemas import (
    BehavioralDifficulty,
    EngagementLevel,
    MisconceptionCode,
    SupportLevel,
    TutorStrategyRequest,
    TutoringStrategy,
)


@dataclass(frozen=True)
class StrategyPrediction:
    primary_strategy: TutoringStrategy
    supporting_strategies: tuple[TutoringStrategy, ...]
    confidence: float


class RuleBasedStrategyModel:
    """Temporary baseline that will later be replaced by a trained model."""

    version = "rule-based-v2"

    def predict(self, request: TutorStrategyRequest) -> StrategyPrediction:
        quiz = request.quiz
        game = request.game
        learner = request.learner

        performance_score = (
            learner.prior_mastery_score
            + quiz.quiz_mastery_score
            + game.game_mastery_score
        ) / 3
        hint_dependency = (quiz.quiz_hint_rate + game.hint_dependency) / 2

        if (
            performance_score >= 0.8
            and hint_dependency <= 0.25
            and quiz.recommended_support_level == SupportLevel.LOW
            and game.behavioral_difficulty == BehavioralDifficulty.LOW
            and game.game_avg_attempts_per_task <= 1.5
        ):
            primary_strategy = TutoringStrategy.ADVANCED_CHALLENGE
        elif quiz.misconception_code == MisconceptionCode.CONCEPT_CONFUSION:
            primary_strategy = TutoringStrategy.CONCEPTUAL_EXPLANATION
        elif (
            performance_score < 0.5
            or quiz.recommended_support_level == SupportLevel.HIGH
            or game.behavioral_difficulty == BehavioralDifficulty.HIGH
        ):
            primary_strategy = TutoringStrategy.STEP_BY_STEP
        elif quiz.misconception_code in {
            MisconceptionCode.INVERSE_OPERATION,
            MisconceptionCode.SIGN_ERROR,
            MisconceptionCode.ARITHMETIC_ERROR,
        }:
            primary_strategy = TutoringStrategy.WORKED_EXAMPLE_BASED
        elif hint_dependency >= 0.5 or game.game_avg_attempts_per_task >= 2.0:
            primary_strategy = TutoringStrategy.PROGRESSIVE_HINTS
        else:
            primary_strategy = TutoringStrategy.WORKED_EXAMPLE_BASED

        supporting_candidates: list[TutoringStrategy] = []

        if quiz.misconception_code in {
            MisconceptionCode.INVERSE_OPERATION,
            MisconceptionCode.SIGN_ERROR,
            MisconceptionCode.ARITHMETIC_ERROR,
        }:
            supporting_candidates.append(TutoringStrategy.WORKED_EXAMPLE_BASED)
        if (
            performance_score < 0.65
            or quiz.recommended_support_level == SupportLevel.HIGH
            or game.behavioral_difficulty == BehavioralDifficulty.HIGH
        ):
            supporting_candidates.append(TutoringStrategy.STEP_BY_STEP)
        if hint_dependency >= 0.5 or game.game_avg_attempts_per_task >= 2.0:
            supporting_candidates.append(TutoringStrategy.PROGRESSIVE_HINTS)
        if game.engagement_level == EngagementLevel.LOW:
            supporting_candidates.append(TutoringStrategy.WORKED_EXAMPLE_BASED)

        supporting_strategies = tuple(
            strategy
            for strategy in dict.fromkeys(supporting_candidates)
            if strategy != primary_strategy
        )[:2]

        return StrategyPrediction(
            primary_strategy=primary_strategy,
            supporting_strategies=supporting_strategies,
            confidence=1.0,
        )
