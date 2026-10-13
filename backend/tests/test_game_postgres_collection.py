"""Optional isolated PostgreSQL integration test for Game collection.

Run with GAME_COLLECTION_TEST_DATABASE_URL pointing only to local PostgreSQL.
The test uses synthetic evidence and never connects to Supabase.
"""

import csv
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.modules.game.models import GameResult, GameSession, GameTaskAttempt, GameplayEvent
from app.modules.game.schemas import (
    CreateGameSessionRequest,
    GameplayEventRequest,
    GameplayEventType,
    GameTaskAttemptRequest,
)
from app.modules.game.service import (
    complete_game_session,
    create_game_session,
    record_game_event,
    save_task_attempt,
)
from scripts.export_game_collection import export_game_data


def test_game_collection_on_local_postgres(tmp_path):
    url = os.getenv("GAME_COLLECTION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("set GAME_COLLECTION_TEST_DATABASE_URL for isolated local PostgreSQL")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or parsed.host not in ("127.0.0.1", "localhost", "::1"):
        pytest.fail("Game collection integration test requires loopback PostgreSQL")

    engine = create_engine(url)
    Base.metadata.create_all(
        engine, tables=[GameSession.__table__, GameplayEvent.__table__,
                        GameTaskAttempt.__table__, GameResult.__table__]
    )
    factory = sessionmaker(engine, autoflush=False, expire_on_commit=False)

    def emit(session_id: str, task_id: str | None, kind: str, payload: dict):
        request = GameplayEventRequest(
            game_session_id=session_id, task_id=task_id,
            event_type=GameplayEventType(kind), event_timestamp=datetime.now(UTC),
            event_payload={**payload, "client_event_id": str(uuid.uuid4())},
        )
        with factory() as database:
            return record_game_event(request, database)

    for student, mode in (("STU_TEST_001", "drag_drop"), ("STU_TEST_002", "hangman")):
        request = CreateGameSessionRequest(
            student_id=student, concept_id="linear_equations",
            learning_cycle_id=uuid.uuid4(), client_session_id=uuid.uuid4(),
        )
        with factory() as database:
            first = create_game_session(request, database)
        with factory() as database:
            again = create_game_session(request, database)
        assert first.game_session_id == again.game_session_id
        session_id = first.game_session_id
        emit(session_id, None, "GAME_STARTED", {
            "game_type": mode, "recording_protocol": "game-evidence-v1",
        })
        for task_id, difficulty in (
            ("E1", "easy"), ("E2", "easy"), ("M1", "medium"),
            ("M2", "medium"), ("H1", "hard"), ("H2", "hard"),
        ):
            failed_hangman = mode == "hangman" and task_id == "E1"
            count = 10 if failed_hangman else 1
            if mode == "drag_drop" and task_id == "H1":
                count = 2  # two successful equation-operation steps
            for number in range(1, count + 1):
                if failed_hangman and number > 1:
                    emit(session_id, task_id, "RETRY_STARTED", {})
                emit(session_id, task_id,
                     "ANSWER_INCORRECT" if failed_hangman else "ANSWER_CORRECT", {
                         "game_type": mode, "difficulty_level": difficulty,
                         "question_prompt": "x + 3 = 7", "expected_response": "4" if mode == "hangman" else "-3",
                         "submitted_value" if mode == "hangman" else "selected_choice": (
                             "3" if failed_hangman else "4" if mode == "hangman" else "-3"
                         ),
                         "answer_type": "final_value" if mode == "hangman" else "equation_operation",
                         "step_index": number - 1 if mode == "drag_drop" and task_id == "H1" else 0,
                         "step_count": 2 if mode == "drag_drop" and task_id == "H1" else 1,
                         "attempt_number": number if failed_hangman else 1,
                     })
            summary = GameTaskAttemptRequest(
                game_session_id=session_id, task_id=task_id, activity_id=f"ACT_{task_id}",
                variant_id=task_id, difficulty_level=difficulty,
                attempts_count=count, wrong_attempts=count if failed_hangman else 0,
                is_completed=True, is_successful=not failed_hangman,
                score=0 if failed_hangman else 1,
            )
            with factory() as database:
                saved = save_task_attempt(summary, database)
            with factory() as database:
                assert save_task_attempt(summary, database).id == saved.id
        if mode == "drag_drop":
            # PostgreSQL row locks serialize concurrent retries without a
            # schema change. SESSION_ENDED does not affect task metrics.
            duplicate = GameplayEventRequest(
                game_session_id=session_id, task_id=None,
                event_type=GameplayEventType.SESSION_ENDED,
                event_timestamp=datetime.now(UTC),
                event_payload={"client_event_id": str(uuid.uuid4())},
            )
            def write_duplicate():
                with factory() as database:
                    return record_game_event(duplicate, database).id
            with ThreadPoolExecutor(max_workers=2) as pool:
                ids = list(pool.map(lambda _: write_duplicate(), range(2)))
            assert ids[0] == ids[1]
        with factory() as database:
            completed = complete_game_session(session_id, database)
            assert completed.status.value == "completed"

    with factory() as database:
        assert database.scalar(select(func.count(GameSession.id))) == 2
        assert database.scalar(select(func.count(GameResult.id))) == 2
        counts = export_game_data(database, tmp_path)
        source_ids = {
            str(row.id) for row in database.scalars(
                select(GameplayEvent).where(GameplayEvent.event_type.in_(
                    ("ANSWER_CORRECT", "ANSWER_INCORRECT")
                ))
            )
        }
    assert counts["incomplete_sessions"] == 0
    with (tmp_path / "student_answers.csv").open(encoding="utf-8-sig", newline="") as handle:
        answers = list(csv.DictReader(handle))
    assert {row["source_event_id"] for row in answers} == source_ids
    assert {row["student_id_recorded"] for row in answers} == {"STU_TEST_001", "STU_TEST_002"}
    assert {row["game_type"] for row in answers} == {"drag_drop", "hangman"}
    engine.dispose()
