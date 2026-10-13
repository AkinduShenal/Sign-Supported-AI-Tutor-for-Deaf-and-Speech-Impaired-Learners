"""Reconcile synthetic real-browser actions, local PostgreSQL and CSV exports.

Read-only database access. Never use this engineering verifier for school data.
"""

import argparse
import csv
import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.modules.game.models import (
    GameResult,
    GameSession,
    GameTaskAttempt,
    GameplayEvent,
)
from scripts.export_game_collection import export_game_data


def verify(database_url: str, evidence_path: Path, output: Path) -> dict:
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or url.host not in (
        "127.0.0.1",
        "localhost",
        "::1",
    ):
        raise ValueError("Only isolated loopback PostgreSQL is supported")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("kind") != "synthetic_engineering_only":
        raise ValueError("Expected synthetic browser engineering evidence")
    if output.exists():
        raise FileExistsError(
            "Use a fresh export directory; existing exports are preserved"
        )
    engine = create_engine(database_url)
    try:
        with Session(engine) as database:
            database.connection().exec_driver_sql(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            counts = export_game_data(database, output)
            sessions = list(database.scalars(select(GameSession)))
            events = list(
                database.scalars(
                    select(GameplayEvent).order_by(GameplayEvent.event_timestamp)
                )
            )
            attempts = list(database.scalars(select(GameTaskAttempt)))
            results = list(database.scalars(select(GameResult)))
            by_session = {row.game_session_id: row for row in sessions}
            selected = {row["id"] for row in evidence["sessions"]}
            assert len(selected) == 6
            assert len([row for row in results if row.game_session_id in selected]) == 4
            assert (
                len(
                    [
                        row
                        for row in sessions
                        if row.game_session_id in selected
                        and row.status == "in_progress"
                    ]
                )
                == 2
            )
            for row in evidence["sessions"]:
                assert by_session[row["id"]].student_id == row["student"]
            for session_id in selected:
                actual = [
                    row
                    for row in events
                    if row.game_session_id == session_id
                    and row.event_type in ("ANSWER_CORRECT", "ANSWER_INCORRECT")
                ]
                expected = [
                    row for row in evidence["actions"] if row["session"] == session_id
                ]
                assert len(actual) == len(expected), (
                    session_id,
                    len(actual),
                    len(expected),
                )
                for saved, action in zip(actual, expected):
                    assert saved.task_id == action["task"]
                    # Hangman is one final-value step; existing evidence uses
                    # the backend's implicit step zero for that mode.
                    assert saved.event_payload.get("step_index", 0) == action["step"]
                    assert (saved.event_type == "ANSWER_CORRECT") == action["correct"]
                    assert (
                        saved.event_payload.get(
                            "submitted_value",
                            saved.event_payload.get("selected_choice"),
                        )
                        == action["response"]
                    )
            posted = {
                row["body"]["event_payload"]["client_event_id"]: row["body"]
                for row in evidence["captures"]
                if row["url"].endswith("/events")
            }
            keys = set()
            for row in events:
                client_id = row.event_payload.get("client_event_id")
                key = (row.game_session_id, client_id)
                assert client_id and key not in keys, "Duplicate source event key"
                keys.add(key)
                if row.game_session_id in selected:
                    assert client_id in posted
                    assert row.event_payload == posted[client_id]["event_payload"]
            for row in results:
                assert row.game_difficulty_level in (
                    "beginner",
                    "intermediate",
                    "advanced",
                )

            def read(name):
                with (output / name).open(encoding="utf-8-sig", newline="") as handle:
                    return list(csv.DictReader(handle))

            answers = read("student_answers.csv")
            exported_sessions = read("game_sessions.csv")
            exported_events = read("game_events.csv")
            exported_results = read("game_analytics.csv")
            outcomes = {
                str(row.id): row
                for row in events
                if row.event_type in ("ANSWER_CORRECT", "ANSWER_INCORRECT")
            }
            assert len(answers) == len(outcomes) == counts["student_answers"]
            assert {row["source_event_id"] for row in answers} == set(outcomes)
            assert (
                len(exported_events) == len(events) == counts["source_gameplay_events"]
            )
            assert {row["source_event_id"] for row in exported_events} == {
                str(row.id) for row in events
            }
            assert len(exported_sessions) == len(sessions) == counts["game_sessions"]
            assert len(exported_results) == len(results) == counts["game_analytics"]
            assert len(attempts) == counts["source_game_task_attempts"]
            for row in answers:
                source = outcomes[row["source_event_id"]]
                assert row["client_event_id"] == source.event_payload["client_event_id"]
                assert (
                    row["student_code"]
                    == row["student_id_recorded"]
                    == by_session[source.game_session_id].student_id
                )
                assert row["difficulty_level"] in ("easy", "medium", "hard")
            for row in exported_sessions:
                session_id = row["game_session_id"]
                if (
                    session_id in selected
                    and by_session[session_id].status == "in_progress"
                ):
                    assert row["saved_assessment_complete"].lower() == "false"
            report = {
                "status": "PASS",
                "data_kind": "synthetic_engineering_only",
                "browser_sessions_checked": len(selected),
                "browser_actions_checked": len(evidence["actions"]),
                "counts": counts,
                "checks": [
                    "assigned identity/session mapping",
                    "actual browser answers",
                    "stable client/source event IDs",
                    "no duplicate events",
                    "difficulty vocabularies",
                    "CSV/PostgreSQL counts",
                    "incomplete sessions retained",
                ],
            }
            (output / "smoke_reconciliation.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            return report
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--browser-evidence", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            verify(args.database_url, args.browser_evidence, args.output_dir), indent=2
        )
    )


if __name__ == "__main__":
    main()
