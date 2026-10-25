"""Create a fresh, isolated SQLite Quiz demo under repository tmp/.

From backend/: python -m scripts.prepare_quiz_dynamic_demo
Fails if the file already exists; never reads DATABASE_URL or .env.
This uses ORM create_all for local bootstrap. The Alembic migration is tested
separately against a simulated legacy schema.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.quiz.models import (
    MisconceptionMapping, QuizQuestion, QuizQuestionOption, QuizSession,
    QuizSessionQuestion, QuizResponse, QuizResult, QuizComparison,
)
from scripts.seed_quiz_dynamic import load_bank as load_dynamic, seed_bank as seed_dynamic
from scripts.seed_quiz_phase2 import load_bank as load_fixed, seed_bank as seed_fixed

DB_PATH = Path(__file__).resolve().parents[2] / "tmp" / "quiz_dynamic_demo.sqlite"


def main() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        raise SystemExit(f"Demo database already exists; refused to overwrite: {DB_PATH}")
    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")
    tables = [model.__table__ for model in (
        MisconceptionMapping, QuizQuestion, QuizQuestionOption, QuizSession,
        QuizSessionQuestion, QuizResponse, QuizResult, QuizComparison,
    )]
    try:
        Base.metadata.create_all(engine, tables=tables)
        with Session(engine) as database, database.begin():
            seed_fixed(database, load_fixed())
            seed_dynamic(database, load_dynamic())
    finally:
        engine.dispose()
    print(f"Created isolated Quiz demo with 10 fixed and 60 draft questions: {DB_PATH}")


if __name__ == "__main__": main()
