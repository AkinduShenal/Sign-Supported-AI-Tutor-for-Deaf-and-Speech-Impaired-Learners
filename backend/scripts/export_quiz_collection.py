"""Export saved Quiz sessions and question evidence without changing the database.

From backend/: python -m scripts.export_quiz_collection
Remote sources require --allow-remote-read and explicit researcher authorization.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.quiz.models import QuizQuestion, QuizQuestionOption, QuizResponse, QuizSession

DEFAULT_EXPORT_ROOT = Path(__file__).resolve().parents[2] / "exports"
SESSION_FIELDS = (
    "source_session_id", "quiz_session_id", "student_id_recorded", "student_code",
    "concept_id", "learning_cycle_id", "assessment_phase", "quiz_attempt_number",
    "display_language", "status", "assessment_complete", "responses_saved",
    "started_at", "completed_at", "created_at",
)
RESPONSE_FIELDS = (
    "source_response_id", "quiz_session_id", "student_id_recorded", "student_code",
    "assessment_phase", "assessment_complete", "question_id", "question_code",
    "question_order", "concept_id", "subconcept_code", "difficulty_level",
    "selected_option_id", "selected_option_code", "selected_answer", "is_correct",
    "response_time_sec", "confidence_level", "misconception_code", "answered_at",
    "saved_at",
)


def _iso(value):
    return value.replace(tzinfo=value.tzinfo or UTC).isoformat() if value is not None else ""


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def export_quiz_data(database: Session, output_dir: Path) -> dict[str, int]:
    sessions = database.scalars(select(QuizSession).order_by(QuizSession.quiz_session_id)).all()
    responses = database.scalars(select(QuizResponse).order_by(
        QuizResponse.quiz_session_id, QuizResponse.question_order, QuizResponse.id
    )).all()
    questions = {row.id: row for row in database.scalars(select(QuizQuestion)).all()}
    options = {row.id: row for row in database.scalars(select(QuizQuestionOption)).all()}
    by_session = {row.quiz_session_id: row for row in sessions}
    counts_by_session: dict[str, int] = {}
    for row in responses:
        counts_by_session[row.quiz_session_id] = counts_by_session.get(row.quiz_session_id, 0) + 1

    session_rows = [{
        "source_session_id": str(row.id), "quiz_session_id": row.quiz_session_id,
        "student_id_recorded": row.student_id,
        "student_code": row.student_id if row.student_id.startswith("STU_") else "",
        "concept_id": row.concept_id, "learning_cycle_id": str(row.learning_cycle_id),
        "assessment_phase": row.assessment_phase,
        "quiz_attempt_number": row.quiz_attempt_number,
        "display_language": row.display_language, "status": row.status,
        "assessment_complete": row.status == "completed",
        "responses_saved": counts_by_session.get(row.quiz_session_id, 0),
        "started_at": _iso(row.started_at), "completed_at": _iso(row.completed_at),
        "created_at": _iso(row.created_at),
    } for row in sessions]

    response_rows = []
    for row in responses:
        session = by_session[row.quiz_session_id]
        question = questions.get(row.question_id)
        option = options.get(row.selected_option_id)
        response_rows.append({
            "source_response_id": str(row.id), "quiz_session_id": row.quiz_session_id,
            "student_id_recorded": session.student_id,
            "student_code": session.student_id if session.student_id.startswith("STU_") else "",
            "assessment_phase": session.assessment_phase,
            "assessment_complete": session.status == "completed",
            "question_id": str(row.question_id),
            "question_code": question.question_code if question else "",
            "question_order": row.question_order,
            "concept_id": question.concept_id if question else session.concept_id,
            "subconcept_code": question.subconcept_code if question else "",
            "difficulty_level": question.difficulty_level if question else "",
            "selected_option_id": str(row.selected_option_id) if row.selected_option_id else "",
            "selected_option_code": option.option_code if option else "",
            "selected_answer": option.option_text_en if option else (row.answer_text or ""),
            "is_correct": row.is_correct, "response_time_sec": row.response_time_sec,
            "confidence_level": row.confidence_level,
            "misconception_code": row.misconception_code or "",
            "answered_at": _iso(row.answered_at), "saved_at": _iso(row.created_at),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "quiz_sessions.csv", SESSION_FIELDS, session_rows)
    _write_csv(output_dir / "quiz_responses.csv", RESPONSE_FIELDS, response_rows)
    counts = {
        "total_sessions": len(sessions), "total_responses": len(responses),
        "completed_sessions": sum(row.status == "completed" for row in sessions),
        "incomplete_sessions": sum(row.status != "completed" for row in sessions),
        "source_quiz_sessions": len(sessions), "source_quiz_responses": len(responses),
    }
    (output_dir / "manifest.json").write_text(json.dumps({
        "exported_at_utc": datetime.now(UTC).isoformat(), "counts": counts,
        "note": "Question-level source evidence; no mastery labels are generated. Codes are caller-supplied, not authenticated.",
    }, indent=2), encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="Override DATABASE_URL from settings")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-remote-read", action="store_true")
    args = parser.parse_args()
    if args.database_url is None:
        from app.core.config import Settings
        try:
            database_url = Settings().database_url
        except ValueError:
            parser.error("could not load database settings")
    else:
        database_url = args.database_url
    try:
        host = make_url(database_url).host
    except (ValueError, SQLAlchemyError):
        parser.error("invalid database URL")
    if host not in (None, "localhost", "127.0.0.1", "::1") and not args.allow_remote_read:
        parser.error("remote database reads require --allow-remote-read")
    output_dir = args.output_dir or DEFAULT_EXPORT_ROOT / datetime.now(UTC).strftime("quiz-%Y%m%dT%H%M%S-%fZ")
    if output_dir.exists():
        parser.error("output directory already exists")
    engine = create_engine(database_url)
    try:
        with Session(engine) as database:
            if engine.dialect.name == "postgresql":
                database.connection().exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            output_dir.mkdir(parents=True, exist_ok=False)
            counts = export_quiz_data(database, output_dir)
    except (SQLAlchemyError, OSError):
        parser.exit(1, "Quiz export failed; preserve any partial output and retry into a new folder.\n")
    finally:
        engine.dispose()
    print(json.dumps({**counts, "output_dir": str(output_dir.resolve())}, indent=2))


if __name__ == "__main__":
    main()
