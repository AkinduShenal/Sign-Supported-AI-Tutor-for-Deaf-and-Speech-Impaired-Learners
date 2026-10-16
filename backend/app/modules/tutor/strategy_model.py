from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Protocol
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

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


class StrategyPredictor(Protocol):
    """Common inference boundary for the baseline and the trained model."""

    version: str

    def predict(self, request: TutorStrategyRequest) -> StrategyPrediction: ...


ARTIFACT_DIRECTORY = Path(__file__).resolve().parent / "artifacts"
NUMERIC_FEATURES = (
    "quiz_mastery_score", "quiz_hint_rate", "game_mastery_score",
    "game_avg_attempts_per_task", "hint_dependency", "prior_mastery_score",
)
CATEGORICAL_FEATURES = (
    "misconception_code", "quiz_difficulty_level", "recommended_support_level",
    "game_difficulty_level", "engagement_level",
)


class TrainedStrategyModel:
    """Serve the supplied Colab preprocessing + LogisticRegression pipeline."""

    def __init__(self, artifact_directory: Path = ARTIFACT_DIRECTORY) -> None:
        self.metadata = json.loads(
            (artifact_directory / "teaching_strategy_model_metadata.json").read_text(
                encoding="utf-8"
            )
        )
        if (
            self.metadata.get("numeric_features") != list(NUMERIC_FEATURES)
            or self.metadata.get("categorical_features") != list(CATEGORICAL_FEATURES)
            or self.metadata.get("target") != "final_primary_strategy"
            or set(self.metadata.get("classes", [])) != {s.value for s in TutoringStrategy}
        ):
            raise ValueError("Strategy metadata does not match the backend feature/label contract")
        self.version = self.metadata["model_version"]
        # Only load the bundled, trusted artifact. Never accept uploaded pickle paths.
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            self.pipeline = joblib.load(artifact_directory / "teaching_strategy_model.joblib")
        if (
            list(self.pipeline.feature_names_in_) != list(NUMERIC_FEATURES + CATEGORICAL_FEATURES)
            or set(self.pipeline.classes_) != set(self.metadata["classes"])
        ):
            raise ValueError("Strategy pipeline and metadata disagree")

    @staticmethod
    def features(request: TutorStrategyRequest) -> pd.DataFrame:
        quiz, game = request.quiz, request.game
        return pd.DataFrame([{
            "quiz_mastery_score": quiz.quiz_mastery_score,
            "quiz_hint_rate": quiz.quiz_hint_rate,
            "game_mastery_score": game.game_mastery_score,
            "game_avg_attempts_per_task": game.game_avg_attempts_per_task,
            "hint_dependency": game.hint_dependency,
            "prior_mastery_score": request.learner.prior_mastery_score,
            "misconception_code": quiz.misconception_code.value,
            "quiz_difficulty_level": quiz.quiz_difficulty_level.value,
            "recommended_support_level": quiz.recommended_support_level.value,
            "game_difficulty_level": game.game_difficulty_level.value,
            "engagement_level": game.engagement_level.value,
        }], columns=list(NUMERIC_FEATURES + CATEGORICAL_FEATURES))

    def predict(self, request: TutorStrategyRequest) -> StrategyPrediction:
        probabilities = np.asarray(self.pipeline.predict_proba(self.features(request))[0])
        if (
            not np.isfinite(probabilities).all()
            or (probabilities < 0).any()
            or (probabilities > 1).any()
            or not np.isclose(probabilities.sum(), 1)
        ):
            raise ValueError("Strategy model returned invalid probabilities")
        index = int(probabilities.argmax())
        return StrategyPrediction(
            primary_strategy=TutoringStrategy(self.pipeline.classes_[index]),
            # Training target is a single primary strategy, not supporting labels.
            supporting_strategies=(),
            confidence=float(probabilities[index]),
        )


@lru_cache(maxsize=1)
def get_strategy_model() -> TrainedStrategyModel:
    # Missing/incompatible artifacts fail explicitly instead of using rules silently.
    return TrainedStrategyModel()


class RuleBasedStrategyModel:
    """Retained for explicit baseline comparisons; never the serving default."""

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
