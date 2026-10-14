from app.db.base import Base
from app.modules.game.models import GameResult  # noqa: F401
from app.modules.quiz.models import QuizResult  # noqa: F401
from app.modules.tutor.models import TutorStrategyPrediction  # noqa: F401


def test_shared_learning_tables_are_registered() -> None:
    assert {
        "quiz_results",
        "game_results",
        "tutor_strategy_predictions",
    }.issubset(Base.metadata.tables)


def test_tutor_prediction_links_to_quiz_and_game_results() -> None:
    table = Base.metadata.tables["tutor_strategy_predictions"]
    foreign_key_targets = {key.target_fullname for key in table.foreign_keys}

    assert foreign_key_targets == {
        "quiz_results.id",
        "game_results.id",
    }
    assert "supporting_strategies" in table.c


def test_session_ids_are_unique() -> None:
    quiz_table = Base.metadata.tables["quiz_results"]
    game_table = Base.metadata.tables["game_results"]

    assert quiz_table.c.quiz_session_id.unique is True
    assert game_table.c.game_session_id.unique is True


def test_diagnostic_model_outputs_are_stored() -> None:
    quiz_table = Base.metadata.tables["quiz_results"]
    game_table = Base.metadata.tables["game_results"]

    assert {
        "weak_concept",
        "quiz_mastery_score",
        "recommended_support_level",
    }.issubset(quiz_table.c.keys())
    assert {
        "engagement_level",
        "behavioral_difficulty",
        "hint_dependency",
        "game_mastery_score",
    }.issubset(game_table.c.keys())
