"""Read-only verification of the bundled model against saved Quiz/Game results.

Run from backend: python -m scripts.verify_tutor_strategy_model --prior-mastery 0.5
The supplied prior is a verification assumption, not a new learner diagnosis.
No Quiz/Game rows or Tutor predictions are written by this command.
"""

import argparse
from collections import Counter
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.modules.game.models import GameResult
from app.modules.quiz.models import QuizResult
from app.modules.tutor.models import TutorStrategyPrediction
from app.modules.tutor.schemas import LearnerProfile, TutorStrategyFromResultsRequest
from app.modules.tutor.service import DuplicateSessionConflictError, TutorStrategyService
from app.modules.tutor.strategy_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def verify(database: Session, assumed_prior: float | None = None) -> dict:
    if assumed_prior is not None and not 0 <= assumed_prior <= 1:
        raise ValueError("Prior mastery must be between 0 and 1")
    if database.bind.dialect.name == "postgresql":
        database.connection().exec_driver_sql(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        )
        database.connection().exec_driver_sql("SET LOCAL statement_timeout = '15000'")
    service = TutorStrategyService()
    counts = {
        model.__tablename__: database.scalar(select(func.count()).select_from(model))
        for model in (QuizResult, GameResult, TutorStrategyPrediction)
    }
    pairs = database.execute(
        select(QuizResult, GameResult).join(GameResult, (
            (QuizResult.student_id == GameResult.student_id)
            & (QuizResult.concept_id == GameResult.concept_id)
        )).order_by(QuizResult.created_at, GameResult.created_at)
    ).all()
    predictions, skipped = [], Counter()
    for quiz, game in pairs:
        previous = database.scalar(select(TutorStrategyPrediction).where(
            TutorStrategyPrediction.quiz_result_id == quiz.id,
            TutorStrategyPrediction.game_result_id == game.id,
        ).order_by(TutorStrategyPrediction.created_at.desc()))
        profile = previous.input_snapshot.get("learner") if previous else None
        if profile:
            source = "existing_prediction_snapshot"
        elif assumed_prior is not None:
            profile = {"prior_mastery_score": assumed_prior, "preferred_mode": "mixed",
                       "sign_support_required": True}
            source = "explicit_test_assumption"
        else:
            skipped["missing_learner_profile"] += 1
            continue
        reference = TutorStrategyFromResultsRequest(
            student_id=quiz.student_id, concept_id=quiz.concept_id,
            quiz_session_id=quiz.quiz_session_id, game_session_id=game.game_session_id,
            learner=LearnerProfile.model_validate(profile),
        )
        try:
            request = service.request_from_results(reference, database)
        except DuplicateSessionConflictError:
            skipped["different_cycle_or_phase"] += 1
            continue
        prediction = service.model.predict(request)
        # Build the comparison frame directly from ORM columns, independently of
        # the serving feature mapper, then invoke the original Colab pipeline.
        values = {
            name: getattr(quiz if name.startswith("quiz_") or name in (
                "misconception_code", "recommended_support_level"
            ) else game, name)
            for name in NUMERIC_FEATURES + CATEGORICAL_FEATURES
            if name != "prior_mastery_score"
        }
        values["prior_mastery_score"] = reference.learner.prior_mastery_score
        frame = pd.DataFrame([values], columns=list(NUMERIC_FEATURES + CATEGORICAL_FEATURES))
        raw_label = str(service.model.pipeline.predict(frame)[0])
        raw_probability = float(service.model.pipeline.predict_proba(frame).max())
        if prediction.primary_strategy.value != raw_label or abs(
            prediction.confidence - raw_probability
        ) > 1e-12:
            raise AssertionError("Backend prediction disagrees with the supplied pipeline")
        categories = service.model.pipeline.named_steps["preprocessor"].named_transformers_[
            "cat"
        ].named_steps["onehot"].categories_
        unknown = {name: values[name] for name, known in zip(
            CATEGORICAL_FEATURES, categories, strict=True
        ) if values[name] not in known}
        predictions.append({
            "pair_number": len(predictions) + 1,
            "primary_strategy": raw_label,
            "confidence": prediction.confidence,
            "prior_mastery_source": source,
            "prior_mastery_score": reference.learner.prior_mastery_score,
            "cycle_linkage": "matched" if quiz.learning_cycle_id and game.learning_cycle_id
                             else "legacy_missing_cycle",
            "unseen_categories": unknown,
            "matches_original_pipeline": True,
        })
    return {
        "verification_kind": "read_only_live_data_engineering_check",
        "model_version": service.model.version,
        "database_rows": counts,
        "same_student_concept_pairs": len(pairs),
        "verified_pairs": len(predictions),
        "skipped_pairs": dict(skipped),
        "strategy_distribution": dict(Counter(p["primary_strategy"] for p in predictions)),
        "predictions": predictions,
        "writes_performed": False,
        "notes": [
            "Test-assumed priors do not establish a real learner's prior mastery.",
            "This checks integration, not model accuracy against teacher labels.",
            "Unknown categories use the exported OneHotEncoder(handle_unknown='ignore').",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-mastery", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with Session(engine) as database:
        report = verify(database, args.prior_mastery)
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    if not report["verified_pairs"]:
        raise SystemExit("No compatible result pairs were verified")


if __name__ == "__main__":
    main()
