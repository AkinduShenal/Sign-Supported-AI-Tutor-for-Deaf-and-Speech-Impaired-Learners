"""Resolve pre-tutor evidence for exactly one learner, concept and cycle."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.game.models import GameResult
from app.modules.quiz.models import QuizResult
from app.modules.tutor.schemas import (
    AutomaticTutorRequest, LearnerProfile, TutorLearningStatus,
    TutorStrategyFromResultsRequest, TutorStrategyRequest,
)
from app.modules.tutor.service import MissingDiagnosticResultsError, TutorStrategyService


def cycle_results(request: AutomaticTutorRequest, database: Session):
    results = []
    for model in (QuizResult, GameResult):
        results.append(database.scalar(select(model).where(
            model.student_id == request.student_id,
            model.concept_id == request.concept_id,
            model.learning_cycle_id == request.learning_cycle_id,
            model.assessment_phase == "pre_tutor",
            model.completed_at.is_not(None),
        ).order_by(model.completed_at.desc(), model.created_at.desc(), model.id.desc()).limit(1)))
    return results


def learning_status(request: AutomaticTutorRequest, database: Session) -> TutorLearningStatus:
    quiz, game = cycle_results(request, database)
    return TutorLearningStatus(
        quiz_complete=quiz is not None, game_complete=game is not None,
        ready=quiz is not None and game is not None,
    )


def automatic_diagnostics(
    request: AutomaticTutorRequest, database: Session, service: TutorStrategyService,
) -> TutorStrategyRequest:
    quiz, game = cycle_results(request, database)
    if quiz is None or game is None:
        raise MissingDiagnosticResultsError("Complete the Quiz and Game for this learning cycle first")
    return service.request_from_results(TutorStrategyFromResultsRequest(
        student_id=request.student_id, concept_id=request.concept_id,
        quiz_session_id=quiz.quiz_session_id, game_session_id=game.game_session_id,
        learner=LearnerProfile(
            # Training definition confirmed by the model's author: the Quiz
            # before tutoring provides prior mastery, not an arbitrary constant.
            prior_mastery_score=quiz.quiz_mastery_score,
            preferred_mode="visual", sign_support_required=True,
        ),
    ), database)
