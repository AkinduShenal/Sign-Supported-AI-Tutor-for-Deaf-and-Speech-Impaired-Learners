from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.game.models import GameResult as GameResultModel
from app.modules.quiz.models import QuizResult as QuizResultModel
from app.modules.tutor.models import TutorStrategyPrediction
from app.modules.tutor.schemas import (
    GameResult, QuizResult, TutorStrategyFromResultsRequest,
    TutorStrategyRequest, TutorStrategyResponse,
)
from app.modules.tutor.strategy_model import StrategyPredictor, get_strategy_model


class DuplicateSessionConflictError(ValueError):
    pass


class MissingDiagnosticResultsError(ValueError):
    pass


class TutorStrategyService:
    def __init__(self, model: StrategyPredictor | None = None) -> None:
        self.model = model if model is not None else get_strategy_model()

    def request_from_results(
        self, request: TutorStrategyFromResultsRequest, database: Session,
    ) -> TutorStrategyRequest:
        """Read diagnostic evidence; Tutor owns predictions, never Quiz/Game rows."""
        quiz = database.scalar(select(QuizResultModel).where(
            QuizResultModel.quiz_session_id == request.quiz_session_id
        ))
        game = database.scalar(select(GameResultModel).where(
            GameResultModel.game_session_id == request.game_session_id
        ))
        if quiz is None or game is None:
            raise MissingDiagnosticResultsError(
                "Completed Quiz and Game results are required; finish both assessments first"
            )
        if any(
            result.student_id != request.student_id or result.concept_id != request.concept_id
            for result in (quiz, game)
        ):
            raise DuplicateSessionConflictError("Quiz/Game results belong to a different student or concept")
        if (
            quiz.learning_cycle_id is not None and game.learning_cycle_id is not None
            and quiz.learning_cycle_id != game.learning_cycle_id
        ) or (
            quiz.assessment_phase is not None and game.assessment_phase is not None
            and quiz.assessment_phase != game.assessment_phase
        ):
            raise DuplicateSessionConflictError("Quiz/Game results belong to different learning cycles or phases")

        def diagnostic(result, schema):
            values = {name: getattr(result, name) for name in schema.model_fields}
            # SQLite drops timezone info; represent the persisted instant consistently.
            completed = values["completed_at"]
            if completed is not None and completed.tzinfo is None:
                values["completed_at"] = completed.replace(tzinfo=UTC)
            return schema.model_validate(values)

        return TutorStrategyRequest(
            student_id=request.student_id, concept_id=request.concept_id,
            quiz=diagnostic(quiz, QuizResult), game=diagnostic(game, GameResult),
            learner=request.learner,
        )

    def recommend_from_results(
        self, request: TutorStrategyFromResultsRequest, database: Session,
    ) -> TutorStrategyResponse:
        return self.recommend(self.request_from_results(request, database), database)

    def recommend(
        self,
        request: TutorStrategyRequest,
        database: Session,
    ) -> TutorStrategyResponse:
        try:
            stored_request = self.request_from_results(TutorStrategyFromResultsRequest(
                student_id=request.student_id, concept_id=request.concept_id,
                quiz_session_id=request.quiz.quiz_session_id,
                game_session_id=request.game.game_session_id, learner=request.learner,
            ), database)
            input_snapshot = stored_request.model_dump(mode="json")
            quiz_result = database.scalar(
                select(QuizResultModel).where(
                    QuizResultModel.quiz_session_id == request.quiz.quiz_session_id
                )
            )
            game_result = database.scalar(
                select(GameResultModel).where(
                    GameResultModel.game_session_id == request.game.game_session_id
                )
            )

            if quiz_result is not None and not self._quiz_result_matches(
                quiz_result, request
            ):
                raise DuplicateSessionConflictError(
                    "quiz_session_id already belongs to a different quiz result"
                )
            if game_result is not None and not self._game_result_matches(
                game_result, request
            ):
                raise DuplicateSessionConflictError(
                    "game_session_id already belongs to a different game result"
                )

            existing_prediction = database.scalar(
                select(TutorStrategyPrediction).where(
                    TutorStrategyPrediction.quiz_result_id == quiz_result.id,
                    TutorStrategyPrediction.game_result_id == game_result.id,
                    TutorStrategyPrediction.model_version == self.model.version,
                ).order_by(TutorStrategyPrediction.created_at.desc())
            )
            if existing_prediction is not None:
                if existing_prediction.input_snapshot != input_snapshot:
                    raise DuplicateSessionConflictError(
                        "The supplied session IDs already belong to a different payload"
                    )
                return self._to_response(existing_prediction)

            strategy_prediction = self.model.predict(stored_request)
            prediction_record = TutorStrategyPrediction(
                student_id=request.student_id,
                concept_id=request.concept_id,
                quiz_result_id=quiz_result.id,
                game_result_id=game_result.id,
                primary_strategy=strategy_prediction.primary_strategy.value,
                supporting_strategies=[
                    strategy.value
                    for strategy in strategy_prediction.supporting_strategies
                ],
                confidence=strategy_prediction.confidence,
                model_version=self.model.version,
                preferred_mode=request.learner.preferred_mode.value,
                sign_support_required=request.learner.sign_support_required,
                input_snapshot=input_snapshot,
            )
            database.add(prediction_record)
            database.commit()
            database.refresh(prediction_record)

            return self._to_response(prediction_record)
        except Exception:
            database.rollback()
            raise

    @staticmethod
    def _quiz_result_matches(
        result: QuizResultModel,
        request: TutorStrategyRequest,
    ) -> bool:
        quiz = request.quiz
        return (
            result.student_id == request.student_id
            and result.concept_id == request.concept_id
            and result.weak_concept == quiz.weak_concept
            and result.quiz_mastery_score == quiz.quiz_mastery_score
            and result.recommended_support_level == quiz.recommended_support_level.value
            and result.questions_total == quiz.questions_total
            and result.questions_attempted == quiz.questions_attempted
            and result.correct_answers == quiz.correct_answers
            and result.quiz_accuracy == quiz.quiz_accuracy
            and result.quiz_avg_response_time_sec == quiz.quiz_avg_response_time_sec
            and result.quiz_hint_rate == quiz.quiz_hint_rate
            and result.misconception_code == quiz.misconception_code.value
            and result.quiz_difficulty_level == quiz.quiz_difficulty_level.value
            and result.quiz_attempt_count == quiz.quiz_attempt_count
        )

    @staticmethod
    def _game_result_matches(
        result: GameResultModel,
        request: TutorStrategyRequest,
    ) -> bool:
        game = request.game
        return (
            result.student_id == request.student_id
            and result.concept_id == request.concept_id
            and result.engagement_level == game.engagement_level.value
            and result.behavioral_difficulty == game.behavioral_difficulty.value
            and result.hint_dependency == game.hint_dependency
            and result.game_mastery_score == game.game_mastery_score
            and result.tasks_total == game.tasks_total
            and result.tasks_attempted == game.tasks_attempted
            and result.tasks_completed == game.tasks_completed
            and result.successful_tasks == game.successful_tasks
            and result.game_success_rate == game.game_success_rate
            and result.game_completion_rate == game.game_completion_rate
            and result.game_avg_attempts_per_task == game.game_avg_attempts_per_task
            and result.game_hint_rate == game.game_hint_rate
            and result.game_difficulty_level == game.game_difficulty_level.value
            and result.game_active_time_sec == game.game_active_time_sec
        )

    @staticmethod
    def _to_response(
        prediction: TutorStrategyPrediction,
    ) -> TutorStrategyResponse:
        return TutorStrategyResponse(
            prediction_id=prediction.id,
            quiz_result_id=prediction.quiz_result_id,
            game_result_id=prediction.game_result_id,
            student_id=prediction.student_id,
            concept_id=prediction.concept_id,
            primary_strategy=prediction.primary_strategy,
            supporting_strategies=prediction.supporting_strategies,
            confidence=prediction.confidence,
            preferred_mode=prediction.preferred_mode,
            sign_support_required=prediction.sign_support_required,
            model_version=prediction.model_version,
        )
