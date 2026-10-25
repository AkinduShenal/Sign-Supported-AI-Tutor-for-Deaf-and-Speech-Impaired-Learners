"""Offline CSV audit, explicit authenticity review and paired dataset preparation.

No application settings, database engine or API is imported. Source files are
read only. Real observations require an exact session approval and complete,
reconciled evidence. Unknown sessions never become real data by default.
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Literal
from zipfile import ZipFile
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .research_dataset import extract_research_features, feature_set
from .research_schema import (
    IndependentLabel,
    ResearchObservation,
    validate_research_dataset,
)
from .teacher_assessments import Purpose, TeacherAssessment

DEVELOPMENT_SESSIONS = frozenset(
    {
        "GAME-SES-2026-001",
        "GAME-SES-2026-002",
        "GAME-SES-2026-003",
    }
)
CLASSES = ("beginner", "intermediate", "advanced")
COHORT = frozenset(f"STU_{number:03}" for number in range(1, 17))
INVALID_STUDENT_CODES = frozenset({"STU_0014"})
INVALID_CODE_DECISION = "EXCLUDED_INVALID_STUDENT_CODE"
INTEGRITY_QUARANTINE_DECISION = "QUARANTINED_INTEGRITY"
INVALID_CODE_REASON = (
    "Researcher-confirmed accidental student-code entry STU_0014; preserve as "
    "recorded, exclude from training/evaluation, and never reassign to STU_014"
)
TABLES = {
    "game_sessions": (
        "game_session_id",
        "source_session_uuid",
        "student_id_recorded",
        "student_code",
        "concept_id",
        "learning_cycle_id",
        "assessment_phase",
        "game_type",
        "status",
        "started_at",
        "completed_at",
        "recording_protocol",
        "saved_assessment_complete",
    ),
    "student_answers": (
        "source_event_id",
        "client_event_id",
        "game_session_id",
        "student_id_recorded",
        "student_code",
        "concept_id",
        "learning_cycle_id",
        "assessment_phase",
        "game_type",
        "activity_id",
        "variant_id",
        "task_id",
        "difficulty_level",
        "step_index",
        "attempt_number",
        "answer_type",
        "expected_response",
        "submitted_answer",
        "is_correct",
        "hints_before_attempt",
        "first_attempt_correct",
        "event_timestamp",
        "content_version",
    ),
    "game_events": (
        "source_event_id",
        "client_event_id",
        "game_session_id",
        "student_id_recorded",
        "event_type",
        "task_id",
        "step_index",
        "attempt_number",
        "event_timestamp",
    ),
    "game_analytics": (
        "source_result_id",
        "game_session_id",
        "student_id_recorded",
        "student_code",
        "concept_id",
        "learning_cycle_id",
        "assessment_phase",
        "tasks_total",
        "tasks_attempted",
        "tasks_completed",
        "successful_tasks",
        "wrong_attempt_count",
        "retry_count",
        "total_hint_count",
    ),
}


class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class VerifiedSession(Contract):
    student_code: str
    concept: str
    game_type: Literal["drag_drop", "hangman"]
    source_reference: Annotated[str, Field(min_length=1)]


class VariantEvidence(Contract):
    activity_id: str
    difficulty: Literal["easy", "medium", "hard"]
    expected_operations: Annotated[list[str], Field(min_length=1)]
    final_answer: str


class CollectionReview(Contract):
    schema_version: Literal["game-collection-review-v1"] = "game-collection-review-v1"
    verified_sessions: dict[str, VerifiedSession]
    development_sessions: dict[str, Annotated[str, Field(min_length=1)]] = Field(
        default_factory=dict
    )
    teacher_scores: dict[str, Annotated[int, Field(ge=0, le=10)]]
    assessed_on: Annotated[date, Field(strict=False)]
    assessment_timezone: str = "Asia/Colombo"
    assessment_timing: Literal["after_gameplay"] = "after_gameplay"
    revision_before_assessment: Literal[True] = True
    revision_description: Annotated[str, Field(min_length=1)]
    teacher_source_reference: Annotated[str, Field(min_length=1)]
    rubric_version: Annotated[str, Field(min_length=1)]
    variant_catalog_source: Annotated[str, Field(min_length=1)]
    variant_catalog_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    variant_catalog: dict[str, VariantEvidence]

    @model_validator(mode="after")
    def distinct_authenticity_decisions(self) -> "CollectionReview":
        if set(self.verified_sessions) & (
            DEVELOPMENT_SESSIONS | set(self.development_sessions)
        ):
            raise ValueError(
                "Verified sessions conflict with exact development exclusions"
            )
        if any(not basis.strip() for basis in self.development_sessions.values()):
            raise ValueError("Development exclusions require a verification basis")
        return self


def proficiency(score: int) -> str:
    return "beginner" if score <= 4 else ("intermediate" if score <= 7 else "advanced")


def has_invalid_student_code(session: dict) -> bool:
    # Check the original identity too: an edited projection must not turn the
    # accidental entry into an apparently valid STU_014 observation.
    return any(
        session.get(key) in INVALID_STUDENT_CODES
        for key in ("student_code", "student_id_recorded")
    )


def read_export(source: Path) -> tuple[dict, dict]:
    """Read fixed ZIP members without extracting paths or changing the source."""
    if source.is_dir():
        contents = {
            name: (source / name).read_bytes()
            for name in [*(f"{table}.csv" for table in TABLES), "manifest.json"]
        }
    else:
        with ZipFile(source) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate ZIP members make source identity ambiguous")
            contents = {}
            for name in [*(f"{table}.csv" for table in TABLES), "manifest.json"]:
                if archive.getinfo(name).file_size > 100 * 1024 * 1024:
                    raise ValueError(
                        "Export member exceeds the offline audit size limit"
                    )
                contents[name] = archive.read(name)
    tables = {}
    for table, required in TABLES.items():
        reader = csv.DictReader(
            io.StringIO(contents[f"{table}.csv"].decode("utf-8-sig"))
        )
        if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
            raise ValueError(f"Duplicate headers in {table}")
        if set(required) - set(reader.fieldnames or []):
            raise ValueError(f"Missing required columns in {table}")
        tables[table] = list(reader)
    provenance = {
        "source": str(source.resolve()),
        "file_sha256": {
            name: hashlib.sha256(data).hexdigest() for name, data in contents.items()
        },
        "manifest": json.loads(contents["manifest.json"]),
    }
    if source.is_file():
        provenance["zip_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    return tables, provenance


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Source timestamp lacks timezone evidence")
    return parsed


def boolean(value: str) -> bool:
    if value not in ("True", "False"):
        raise ValueError("Missing/invalid exported boolean")
    return value == "True"


def step_key(row: dict, mode: str) -> tuple[str, int]:
    # The existing Hangman protocol defines exactly one final-value step;
    # its omitted index means zero. A missing Drag & Drop index stays invalid.
    index = (
        0 if mode == "hangman" and row["step_index"] == "" else int(row["step_index"])
    )
    if index < 0 or (mode == "hangman" and index != 0):
        raise ValueError("Invalid operation/guess step index")
    return row["task_id"], index


def audit_attempt_chronology(rows: list[dict], events: list[dict], mode: str) -> dict | None:
    """Validate numbered outcomes; ties require corroborating submission events.

    Called only after game-evidence-v1, exact ownership and projection checks.
    The recorder increments the per-step counter synchronously, independently of
    its millisecond clock. UUID/CSV order never supplies temporal evidence.
    """
    numbered = sorted(rows, key=lambda row: int(row["attempt_number"]))
    numbers = [int(row["attempt_number"]) for row in numbered]
    if numbers != list(range(1, len(rows) + 1)):
        raise ValueError("Duplicate or missing first/subsequent attempt evidence")
    times = [timestamp(row["event_timestamp"]) for row in numbered]
    if times != sorted(times):
        raise ValueError("Attempt numbering contradicts event chronology")
    tied = {value for value, count in Counter(times).items() if count > 1}
    if not tied:
        return None
    key = step_key(numbered[0], mode)
    submissions = [row for row in events if row["event_type"] == "ANSWER_SUBMITTED"
                   and step_key(row, mode) == key]
    if len(submissions) != len(rows) or sorted(int(row["attempt_number"]) for row in submissions) != numbers:
        raise ValueError("Timestamp ties require complete unique numbered submission evidence")
    submissions = sorted(submissions, key=lambda row: int(row["attempt_number"]))
    all_rows = [*numbered, *submissions]
    for field in ("source_event_id", "client_event_id"):
        identities = [row[field] for row in all_rows]
        if any(not value.strip() for value in identities) or len(set(identities)) != len(identities):
            raise ValueError("Timestamp ties require distinct nonempty source/client event identities")
    if any(row["game_session_id"] != numbered[0]["game_session_id"]
           or row["student_id_recorded"] != numbered[0]["student_id_recorded"]
           for row in all_rows):
        raise ValueError("Timestamp tie submission ownership mismatch")
    submitted_times = [timestamp(row["event_timestamp"]) for row in submissions]
    if any(submitted > outcome for submitted, outcome in zip(submitted_times, times)) or any(
        outcome > following for outcome, following in zip(times, submitted_times[1:])
    ):
        raise ValueError("Attempt submission/outcome sequence contradicts event chronology")
    if any(row["event_type"] == "HINT_REQUESTED" and step_key(row, mode) == key
           and timestamp(row["event_timestamp"]) in times for row in events):
        raise ValueError("Timestamp ties lack independent hint/answer ordering")
    shown = [timestamp(row["event_timestamp"]) for row in events
             if row["event_type"] == "QUESTION_SHOWN" and step_key(row, mode) == key]
    completed = [timestamp(row["event_timestamp"]) for row in events
                 if row["event_type"] == "TASK_COMPLETED" and step_key(row, mode) == key]
    if not shown or max(shown) > submitted_times[0] or len(completed) != 1 or completed[0] < times[-1]:
        raise ValueError("Timestamp tie sequence conflicts with shown/completed step evidence")
    return {
        "policy": "recorded-attempt-sequence-ties-v1",
        "decision": "ACCEPT_RECORDED_LOGICAL_SEQUENCE",
        "task_id": key[0], "step_index": key[1],
        "recorded_logical_attempt_order": numbers,
        "original_exported_outcome_attempt_order": [int(row["attempt_number"]) for row in rows],
        "tied_attempt_groups": [
            {"original_timestamp": next(row["event_timestamp"] for row in numbered
                                         if timestamp(row["event_timestamp"]) == value),
             "attempt_numbers": [number for number, time in zip(numbers, times) if time == value]}
            for value in sorted(tied)
        ],
        "wall_clock_order_within_ties": "UNRESOLVED_AT_RECORDED_PRECISION",
        "basis": "game-evidence-v1 per-step monotonic counter, complete numbered submissions, nondecreasing submission/outcome sequence; UUID and CSV order ignored",
        "original_outcome_rows": rows,
        "original_submission_rows": [row for row in events if row in submissions],
        "source_rows_modified": False,
    }


def prepare_session(
    session: dict,
    answers: list[dict],
    events: list[dict],
    results: list[dict],
    review: CollectionReview,
    *,
    independent_assessment: TeacherAssessment | None = None,
    analysis_purpose: Purpose | None = None,
) -> tuple[ResearchObservation, dict]:
    if analysis_purpose is not None and independent_assessment is None:
        raise ValueError("An explicit analysis purpose requires independent assessment evidence")
    if has_invalid_student_code(session):
        raise ValueError(INVALID_CODE_REASON)
    sid, mode = session["game_session_id"], session["game_type"]
    approval = review.verified_sessions[sid]
    if (session["student_code"], session["concept_id"], mode) != (
        approval.student_code,
        approval.concept,
        approval.game_type,
    ):
        raise ValueError("Exact approval does not match student/concept/mode")
    if (
        session["student_code"] not in COHORT
        or session["concept_id"] != "linear_equations"
    ):
        raise ValueError("Outside declared learner/concept cohort")
    if not approval.source_reference.strip():
        raise ValueError("Missing authenticity provenance")
    if session["status"] != "completed" or not boolean(
        session["saved_assessment_complete"]
    ):
        raise ValueError("Saved assessment is incomplete")
    if session["recording_protocol"] != "game-evidence-v1" or len(results) != 1:
        raise ValueError("Need audited recording protocol and one saved result")
    if session["student_id_recorded"] != session["student_code"]:
        raise ValueError("Recorded learner and student code differ")
    result = results[0]
    for row in [*answers, *results]:
        for key in (
            "student_id_recorded",
            "student_code",
            "concept_id",
            "assessment_phase",
            "learning_cycle_id",
        ):
            if row[key] != session[key]:
                raise ValueError(f"Source learner/session context mismatch: {key}")
    for row in events:
        if row["student_id_recorded"] != session["student_id_recorded"]:
            raise ValueError("Event learner/session mismatch")
    event_types = Counter(row["event_type"] for row in events)
    if event_types["GAME_STARTED"] != 1 or event_types["GAME_COMPLETED"] != 1:
        raise ValueError("Need one GAME_STARTED and GAME_COMPLETED event")
    outcome_events = {
        row["source_event_id"]: row
        for row in events
        if row["event_type"] in ("ANSWER_CORRECT", "ANSWER_INCORRECT")
    }
    if set(outcome_events) != {row["source_event_id"] for row in answers}:
        raise ValueError("Answers do not match the complete outcome-event roster")
    for row in answers:
        event = outcome_events[row["source_event_id"]]
        for key in (
            "task_id",
            "client_event_id",
            "step_index",
            "attempt_number",
            "event_timestamp",
        ):
            if row[key] != event[key] or not row["client_event_id"]:
                raise ValueError("Answer source-ID/event projection mismatch")
        if boolean(row["is_correct"]) != (event["event_type"] == "ANSWER_CORRECT"):
            raise ValueError("Answer correctness contradicts its source event")
        if row["game_type"] != mode or row["answer_type"] != (
            "final_value" if mode == "hangman" else "equation_operation"
        ):
            raise ValueError(
                "Operation selections and final-value guesses must remain distinct"
            )
        if row["variant_id"] != row["task_id"]:
            raise ValueError("Variant/task identity mismatch")
    task_ids = {row["task_id"] for row in answers}
    completed = [
        row["task_id"] for row in events if row["event_type"] == "TASK_COMPLETED"
    ]
    if len(task_ids) != 6 or set(completed) != task_ids:
        raise ValueError("Need exactly six answered and completed tasks")
    by_step = defaultdict(list)
    difficulties = Counter()
    planned = set()
    for task_id in sorted(task_ids):
        variant = review.variant_catalog.get(task_id)
        if variant is None:
            raise ValueError("Variant is missing from the frozen source catalog")
        difficulties[variant.difficulty] += 1
        count = 1 if mode == "hangman" else len(variant.expected_operations)
        planned.update((task_id, index) for index in range(count))
        for row in [answer for answer in answers if answer["task_id"] == task_id]:
            key = step_key(row, mode)
            if (
                key not in planned
                or row["activity_id"] != variant.activity_id
                or row["difficulty_level"] != variant.difficulty
            ):
                raise ValueError(
                    "Answer conflicts with frozen variant/step/activity evidence"
                )
            expected = (
                variant.final_answer
                if mode == "hangman"
                else variant.expected_operations[key[1]]
            )
            if row["expected_response"] != expected:
                raise ValueError(
                    "Expected response conflicts with frozen variant catalog"
                )
            correct = (
                (Fraction(row["submitted_answer"]) == Fraction(expected))
                if mode == "hangman"
                else row["submitted_answer"] == expected
            )
            if correct != boolean(row["is_correct"]):
                raise ValueError(
                    "Submitted response conflicts with recorded correctness"
                )
            by_step[key].append(row)
    if difficulties != Counter({"easy": 2, "medium": 2, "hard": 2}):
        raise ValueError("Assessment difficulty roster is not 2 easy/2 medium/2 hard")
    shown = {
        step_key(row, mode) for row in events if row["event_type"] == "QUESTION_SHOWN"
    }
    if set(by_step) != planned or shown != planned:
        raise ValueError("Planned, shown and answered step rosters differ")
    completed_steps = [
        step_key(row, mode) for row in events if row["event_type"] == "TASK_COMPLETED"
    ]
    if len(completed_steps) != len(planned) or set(completed_steps) != planned:
        raise ValueError(
            "Completion events must cover each operation/guess step exactly once"
        )
    chronology_decisions = []
    for rows in by_step.values():
        decision = audit_attempt_chronology(rows, events, mode)
        if decision is not None:
            chronology_decisions.append(decision)
        for row in rows:
            first_correct = int(row["attempt_number"]) == 1 and boolean(
                row["is_correct"]
            )
            if boolean(row["first_attempt_correct"]) != first_correct:
                raise ValueError("Exported first-attempt correctness is inconsistent")
    first_correct = sum(
        boolean(row["is_correct"]) for row in answers if row["attempt_number"] == "1"
    )
    wrong = sum(not boolean(row["is_correct"]) for row in answers)
    retries = event_types["RETRY_STARTED"]
    if retries != len(answers) - len(planned):
        raise ValueError("Retry events do not reconcile to subsequent submissions")
    hints = [row for row in events if row["event_type"] == "HINT_REQUESTED"]
    if any(step_key(row, mode) not in planned for row in hints):
        raise ValueError("Hints do not match the planned step roster")
    for row in answers:
        before = sum(
            step_key(hint, mode) == step_key(row, mode)
            and timestamp(hint["event_timestamp"]) <= timestamp(row["event_timestamp"])
            for hint in hints
        )
        if int(row["hints_before_attempt"]) != before:
            raise ValueError("Hints-before-attempt do not reconcile with hint events")
    for key, expected in (
        ("tasks_total", 6),
        ("tasks_attempted", 6),
        ("tasks_completed", 6),
        ("wrong_attempt_count", wrong),
        ("retry_count", retries),
        ("total_hint_count", len(hints)),
    ):
        if int(result[key]) != expected:
            raise ValueError(f"Session summary conflicts with source evidence: {key}")
    start = min(
        timestamp(session["started_at"]),
        *(timestamp(row["event_timestamp"]) for row in events),
    )
    end = max(
        timestamp(session["completed_at"]),
        *(timestamp(row["event_timestamp"]) for row in events),
    )
    if independent_assessment is not None:
        if analysis_purpose is None:
            raise ValueError("Independent assessment requires an explicit analysis purpose")
        label = independent_assessment.label_for(session, start, end, analysis_purpose)
    else:
        label = legacy_teacher_label(session, review, end)
    observation = ResearchObservation(
        student_code=session["student_code"],
        session_id=sid,
        concept=session["concept_id"],
        game_type=mode,
        activity_ids=sorted({row["activity_id"] for row in answers}),
        assessment_phase=session["assessment_phase"],
        observation_started_at=start,
        observation_ended_at=end,
        total_steps=len(planned),
        first_attempt_correct_steps=first_correct,
        first_attempt_observation_complete=True,
        wrong_attempts=wrong,
        retry_count=retries,
        hint_count=len(hints),
        steps_with_hints=len({step_key(row, mode) for row in hints}),
        hint_observation_complete=True,
        tasks_total=6,
        tasks_completed=6,
        task_completed=True,
        skipped_steps=0,
        # Timestamps establish an observation window, not reliable active time.
        task_duration_seconds=None,
        task_duration_reliable=False,
        difficulty_label=None,
        mastery_label=label,
    )
    evidence = {
        "student_code": observation.student_code,
        "session_id": sid,
        "source_session_uuid": session["source_session_uuid"],
        "source_result_id": result["source_result_id"],
        "source_event_ids": sorted(row["source_event_id"] for row in events),
        "source_answer_event_ids": sorted(row["source_event_id"] for row in answers),
        "authenticity_source": approval.source_reference,
        "activity_difficulty_task_counts": dict(difficulties),
        "answer_semantics": "final_value_guess"
        if mode == "hangman"
        else "inverse_operation_selection",
        "missing_content_version_answers": sum(
            not row["content_version"] for row in answers
        ),
        "source_session_elapsed_seconds": (
            timestamp(session["completed_at"]) - timestamp(session["started_at"])
        ).total_seconds(),
        "source_reported_active_seconds_unverified": result.get("game_active_time_sec"),
        "task_summaries_exported": False,
        "timing_reliability": "unverified: active task timing/focus records are not in this export",
        "planned_roster_basis": "frozen current variant catalog reconciled with every shown/answered step plus saved-assessment-complete assertion; historic content version unavailable",
    }
    if chronology_decisions:
        evidence["attempt_chronology_decisions"] = chronology_decisions
    return observation, evidence


def legacy_teacher_label(session: dict, review: CollectionReview, end: datetime) -> IndependentLabel:
    """Keep prior preparation/import behavior unchanged unless new evidence is supplied."""
    if end.astimezone(ZoneInfo(review.assessment_timezone)).date() > review.assessed_on:
        raise ValueError("Gameplay occurs after the recorded assessment date")
    score = review.teacher_scores.get(session["student_code"])
    if score is None:
        raise ValueError("Independent teacher label is missing")
    return IndependentLabel(
        student_code=session["student_code"],
        session_id=session["game_session_id"],
        concept=session["concept_id"],
        assessment_phase=session["assessment_phase"],
        value=proficiency(score),
        source="teacher",
        source_reference=review.teacher_source_reference,
        assessed_on=review.assessed_on,
        assessment_timing=review.assessment_timing,
        revision_before_assessment=True,
        revision_description=review.revision_description,
        assessment_score=score,
        assessment_max_score=10,
        rubric_version=review.rubric_version,
        gameplay_independent=True,
    )


def audit_collection(tables: dict, provenance: dict, review: CollectionReview) -> dict:
    """Return source-linked outputs; no files are written and no model is fitted."""
    sessions = tables["game_sessions"]
    source_checks = {}
    global_issues = []
    analytics_ownership_issues = defaultdict(list)
    for table, key in (
        ("game_sessions", "game_session_id"),
        ("game_events", "source_event_id"),
        ("student_answers", "source_event_id"),
        ("game_analytics", "source_result_id"),
    ):
        ids = Counter(row[key] for row in tables[table])
        duplicates = sum(count - 1 for count in ids.values() if count > 1)
        clients = Counter(
            row["client_event_id"]
            for row in tables[table]
            if row.get("client_event_id")
        )
        duplicate_clients = sum(count - 1 for count in clients.values() if count > 1)
        source_checks[table] = {
            "rows": len(tables[table]),
            "duplicate_source_ids": duplicates,
            "duplicate_client_ids": duplicate_clients,
            "missing_source_ids": ids.get("", 0),
        }
        if duplicates or duplicate_clients or ids.get("", 0):
            global_issues.append(f"Ambiguous/missing source IDs in {table}")
    parent_uuids = Counter(row["source_session_uuid"] for row in sessions)
    source_checks["game_sessions"]["duplicate_source_session_uuids"] = sum(
        count - 1 for count in parent_uuids.values() if count > 1
    )
    source_checks["game_sessions"]["missing_source_session_uuids"] = parent_uuids.get("", 0)
    if any(count > 1 for count in parent_uuids.values()) or "" in parent_uuids:
        global_issues.append("Ambiguous/missing parent session UUIDs")
    session_ids = {row["game_session_id"] for row in sessions}
    owners = {row["game_session_id"]: row for row in sessions}
    for table in ("game_events", "student_answers", "game_analytics"):
        orphans = sum(
            row["game_session_id"] not in session_ids for row in tables[table]
        )
        source_checks[table]["orphan_session_rows"] = orphans
        mismatches = sum(
            row["game_session_id"] in owners
            and row["student_id_recorded"]
            != owners[row["game_session_id"]]["student_id_recorded"]
            for row in tables[table]
        )
        source_checks[table]["recorded_learner_mismatches"] = mismatches
        if orphans:
            global_issues.append(f"Orphan session evidence in {table}")
        if mismatches and table != "game_analytics":
            global_issues.append(f"Recorded learner/session mismatch in {table}")
        if table == "game_analytics":
            for row in tables[table]:
                parent = owners.get(row["game_session_id"])
                if parent is None or row["student_id_recorded"] == parent["student_id_recorded"]:
                    continue
                analytics_ownership_issues[row["game_session_id"]].append(
                    {
                        "table": table,
                        "source_result_id": row["source_result_id"],
                        "reason": "Analytics learner ownership conflicts with its exact parent session",
                        "field_disagreements": {
                            key: {"parent": parent[key], "analytics": row[key]}
                            for key in (
                                "student_id_recorded", "student_code", "concept_id",
                                "learning_cycle_id", "assessment_phase",
                            )
                            if row[key] != parent[key]
                        },
                    }
                )
    analytics_parents = Counter(row["game_session_id"] for row in tables["game_analytics"])
    if any(count > 1 for count in analytics_parents.values()):
        global_issues.append("Multiple analytics records share a parent session")
    answer_keys = Counter(
        (
            row["game_session_id"],
            row["task_id"],
            row["step_index"],
            row["attempt_number"],
        )
        for row in tables["student_answers"]
        if row["task_id"] and row["attempt_number"]
    )
    source_checks["student_answers"]["duplicate_attempt_keys"] = sum(
        count - 1 for count in answer_keys.values() if count > 1
    )
    source_checks["student_answers"]["logical_attempt_identity_unavailable"] = sum(
        not row["task_id"] or not row["attempt_number"]
        for row in tables["student_answers"]
    )
    if source_checks["student_answers"]["duplicate_attempt_keys"]:
        global_issues.append("Duplicate logical answer attempts")
    events_by_id = {row["source_event_id"]: row for row in tables["game_events"]}
    missing_answer_sources = sum(
        row["source_event_id"] not in events_by_id for row in tables["student_answers"]
    )
    source_checks["student_answers"]["missing_source_event_links"] = (
        missing_answer_sources
    )
    projection_conflicts = sum(
        row["source_event_id"] in events_by_id
        and any(
            row[key] != events_by_id[row["source_event_id"]][key]
            for key in (
                "game_session_id",
                "task_id",
                "client_event_id",
                "step_index",
                "attempt_number",
                "event_timestamp",
            )
        )
        for row in tables["student_answers"]
    )
    source_checks["student_answers"]["source_event_projection_conflicts"] = (
        projection_conflicts
    )
    if missing_answer_sources or projection_conflicts:
        global_issues.append(
            "Answer source-event linkage is incomplete or inconsistent"
        )
    manifest_counts = provenance.get("manifest", {}).get("counts", {})
    for name, actual in (
        ("game_sessions", len(sessions)),
        ("student_answers", len(tables["student_answers"])),
        ("source_gameplay_events", len(tables["game_events"])),
        ("game_analytics", len(tables["game_analytics"])),
    ):
        if manifest_counts.get(name) != actual:
            global_issues.append(f"Manifest count mismatch: {name}")
    indexed = {}
    for table in ("student_answers", "game_events", "game_analytics"):
        index = defaultdict(list)
        for row in tables[table]:
            index[row["game_session_id"]].append(row)
        indexed[table] = index
    # Only analytics ownership conflicts are eligible for local quarantine.
    # All shared identity, linkage, projection and manifest checks must pass
    # first. A duplicate/orphan/cross-session source is never downgraded here.
    isolation_confirmed = not global_issues
    quarantined = set(analytics_ownership_issues) if isolation_confirmed else set()
    if analytics_ownership_issues and not isolation_confirmed:
        global_issues.append(
            "Analytics ownership conflicts cannot be isolated while shared integrity fails"
        )
    observations, evidence, session_review = [], [], []
    for session in sorted(sessions, key=lambda row: row["game_session_id"]):
        sid = session["game_session_id"]
        aa, ee, rr = (
            indexed[name][sid]
            for name in ("student_answers", "game_events", "game_analytics")
        )
        status, reason = "REVIEW REQUIRED", "Authenticity not explicitly verified"
        if session["student_code"] not in COHORT:
            reason += "; outside the candidate STU_001–STU_016 roster"
        if has_invalid_student_code(session):
            status, reason = INVALID_CODE_DECISION, INVALID_CODE_REASON
        elif sid in DEVELOPMENT_SESSIONS or sid in review.development_sessions:
            status, reason = (
                "EXCLUDED DEVELOPMENT",
                review.development_sessions.get(
                    sid, "Exact user-confirmed development session ID"
                ),
            )
        elif sid in quarantined:
            status, reason = (
                INTEGRITY_QUARANTINE_DECISION,
                "Analytics learner ownership mismatch; exact session evidence quarantined without reassignment",
            )
        elif sid in review.verified_sessions:
            try:
                if global_issues:
                    raise ValueError("; ".join(global_issues))
                observation, linked = prepare_session(session, aa, ee, rr, review)
                observations.append(observation)
                evidence.append(linked)
                status, reason = (
                    "INCLUDED VERIFIED",
                    "Exact authenticity approval and evidence/label checks passed",
                )
            except (ValueError, KeyError, TypeError) as error:
                status, reason = "VERIFIED / EVIDENCE BLOCKED", str(error)
        session_review.append(
            {
                "session_id": sid,
                "student_code": session["student_code"],
                "student_id_recorded": session["student_id_recorded"],
                "game_mode": session["game_type"],
                "completion": session["status"],
                "saved_assessment_complete": session["saved_assessment_complete"],
                "started_at": session["started_at"],
                "answers": len(aa),
                "events": len(ee),
                "session_summaries": len(rr),
                "task_summaries": "not exported",
                "completed_task_events": sum(
                    row["event_type"] == "TASK_COMPLETED" for row in ee
                ),
                "decision": status,
                "reason": reason,
                "integrity_quarantined": sid in quarantined,
            }
        )
    records = validate_research_dataset(observations)
    features = {}
    for name in ("score_only", "score_plus_behaviour"):
        spec = feature_set(name)
        features[name] = [
            {
                "student_code": row.student_code,
                "session_id": row.session_id,
                **{
                    key: extract_research_features(row).values[key]
                    for key in spec.names
                },
            }
            for row in records
        ]
    verified_codes = {row.student_code for row in records}
    distribution = {
        level: sum(
            proficiency(review.teacher_scores[code]) == level for code in verified_codes
        )
        for level in CLASSES
    }
    candidates = [
        row
        for row in sessions
        if row["student_code"] in COHORT and not has_invalid_student_code(row)
    ]
    invalid_sessions = [row for row in sessions if has_invalid_student_code(row)]
    authentic_sessions = [
        row for row in candidates
        if row["game_session_id"] in review.verified_sessions
        and row["game_session_id"] not in DEVELOPMENT_SESSIONS
        and row["game_session_id"] not in review.development_sessions
        and (
            row["student_code"], row["concept_id"], row["game_type"]
        ) == (
            review.verified_sessions[row["game_session_id"]].student_code,
            review.verified_sessions[row["game_session_id"]].concept,
            review.verified_sessions[row["game_session_id"]].game_type,
        )
    ]
    return {
        "summary": {
            "export_sessions": len(sessions),
            "candidate_student_codes": sorted(COHORT),
            "candidate_learners_present": len(
                {row["student_code"] for row in candidates}
            ),
            "target_learner_sessions": len(candidates),
            "target_completed_sessions": sum(
                row["status"] == "completed" for row in candidates
            ),
            "target_incomplete_sessions": sum(
                row["status"] != "completed" for row in candidates
            ),
            "invalid_student_codes": sorted(INVALID_STUDENT_CODES),
            "invalid_student_code_sessions": len(invalid_sessions),
            "invalid_student_code_completed_sessions": sum(
                row["status"] == "completed" for row in invalid_sessions
            ),
            "invalid_student_code_incomplete_sessions": sum(
                row["status"] != "completed" for row in invalid_sessions
            ),
            "eligible_learners": len(verified_codes),
            "eligible_sessions": len(records),
            "eligible_completed_sessions": len(records),
            "explicitly_verified_learners": len(
                {row["student_code"] for row in authentic_sessions}
            ),
            "explicitly_verified_sessions": len(authentic_sessions),
            "verified_completed_sessions": sum(
                row["status"] == "completed"
                and row["saved_assessment_complete"] == "True"
                for row in authentic_sessions
            ),
            "integrity_quarantined_sessions": len(quarantined),
            "integrity_quarantined_and_invalid_code_sessions": sum(
                row["game_session_id"] in quarantined for row in invalid_sessions
            ),
            "unknown_candidate_sessions": sum(
                row["game_session_id"] not in review.verified_sessions
                and row["game_session_id"] not in DEVELOPMENT_SESSIONS
                and row["game_session_id"] not in review.development_sessions
                for row in candidates
            ),
            "unlabeled_candidate_learners": sorted(
                {row["student_code"] for row in candidates} - review.teacher_scores.keys()
            ),
            "model_observations": {name: len(rows) for name, rows in features.items()},
            "exact_development_exclusions": sorted(session_ids & DEVELOPMENT_SESSIONS),
            "researcher_development_exclusions": sorted(
                session_ids & (set(review.development_sessions) - DEVELOPMENT_SESSIONS)
            ),
            "decisions": dict(Counter(row["decision"] for row in session_review)),
            "eligible_sessions_per_learner": {
                code: sum(row.student_code == code for row in records)
                for code in sorted(COHORT)
            },
            "eligible_modes": sorted({row.game_type for row in records}),
            "no_date_based_exclusion": True,
        },
        "source_provenance": provenance,
        "source_checks": source_checks,
        "global_issues": global_issues,
        "session_integrity_issues": dict(analytics_ownership_issues),
        "quarantine": {
            "policy": "analytics ownership conflicts only; shared integrity must pass",
            "session_boundaries_established": isolation_confirmed,
            "session_ids": sorted(quarantined),
            "records": [
                {
                    "session_id": sid,
                    "decision": INTEGRITY_QUARANTINE_DECISION,
                    "issues": analytics_ownership_issues[sid],
                    "original_evidence": {
                        "game_sessions": [row for row in sessions if row["game_session_id"] == sid],
                        **{name: indexed[name][sid] for name in indexed},
                    },
                }
                for sid in sorted(quarantined)
            ],
        },
        "approved_ids_missing_from_export": sorted(
            set(review.verified_sessions) - session_ids
        ),
        "session_review": session_review,
        "observations": [row.model_dump(mode="json") for row in records],
        "source_links": evidence,
        "features": features,
        "label_matching": [
            {
                "student_code": code,
                "teacher_score": score,
                "teacher_level": proficiency(score),
                "included_session_ids": [
                    row.session_id for row in records if row.student_code == code
                ],
                "status": "MATCHED VERIFIED"
                if code in verified_codes
                else "NO VERIFIED ELIGIBLE GAMEPLAY",
            }
            for code, score in sorted(review.teacher_scores.items())
        ],
        "learner_class_distribution": distribution,
        "feature_definitions": {
            name: list(feature_set(name).names) for name in features
        },
    }


def feasibility(audit: dict, config) -> dict:
    from .research_training import learner_split, prepare_cohort

    rows = audit["observations"]
    reasons = list(audit["global_issues"])
    if audit["approved_ids_missing_from_export"]:
        reasons.append("Explicitly approved sessions are missing from the export")
    if any(
        row["decision"] == "VERIFIED / EVIDENCE BLOCKED"
        for row in audit["session_review"]
    ):
        reasons.append("Some explicitly verified sessions failed evidence/label checks")
    missing = [
        label
        for label, count in audit["learner_class_distribution"].items()
        if not count
    ]
    if missing:
        reasons.append(
            f"No verified learners for required proficiency classes: {', '.join(missing)}"
        )
    try:
        cohort = prepare_cohort(rows, config)
        split = learner_split(cohort, config)
        split_details = split.details
    except ValueError as error:
        reasons.append(str(error))
        split_details = None
    return {
        "status": "BLOCKED" if reasons else "FEASIBLE EXPERIMENTAL ONLY",
        "reasons": reasons,
        "configuration": config.model_dump(mode="json"),
        "eligible_observations": len(rows),
        "distinct_learners": len({row["student_code"] for row in rows}),
        "learner_class_distribution": audit["learner_class_distribution"],
        "split": split_details,
        "accuracy_or_superiority_claim": "none",
    }


def write_outputs(
    audit: dict,
    review: CollectionReview,
    config,
    destination: Path,
    *,
    train: bool = False,
    data_kind: Literal["real_collected", "synthetic_development"] = "real_collected",
) -> dict:
    """Fresh output only; fitting remains behind explicit authenticity/data gates."""
    ready = feasibility(audit, config)
    destination.mkdir(parents=True, exist_ok=False)

    def save(name: str, value) -> None:
        with (destination / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")

    save("review_input.json", review.model_dump(mode="json"))
    save("experiment_config.json", config.model_dump(mode="json"))
    save("audit.json", audit)
    save(
        "integrity_quarantine.json",
        {
            "schema_version": "game-integrity-quarantine-v1",
            "source_fingerprint": {
                key: audit["source_provenance"].get(key)
                for key in ("source", "file_sha256", "zip_sha256")
            },
            **audit["quarantine"],
        },
    )
    save(
        "invalid_student_code_sessions.json",
        [
            row
            for row in audit["session_review"]
            if row["decision"] == INVALID_CODE_DECISION
        ],
    )
    save("cleaned_observations.json", audit["observations"])
    save("source_links.json", audit["source_links"])
    save("teacher_label_matching.json", audit["label_matching"])
    save(
        "teacher_assessment_provenance.json",
        review.model_dump(
            mode="json",
            exclude={
                "verified_sessions",
                "variant_catalog",
                "variant_catalog_source",
                "variant_catalog_sha256",
            },
        ),
    )
    save("training_feasibility.json", ready)
    for name, rows in audit["features"].items():
        save(f"{name}_features.json", rows)
    with (destination / "session_review.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as stream:
        fields = (
            list(audit["session_review"][0])
            if audit["session_review"]
            else ["session_id", "decision"]
        )
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit["session_review"])
    focused = [
        row
        for row in audit["session_review"]
        if row["student_code"] in COHORT
        or row["session_id"] in DEVELOPMENT_SESSIONS
        or row["decision"] == INVALID_CODE_DECISION
    ]
    lines = [
        "# Exact session review",
        "",
        "Candidate codes require exact verification. STU_0014 is excluded as an invalid code; no reassignment or date-based exclusions.",
        "",
        "| Session ID | Learner | Mode | Completion | Answers | Events | Session summaries | Decision |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in focused:
        lines.append(
            f"| {row['session_id']} | {row['student_code'] or row['student_id_recorded']} | {row['game_mode'] or 'unknown'} | {row['completion']} | {row['answers']} | {row['events']} | {row['session_summaries']} | {row['decision']} |"
        )
    lines += [
        "",
        "The CSV contains every source session, including those outside the requested cohort.",
        "Task summaries are not exported; session summaries are saved Game analytics, never target labels.",
        "",
    ]
    (destination / "session_review.md").write_text("\n".join(lines), encoding="utf-8")
    training = {
        "status": "NOT TRAINED",
        "reason": ready["status"],
        "artifacts": [],
        "offline_inference": "NOT RUN: no real trained model",
    }
    if train and not ready["reasons"]:
        from .research_artifacts import load_research_artifact, save_comparison
        from .research_inference import predict_research
        from .research_training import run_comparison

        comparison = run_comparison(
            audit["observations"],
            config,
            provenance=json.dumps(audit["source_provenance"], sort_keys=True),
            data_kind=data_kind,
        )
        for run in comparison.models.values():
            run.metadata["status"] = "PRELIMINARY_EXPERIMENTAL_NOT_RESEARCH_VALIDATED"
            run.metadata["operational_target_definition"] = (
                "Teacher-assessed Simple Linear Equations proficiency on a separate 10-question assessment after gameplay and lesson revision; represented by mastery_label without changing the existing target contract."
            )
            run.metadata["collection_review"] = review.model_dump(mode="json")
            run.metadata["limitations"].extend(
                [
                    "Very small learner cohort; no reliable accuracy or superiority claim.",
                    "Teacher assessment followed gameplay and a short lesson revision; proficiency is not isolated pre-revision mastery.",
                    "Exact assessment time and historic gameplay content version were not recorded.",
                ]
            )
        comparison.report["status"] = "PRELIMINARY_EXPERIMENTAL_NOT_RESEARCH_VALIDATED"
        comparison.report["interpretation"] = (
            "Descriptive pilot outputs only; no reliable accuracy or superiority conclusion."
        )
        save_comparison(comparison, destination / "experimental_models")
        predictions = {}
        for name in comparison.models:
            loaded = load_research_artifact(
                destination / "experimental_models" / name,
                target=config.target,
                classifier=config.classifier,
                trusted_local_artifact=True,
            )
            predictions[name] = []
            for source in audit["observations"]:
                observation = {
                    **source,
                    "difficulty_label": None,
                    "mastery_label": None,
                }
                predictions[name].append(
                    {
                        "session_id": source["session_id"],
                        **predict_research(loaded, observation),
                    }
                )
        save("offline_predictions.json", predictions)
        training = {
            "status": "PRELIMINARY EXPERIMENTAL",
            "artifacts": list(predictions),
            "offline_inference": "local artifact reload and label-free prediction passed; not independent evaluation",
        }
    save("training_status.json", training)
    return {"output": str(destination.resolve()), **ready, "training": training}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--training-config", type=Path)
    parser.add_argument(
        "--train",
        action="store_true",
        help="Fit only if all approval/evidence/split gates pass",
    )
    args = parser.parse_args()
    from .research_training import ExperimentConfig

    try:
        if args.output.exists():
            raise FileExistsError("Output already exists; choose a new run directory")
        review = CollectionReview.model_validate_json(
            args.review.read_text(encoding="utf-8")
        )
        config = (
            ExperimentConfig.model_validate_json(
                args.training_config.read_text(encoding="utf-8")
            )
            if args.training_config
            else ExperimentConfig(target="mastery", class_labels=CLASSES)
        )
        if (
            config.target != "mastery"
            or config.class_labels != CLASSES
            or config.common_context
        ):
            raise ValueError(
                "Collection target must be teacher-assessed proficiency via mastery_label; exact rubric class order and pure score-only baseline required"
            )
        tables, provenance = read_export(args.export)
        provenance["collection_review_sha256"] = hashlib.sha256(
            json.dumps(
                review.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        audit = audit_collection(tables, provenance, review)
        result = write_outputs(audit, review, config, args.output, train=args.train)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Offline collection preparation failed: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
