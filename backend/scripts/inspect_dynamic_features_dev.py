"""Print predictors from the isolated development SQLite database, read-only."""

import argparse
import json
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.modules.quiz.dynamic_ml_features import extract_dynamic_features_for_session


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    path = (Path(__file__).resolve().parents[2] / "tmp" / "quiz_dynamic_demo.sqlite").resolve()
    if not path.is_file():
        parser.error(f"Isolated development database is missing: {path}")
    uri = path.as_uri() + "?mode=ro"
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(uri, uri=True))
    try:
        with Session(engine) as database:
            database.connection().exec_driver_sql("PRAGMA query_only=ON")
            result = extract_dynamic_features_for_session(database, args.session_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
