"""Export saved Game evidence as reconciliable, deidentified CSV files.

Run from backend/ to use DATABASE_URL from the application's .env/settings:
    python -m scripts.export_game_collection

Optional explicit overrides (local PostgreSQL):
    python -m scripts.export_game_collection --database-url postgresql+psycopg://... \
        --output-dir ./exports/game-visit

This script only reads the database. Remote hosts require --allow-remote-read.
No label value is generated from Game heuristics.
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

from app.modules.game.models import GameResult, GameSession, GameTaskAttempt, GameplayEvent
from app.modules.game.service import is_assessment_complete


DEFAULT_EXPORT_ROOT = Path(__file__).resolve().parents[2] / "exports"


SESSION_FIELDS = (
    "game_session_id", "student_id_recorded", "student_code", "concept_id",
    "learning_cycle_id", "assessment_phase", "game_type", "status",
    "started_at", "completed_at", "recording_protocol", "saved_assessment_complete",
    "source_session_uuid",
)
ANSWER_FIELDS = (
    "source_event_id", "client_event_id", "game_session_id", "student_id_recorded",
    "student_code", "learning_cycle_id", "assessment_phase", "game_type",
    "concept_id", "activity_id", "variant_id", "task_id", "difficulty_level",
    "step_index", "attempt_number", "answer_type", "question_prompt",
    "expected_response", "submitted_answer", "is_correct", "hints_before_attempt",
    "first_attempt_correct", "event_timestamp", "content_version",
)
EVENT_FIELDS = (
    "source_event_id", "game_session_id", "student_id_recorded", "event_type",
    "task_id", "client_event_id", "step_index", "attempt_number", "event_timestamp",
)
ANALYTICS_FIELDS = (
    "source_result_id", "game_session_id", "student_id_recorded", "student_code",
    "concept_id", "learning_cycle_id", "assessment_phase", "tasks_total",
    "tasks_attempted", "tasks_completed", "successful_tasks", "game_success_rate",
    "game_completion_rate", "game_avg_attempts_per_task", "game_hint_rate",
    "wrong_attempt_count", "retry_count", "total_hint_count", "skipped_step_count",
    "game_active_time_sec", "game_difficulty_level", "game_mastery_level",
    "model_version", "completed_at",
)
LABEL_FIELDS = (
    "game_session_id", "student_code", "concept_id", "assessment_phase",
    "independent_target", "independent_label", "label_source", "source_reference",
    "assessed_at", "rubric_version",
)


def _iso(value):
    return value.isoformat() if value is not None else ""


def _code(value: str) -> str:
    return value if value.startswith("STU_") else ""


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_game_data(database: Session, output_dir: Path) -> dict[str, int]:
    """Write a snapshot from one read transaction; return auditable row counts."""
    sessions = database.scalars(select(GameSession).order_by(GameSession.game_session_id)).all()
    events = database.scalars(
        select(GameplayEvent).order_by(
            GameplayEvent.game_session_id, GameplayEvent.event_timestamp, GameplayEvent.id
        )
    ).all()
    attempts = database.scalars(select(GameTaskAttempt)).all()
    results = database.scalars(select(GameResult).order_by(GameResult.game_session_id)).all()

    events_by_session: dict[str, list[GameplayEvent]] = {}
    for event in events:
        events_by_session.setdefault(event.game_session_id, []).append(event)
    attempts_by_task = {(row.game_session_id, row.task_id): row for row in attempts}
    session_by_id = {row.game_session_id: row for row in sessions}
    result_by_session = {row.game_session_id: row for row in results}
    session_rows: list[dict] = []
    answer_rows: list[dict] = []
    event_rows: list[dict] = []
    analytics_rows: list[dict] = []
    label_rows: list[dict] = []

    for row in sessions:
        game_events = events_by_session.get(row.game_session_id, [])
        started = next((e for e in game_events if e.event_type == "GAME_STARTED"), None)
        game_type = started.event_payload.get("game_type", "") if started else ""
        protocol = started.event_payload.get("recording_protocol", "") if started else ""
        session_rows.append({
            "game_session_id": row.game_session_id,
            "student_id_recorded": row.student_id,
            "student_code": _code(row.student_id),
            "concept_id": row.concept_id,
            "learning_cycle_id": str(row.learning_cycle_id),
            "assessment_phase": row.assessment_phase,
            "game_type": game_type,
            "status": row.status,
            "started_at": _iso(row.started_at),
            "completed_at": _iso(row.completed_at),
            "recording_protocol": protocol,
            "saved_assessment_complete": (
                row.status == "completed"
                and row.game_session_id in result_by_session
                and is_assessment_complete(row.game_session_id, database)
            ),
            "source_session_uuid": str(row.id),
        })
        # Empty label cells are deliberate. They must be filled only from
        # independently assessed teacher/Quiz/test evidence and a rubric.
        label_rows.append({
            "game_session_id": row.game_session_id,
            "student_code": _code(row.student_id),
            "concept_id": row.concept_id,
            "assessment_phase": row.assessment_phase,
        })
        last_shown: dict[tuple[str | None, object], str] = {}
        for event in game_events:
            payload = event.event_payload or {}
            event_rows.append({
                "source_event_id": str(event.id),
                "game_session_id": row.game_session_id,
                "student_id_recorded": row.student_id,
                "event_type": event.event_type,
                "task_id": event.task_id or "",
                "client_event_id": payload.get("client_event_id", ""),
                "step_index": payload.get("step_index", ""),
                "attempt_number": payload.get("attempt_number", ""),
                "event_timestamp": _iso(event.event_timestamp),
            })
            step_key = (event.task_id, payload.get("step_index", 0))
            if event.event_type == "QUESTION_SHOWN":
                shown = payload.get("equation_shown") or payload.get("question_prompt")
                if shown:
                    last_shown[step_key] = shown
                continue
            if event.event_type not in ("ANSWER_CORRECT", "ANSWER_INCORRECT"):
                continue
            attempt = attempts_by_task.get((row.game_session_id, event.task_id))
            submitted = payload.get("selected_choice", payload.get("submitted_value"))
            answer_rows.append({
                "source_event_id": str(event.id),
                "client_event_id": payload.get("client_event_id", ""),
                "game_session_id": row.game_session_id,
                "student_id_recorded": row.student_id,
                "student_code": _code(row.student_id),
                "learning_cycle_id": str(row.learning_cycle_id),
                "assessment_phase": row.assessment_phase,
                "game_type": payload.get("game_type") or game_type,
                "concept_id": row.concept_id,
                "activity_id": attempt.activity_id if attempt else "",
                "variant_id": payload.get("variant_id") or (attempt.variant_id if attempt else ""),
                "task_id": event.task_id or "",
                "difficulty_level": payload.get("difficulty_level") or (attempt.difficulty_level if attempt else ""),
                "step_index": payload.get("step_index", ""),
                "attempt_number": payload.get("attempt_number", ""),
                "answer_type": payload.get("answer_type", ""),
                "question_prompt": payload.get("question_prompt") or last_shown.get(step_key, ""),
                "expected_response": payload.get("expected_response", ""),
                "submitted_answer": submitted if submitted is not None else "",
                "is_correct": event.event_type == "ANSWER_CORRECT",
                "hints_before_attempt": payload.get("hints_before_attempt", ""),
                "first_attempt_correct": (
                    payload["attempt_number"] == 1 and event.event_type == "ANSWER_CORRECT"
                    if type(payload.get("attempt_number")) is int else ""
                ),
                "event_timestamp": _iso(event.event_timestamp),
                "content_version": payload.get("content_version", ""),
            })

    for row in results:
        session = session_by_id.get(row.game_session_id)
        analytics_rows.append({
            "source_result_id": str(row.id),
            "game_session_id": row.game_session_id,
            "student_id_recorded": row.student_id,
            "student_code": _code(row.student_id),
            "concept_id": row.concept_id,
            "learning_cycle_id": str(row.learning_cycle_id or (session.learning_cycle_id if session else "")),
            "assessment_phase": row.assessment_phase or (session.assessment_phase if session else ""),
            **{name: getattr(row, name) for name in ANALYTICS_FIELDS
               if name in (
                   "tasks_total", "tasks_attempted", "tasks_completed", "successful_tasks",
                   "game_success_rate", "game_completion_rate", "game_avg_attempts_per_task",
                   "game_hint_rate", "wrong_attempt_count", "retry_count", "total_hint_count",
                   "skipped_step_count", "game_active_time_sec", "game_difficulty_level",
                   "game_mastery_level", "model_version",
               )},
            "completed_at": _iso(row.completed_at),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "game_sessions.csv", SESSION_FIELDS, session_rows)
    _write_csv(output_dir / "student_answers.csv", ANSWER_FIELDS, answer_rows)
    _write_csv(output_dir / "game_events.csv", EVENT_FIELDS, event_rows)
    _write_csv(output_dir / "game_analytics.csv", ANALYTICS_FIELDS, analytics_rows)
    _write_csv(output_dir / "independent_assessment_labels.csv", LABEL_FIELDS, label_rows)
    counts = {
        "game_sessions": len(session_rows),
        "student_answers": len(answer_rows),
        "game_analytics": len(analytics_rows),
        "independent_assessment_labels_supplied": 0,
        "source_gameplay_events": len(events),
        "source_game_task_attempts": len(attempts),
        "incomplete_sessions": sum(not row["saved_assessment_complete"] for row in session_rows),
    }
    # The source IDs and counts let a researcher reconcile each CSV snapshot.
    assert len({row["source_event_id"] for row in answer_rows}) == len(answer_rows)
    assert len(event_rows) == len(events)
    assert len({row["source_result_id"] for row in analytics_rows}) == len(analytics_rows)
    (output_dir / "manifest.json").write_text(
        json.dumps({
            "exported_at_utc": datetime.now(UTC).isoformat(),
            "counts": counts,
            "student_codes_authoritative": False,
            "note": "Game student_id is caller-supplied until the shared student table is live; STU_ syntax alone does not verify identity.",
        }, indent=2),
        encoding="utf-8",
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        help="Optional override; defaults to DATABASE_URL from application settings/.env",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        help="New output folder; defaults to exports/game-<UTC timestamp> at the repository root",
    )
    parser.add_argument("--allow-remote-read", action="store_true")
    args = parser.parse_args()
    database_url = args.database_url
    if database_url is None:
        from app.core.config import Settings

        # Resolve on invocation, respecting DATABASE_URL over the configured
        # .env file. Never print credentials or place them in a subprocess argv.
        try:
            database_url = Settings().database_url
        except ValueError:
            parser.error("could not load database settings; check DATABASE_URL/.env")
    try:
        host = make_url(database_url).host
    except (ValueError, SQLAlchemyError):
        parser.error("invalid database URL; check DATABASE_URL/.env")
    if host not in (None, "localhost", "127.0.0.1", "::1") and not args.allow_remote_read:
        parser.error("remote database reads require --allow-remote-read")
    output_dir = args.output_dir or (
        DEFAULT_EXPORT_ROOT / datetime.now(UTC).strftime("game-%Y%m%dT%H%M%S-%fZ")
    )
    if output_dir.exists():
        parser.error("output directory already exists; choose a new folder to preserve earlier exports")
    engine = create_engine(database_url)
    try:
        with Session(engine) as database:
            if engine.dialect.name == "postgresql":
                database.connection().exec_driver_sql("SET TRANSACTION READ ONLY")
            # Atomically reserve the destination so concurrent commands cannot
            # overwrite each other's exports, even with the same explicit path.
            output_dir.mkdir(parents=True, exist_ok=False)
            counts = export_game_data(database, output_dir)
    except (SQLAlchemyError, OSError):
        parser.exit(1, "Export failed. Check database access/schema and folder permissions. Any partial output is preserved; retry into a fresh folder.\n")
    finally:
        engine.dispose()
    print(json.dumps({**counts, "output_dir": str(output_dir.resolve())}, indent=2))


if __name__ == "__main__":
    main()
