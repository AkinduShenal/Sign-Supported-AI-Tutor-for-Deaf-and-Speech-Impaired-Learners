"""Seed a fresh disposable SQLite file for the real Tutor browser smoke test."""

from datetime import UTC, datetime
from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.modules.game.models import GameResult, GameSession
from app.modules.quiz.models import QuizResult
from app.modules.tutor.models import TutorStrategyPrediction


def main():
    if engine.dialect.name != "sqlite" or not engine.url.database or engine.url.database == ":memory:":
        raise ValueError("Browser fixtures require a new disposable SQLite file")
    if Path(engine.url.database).exists():
        raise FileExistsError("Refusing to change an existing database")
    Base.metadata.create_all(engine, tables=[
        GameSession.__table__, QuizResult.__table__, GameResult.__table__,
        TutorStrategyPrediction.__table__,
    ])
    cycle = uuid.UUID("00000000-0000-4000-8000-000000000999")
    common = {"student_id": "STU_999", "concept_id": "linear_equations",
              "learning_cycle_id": cycle, "assessment_phase": "pre_tutor"}
    completed = datetime(2026, 10, 16, 10, 0, tzinfo=UTC)
    with Session(engine) as database:
        database.add(GameSession(
            **common, game_session_id="GAME-tutor-ui", status="completed", completed_at=completed,
        ))
        database.flush()
        database.add(QuizResult(
            **common, quiz_session_id="QUIZ-tutor-ui", weak_concept="linear_equation_balancing",
            quiz_mastery_score=.35, recommended_support_level="high",
            questions_total=10, questions_attempted=10, correct_answers=4,
            quiz_accuracy=.4, quiz_avg_response_time_sec=42.5, quiz_hint_rate=.7,
            misconception_code="inverse_operation", quiz_difficulty_level="beginner",
            quiz_attempt_count=1, completed_at=completed,
        ))
        database.add(GameResult(
            **common, game_session_id="GAME-tutor-ui", engagement_level="medium",
            behavioral_difficulty="high", hint_dependency=.7, game_mastery_score=.4,
            tasks_total=6, tasks_attempted=6, tasks_completed=6, successful_tasks=3,
            game_success_rate=.5, game_completion_rate=1., game_avg_attempts_per_task=2.5,
            game_hint_rate=.6, game_difficulty_level="beginner", game_active_time_sec=420,
            completed_at=completed,
        ))
        database.commit()


if __name__ == "__main__":
    main()
