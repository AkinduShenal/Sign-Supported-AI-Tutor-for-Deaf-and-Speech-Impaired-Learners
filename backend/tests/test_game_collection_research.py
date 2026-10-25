"""Invented engineering fixtures only. No real learner data or research results."""

import copy
import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from app.modules.game.ml.collection_research import (
    CLASSES,
    COHORT,
    DEVELOPMENT_SESSIONS,
    INVALID_CODE_DECISION,
    INTEGRITY_QUARANTINE_DECISION,
    TABLES,
    CollectionReview,
    audit_collection,
    feasibility,
    prepare_session,
    proficiency,
    read_export,
    write_outputs,
)
from app.modules.game.ml.research_dataset import extract_research_features
from app.modules.game.ml.research_schema import IndependentLabel, ResearchObservation
from app.modules.game.ml.research_training import ExperimentConfig


@pytest.fixture
def fixture():
    """SYNTHETIC source records using the required code syntax, never real data."""
    tables = {name: [] for name in TABLES}
    catalog = {}
    for index in range(6):
        catalog[f"SYNTHETIC-task-{index}"] = {
            "activity_id": f"SYNTHETIC-activity-{index}",
            "difficulty": ("easy", "medium", "hard")[index // 2],
            "expected_operations": ["+1"],
            "final_answer": "2",
        }
    verified = {}
    for number, mode in ((6, "drag_drop"), (7, "hangman")):
        sid, code = f"SYNTHETIC-session-{number}", f"STU_{number:03}"
        session = {
            "game_session_id": sid,
            "source_session_uuid": f"SYNTHETIC-uuid-{number}",
            "student_id_recorded": code,
            "student_code": code,
            "concept_id": "linear_equations",
            "learning_cycle_id": f"SYNTHETIC-cycle-{number}",
            "assessment_phase": "pre_tutor",
            "game_type": mode,
            "status": "completed",
            "started_at": "2026-10-15T09:00:00+00:00",
            "completed_at": "2026-10-15T09:02:00+00:00",
            "recording_protocol": "game-evidence-v1",
            "saved_assessment_complete": "True",
        }
        tables["game_sessions"].append(session)
        verified[sid] = {
            "student_code": code,
            "concept": "linear_equations",
            "game_type": mode,
            "source_reference": "SYNTHETIC authenticity review",
        }

        def event(kind, task="", step="", number="", second=0):
            identity = f"SYNTHETIC-event-{len(tables['game_events'])}"
            row = {
                "source_event_id": identity,
                "client_event_id": identity + "-client",
                "game_session_id": sid,
                "student_id_recorded": code,
                "event_type": kind,
                "task_id": task,
                "step_index": step,
                "attempt_number": number,
                "event_timestamp": (
                    datetime(2026, 10, 15, 9, tzinfo=UTC) + timedelta(seconds=second)
                ).isoformat(),
            }
            tables["game_events"].append(row)
            return row

        event("GAME_STARTED")
        for index, (task, variant) in enumerate(catalog.items()):
            step = "" if mode == "hangman" else "0"
            event("QUESTION_SHOWN", task, step, second=index * 10 + 1)
            event("ANSWER_SUBMITTED", task, step, "1", index * 10 + 2)
            outcome = event("ANSWER_CORRECT", task, step, "1", index * 10 + 3)
            answer = {
                **session,
                **outcome,
                "variant_id": task,
                "activity_id": variant["activity_id"],
                "difficulty_level": variant["difficulty"],
                "answer_type": "final_value"
                if mode == "hangman"
                else "equation_operation",
                "expected_response": "2" if mode == "hangman" else "+1",
                "submitted_answer": "2" if mode == "hangman" else "+1",
                "is_correct": "True",
                "hints_before_attempt": "0",
                "first_attempt_correct": "True",
                "content_version": "",
            }
            tables["student_answers"].append(answer)
            event("TASK_COMPLETED", task, step, second=index * 10 + 4)
        event("GAME_COMPLETED", second=115)
        tables["game_analytics"].append(
            {
                **session,
                "source_result_id": f"SYNTHETIC-result-{number}",
                "tasks_total": "6",
                "tasks_attempted": "6",
                "tasks_completed": "6",
                "successful_tasks": "6",
                "wrong_attempt_count": "0",
                "retry_count": "0",
                "total_hint_count": "0",
            }
        )
    review = CollectionReview.model_validate_json(
        json.dumps(
            {
                "verified_sessions": verified,
                "teacher_scores": {"STU_006": 7, "STU_007": 4},
                "assessed_on": "2026-10-15",
                "revision_description": "SYNTHETIC lesson revision provenance",
                "teacher_source_reference": "SYNTHETIC independent teacher report",
                "rubric_version": "SYNTHETIC beginner0-4_intermediate5-7_advanced8-10",
                "variant_catalog_source": "SYNTHETIC frozen catalog",
                "variant_catalog_sha256": "0" * 64,
                "variant_catalog": catalog,
            }
        )
    )
    provenance = {
        "manifest": {
            "counts": {
                "game_sessions": 2,
                "student_answers": 12,
                "source_gameplay_events": 52,
                "game_analytics": 2,
            }
        }
    }
    return tables, provenance, review


def audit(fixture):
    return audit_collection(*fixture)


def test_date_only_label_roundtrip_and_legacy_phase_meaning(fixture):
    result = audit(fixture)
    assert len(result["observations"]) == 2
    for source in result["observations"]:
        row = ResearchObservation.model_validate_json(json.dumps(source))
        label = row.mastery_label
        assert label.assessed_at is None
        assert label.assessed_on.isoformat() == "2026-10-15"
        assert label.assessment_timing == "after_gameplay"
        assert label.assessment_phase == row.assessment_phase == "pre_tutor"
        assert label.revision_before_assessment


@pytest.mark.parametrize(
    "change",
    [
        {"assessed_at": None, "assessed_on": None},
        {"assessed_at": "2026-10-15T12:00:00"},
        {"assessed_at": "2026-10-16T12:00:00+05:30"},
        {"assessment_score": 11},
        {"assessment_max_score": None},
        {"revision_description": None},
    ],
)
def test_invalid_label_provenance_rejected(fixture, change):
    label = audit(fixture)["observations"][0]["mastery_label"]
    with pytest.raises(ValidationError):
        IndependentLabel.model_validate_json(json.dumps({**label, **change}))


def test_exact_exclusions_never_use_date_or_prefix(fixture):
    tables, provenance, review = fixture
    for sid in [
        *sorted(DEVELOPMENT_SESSIONS),
        "GAME-SES-2026-004",
        "SYNTHETIC-other-same-day",
    ]:
        tables["game_sessions"].append(
            {
                **tables["game_sessions"][0],
                "game_session_id": sid,
                "source_session_uuid": f"SYNTHETIC-extra-uuid-{sid}",
                "student_code": "STU_001",
                "student_id_recorded": "STU_001",
            }
        )
    provenance["manifest"]["counts"]["game_sessions"] = len(tables["game_sessions"])
    result = audit(fixture)
    decisions = {row["session_id"]: row["decision"] for row in result["session_review"]}
    assert all(decisions[sid] == "EXCLUDED DEVELOPMENT" for sid in DEVELOPMENT_SESSIONS)
    assert decisions["GAME-SES-2026-004"] == "REVIEW REQUIRED"
    assert decisions["SYNTHETIC-other-same-day"] == "REVIEW REQUIRED"
    assert len(result["observations"]) == 2


def test_unverified_sessions_and_unlabelled_students_not_included(fixture):
    tables, provenance, review = fixture
    review.verified_sessions.pop("SYNTHETIC-session-7")
    assert len(audit(fixture)["observations"]) == 1
    review.teacher_scores.clear()
    assert not audit(fixture)["observations"]


@pytest.mark.parametrize("code", ["STU_008", "STU_014", "STU_016", "STU_017"])
def test_expanded_roster_still_requires_exact_verification_and_label(fixture, code):
    tables, _, review = fixture
    sid = "SYNTHETIC-session-6"
    for rows in tables.values():
        for row in rows:
            if row["game_session_id"] == sid:
                row["student_id_recorded"] = code
                if "student_code" in row:
                    row["student_code"] = code
    approval = review.verified_sessions.pop(sid)
    approval.student_code = code
    assert len(audit(fixture)["observations"]) == 1
    review.verified_sessions[sid] = approval
    assert len(audit(fixture)["observations"]) == 1  # No invented teacher label.
    review.teacher_scores[code] = 7  # Explicit SYNTHETIC assessment fixture only.
    result = audit(fixture)
    assert COHORT == {f"STU_{number:03}" for number in range(1, 17)}
    assert len(result["observations"]) == (2 if code in COHORT else 1)


@pytest.mark.parametrize(
    "projected_code,approved",
    [("STU_0014", False), ("STU_0014", True), ("STU_014", True)],
)
def test_completed_invalid_student_code_never_enters_models(
    fixture, tmp_path, projected_code, approved
):
    tables, _, review = fixture
    sid = "SYNTHETIC-session-6"
    for rows in tables.values():
        for row in rows:
            if row["game_session_id"] == sid:
                row["student_id_recorded"] = "STU_0014"
                if "student_code" in row:
                    row["student_code"] = projected_code
    review.verified_sessions[sid].student_code = projected_code
    review.teacher_scores[projected_code] = 7  # Even a label cannot override exclusion.
    if not approved:
        review.verified_sessions.pop(sid)
    before = copy.deepcopy(tables)
    result = audit(fixture)
    excluded = next(row for row in result["session_review"] if row["session_id"] == sid)
    assert excluded["completion"] == "completed"
    assert excluded["decision"] == INVALID_CODE_DECISION
    assert result["summary"]["candidate_learners_present"] == 1
    assert result["summary"]["target_completed_sessions"] == 1
    assert result["summary"]["eligible_learners"] == 1
    assert result["summary"]["eligible_sessions"] == 1
    assert result["summary"]["invalid_student_code_completed_sessions"] == 1
    assert result["summary"]["eligible_sessions_per_learner"]["STU_014"] == 0
    for rows in [result["observations"], *result["features"].values()]:
        assert all(row["session_id"] != sid for row in rows)
    with pytest.raises(ValueError, match="accidental student-code"):
        prepare_session(tables["game_sessions"][0], [], [], [], review)
    output = tmp_path / "SYNTHETIC-invalid-code-preparation"
    status = write_outputs(
        result, review, ExperimentConfig(target="mastery", class_labels=CLASSES), output
    )
    assert status["training"]["status"] == "NOT TRAINED"
    assert not list(output.rglob("*.joblib"))
    assert json.loads((output / "invalid_student_code_sessions.json").read_text()) == [
        excluded
    ]
    assert tables == before


def test_invalid_code_completion_counts_are_separate_from_candidate_counts(fixture):
    tables, provenance, _ = fixture
    for index, status in enumerate(("completed", "in_progress")):
        tables["game_sessions"].append(
            {
                **tables["game_sessions"][0],
                "game_session_id": f"SYNTHETIC-invalid-{index}",
                "source_session_uuid": f"SYNTHETIC-invalid-uuid-{index}",
                "student_code": "STU_0014",
                "student_id_recorded": "STU_0014",
                "status": status,
            }
        )
    provenance["manifest"]["counts"]["game_sessions"] = 4
    summary = audit(fixture)["summary"]
    assert summary["target_learner_sessions"] == summary["target_completed_sessions"] == 2
    assert summary["target_incomplete_sessions"] == 0
    assert summary["invalid_student_code_sessions"] == 2
    assert summary["invalid_student_code_completed_sessions"] == 1
    assert summary["invalid_student_code_incomplete_sessions"] == 1


def test_linkage_and_duplicate_evidence_fail_closed(fixture):
    tables, _, _ = fixture
    tables["student_answers"][0]["student_id_recorded"] = "STU_001"
    assert not audit(fixture)["observations"]
    tables["student_answers"][0]["student_id_recorded"] = "STU_006"
    tables["student_answers"].append(copy.deepcopy(tables["student_answers"][0]))
    result = audit(fixture)
    assert not result["observations"]
    assert result["source_checks"]["student_answers"]["duplicate_source_ids"] == 1


def test_analytics_ownership_quarantine_preserves_evidence_and_approved_cohort(
    fixture, tmp_path
):
    tables, _, review = fixture
    tables["game_analytics"][0].update(
        student_id_recorded="STU_007", student_code="STU_007"
    )
    before = copy.deepcopy(tables)
    approvals = review.model_dump(mode="json")
    result = audit(fixture)
    assert result["global_issues"] == []
    assert result["source_checks"]["game_analytics"]["recorded_learner_mismatches"] == 1
    assert result["quarantine"]["session_boundaries_established"]
    assert result["quarantine"]["session_ids"] == ["SYNTHETIC-session-6"]
    quarantined = result["quarantine"]["records"][0]
    for table, rows in before.items():
        assert quarantined["original_evidence"][table] == [
            row for row in rows if row["game_session_id"] == "SYNTHETIC-session-6"
        ]
    assert quarantined["issues"][0]["source_result_id"] == "SYNTHETIC-result-6"
    assert quarantined["issues"][0]["field_disagreements"] == {
        "student_id_recorded": {"parent": "STU_006", "analytics": "STU_007"},
        "student_code": {"parent": "STU_006", "analytics": "STU_007"},
    }
    assert [row["session_id"] for row in result["observations"]] == ["SYNTHETIC-session-7"]
    for rows in result["features"].values():
        assert [row["session_id"] for row in rows] == ["SYNTHETIC-session-7"]
    assert next(
        row for row in result["session_review"] if row["session_id"] == "SYNTHETIC-session-6"
    )["decision"] == INTEGRITY_QUARANTINE_DECISION
    output = tmp_path / "SYNTHETIC-quarantine"
    write_outputs(
        result, review, ExperimentConfig(target="mastery", class_labels=CLASSES), output
    )
    saved = json.loads((output / "integrity_quarantine.json").read_text())
    assert saved["records"] == result["quarantine"]["records"]
    assert not list(output.rglob("*.joblib"))
    assert tables == before
    assert review.model_dump(mode="json") == approvals


@pytest.mark.parametrize("failure", ["unverified", "missing_label", "bad_evidence"])
def test_unaffected_sessions_still_require_all_research_checks(fixture, failure):
    tables, _, review = fixture
    tables["game_analytics"][0]["student_id_recorded"] = "STU_007"
    if failure == "unverified":
        review.verified_sessions.pop("SYNTHETIC-session-7")
    elif failure == "missing_label":
        review.teacher_scores.pop("STU_007")
    else:
        tables["student_answers"][-1]["expected_response"] = "SYNTHETIC-wrong-answer"
    result = audit(fixture)
    assert result["quarantine"]["session_ids"] == ["SYNTHETIC-session-6"]
    assert result["observations"] == []


@pytest.mark.parametrize(
    "failure",
    ["duplicate_id", "duplicate_client", "missing_id", "duplicate_parent_uuid",
     "missing_parent_uuid", "orphan", "projection", "manifest", "multiple_results"],
)
def test_shared_corruption_never_becomes_a_local_quarantine(fixture, failure):
    tables, provenance, _ = fixture
    tables["game_analytics"][0]["student_id_recorded"] = "STU_007"
    if failure == "duplicate_id":
        tables["game_events"].append(copy.deepcopy(tables["game_events"][0]))
        provenance["manifest"]["counts"]["source_gameplay_events"] += 1
    elif failure == "duplicate_client":
        tables["game_events"][-1]["client_event_id"] = tables["game_events"][0]["client_event_id"]
    elif failure == "missing_id":
        tables["game_analytics"][0]["source_result_id"] = ""
    elif failure == "duplicate_parent_uuid":
        tables["game_sessions"][1]["source_session_uuid"] = tables["game_sessions"][0]["source_session_uuid"]
    elif failure == "missing_parent_uuid":
        tables["game_sessions"][0]["source_session_uuid"] = ""
    elif failure == "orphan":
        tables["game_analytics"][0]["game_session_id"] = "SYNTHETIC-no-parent"
    elif failure == "projection":
        tables["student_answers"][0]["client_event_id"] = "SYNTHETIC-projection-conflict"
    elif failure == "manifest":
        provenance["manifest"]["counts"]["game_sessions"] += 1
    else:
        tables["game_analytics"].append({
            **tables["game_analytics"][0], "source_result_id": "SYNTHETIC-second-result"
        })
        provenance["manifest"]["counts"]["game_analytics"] += 1
    result = audit(fixture)
    assert result["global_issues"]
    assert not result["quarantine"]["session_boundaries_established"]
    assert result["quarantine"]["session_ids"] == []
    assert result["observations"] == []


def test_invalid_code_and_integrity_exclusions_overlap_without_reassignment(fixture):
    tables, _, _ = fixture
    for rows in tables.values():
        for row in rows:
            if row["game_session_id"] == "SYNTHETIC-session-6":
                row["student_id_recorded"] = "STU_0014"
                if "student_code" in row:
                    row["student_code"] = "STU_0014"
    tables["game_analytics"][0].update(student_id_recorded="STU_014", student_code="STU_014")
    before = copy.deepcopy(tables)
    result = audit(fixture)
    excluded = next(row for row in result["session_review"] if row["session_id"] == "SYNTHETIC-session-6")
    assert excluded["decision"] == INVALID_CODE_DECISION
    assert excluded["integrity_quarantined"]
    assert result["summary"]["integrity_quarantined_and_invalid_code_sessions"] == 1
    assert len(result["observations"]) == 1
    assert tables == before


def test_quarantine_does_not_exclude_another_session_with_the_conflicting_code(fixture):
    tables, _, review = fixture
    # The conflict mentions STU_014, but a separately approved STU_014 session
    # still owns its distinct source IDs. Do not quarantine by learner name.
    for rows in tables.values():
        for row in rows:
            if row["game_session_id"] == "SYNTHETIC-session-7":
                row["student_id_recorded"] = "STU_014"
                if "student_code" in row:
                    row["student_code"] = "STU_014"
    review.verified_sessions["SYNTHETIC-session-7"].student_code = "STU_014"
    review.teacher_scores["STU_014"] = 4  # Explicit SYNTHETIC label only.
    tables["game_analytics"][0].update(student_id_recorded="STU_014", student_code="STU_014")
    result = audit(fixture)
    assert result["quarantine"]["session_ids"] == ["SYNTHETIC-session-6"]
    assert [(row["student_code"], row["session_id"]) for row in result["observations"]] == [
        ("STU_014", "SYNTHETIC-session-7")
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("first_attempt_correct", "False"),
        ("attempt_number", "2"),
        ("hints_before_attempt", "1"),
        ("activity_id", "wrong"),
        ("expected_response", "wrong"),
    ],
)
def test_inconsistent_feature_evidence_blocks_session(fixture, field, value):
    tables, _, _ = fixture
    tables["student_answers"][0][field] = value
    if field == "attempt_number":
        source_id = tables["student_answers"][0]["source_event_id"]
        next(
            row for row in tables["game_events"] if row["source_event_id"] == source_id
        )[field] = value
    result = audit(fixture)
    assert len(result["observations"]) == 1
    assert any(
        row["decision"] == "VERIFIED / EVIDENCE BLOCKED"
        for row in result["session_review"]
    )


def test_score_features_missing_timing_and_leakage_prevention(fixture):
    result = audit(fixture)
    assert result["learner_class_distribution"] == {
        "beginner": 1,
        "intermediate": 1,
        "advanced": 0,
    }
    assert result["feature_definitions"]["score_only"] == ["gameplay_score"]
    assert len(result["feature_definitions"]["score_plus_behaviour"]) == 13
    for source in result["observations"]:
        row = ResearchObservation.model_validate_json(json.dumps(source))
        assert row.gameplay_score == 1.0
        assert row.task_duration_seconds is None and not row.task_duration_reliable
        values = extract_research_features(row).values
        assert values["task_duration_seconds"] is None
        assert (
            not {
                "assessment_score",
                "value",
                "assessed_on",
                "revision_before_assessment",
                "student_code",
                "session_id",
            }
            & values.keys()
        )
        source["mastery_label"]["assessment_score"] = 0
        assert (
            extract_research_features(
                ResearchObservation.model_validate_json(json.dumps(source))
            ).values
            == values
        )
    assert [
        (r["student_code"], r["session_id"]) for r in result["features"]["score_only"]
    ] == [
        (r["student_code"], r["session_id"])
        for r in result["features"]["score_plus_behaviour"]
    ]


def test_impossible_training_does_not_create_models(fixture, tmp_path):
    result = audit(fixture)
    config = ExperimentConfig(target="mastery", class_labels=CLASSES)
    ready = feasibility(result, config)
    assert ready["status"] == "BLOCKED"
    assert any("advanced" in reason for reason in ready["reasons"])
    assert any("too small" in reason for reason in ready["reasons"])
    output = tmp_path / "SYNTHETIC-preparation"
    status = write_outputs(result, fixture[2], config, output, train=True)
    assert status["training"]["status"] == "NOT TRAINED"
    assert not (output / "experimental_models").exists()
    with pytest.raises(FileExistsError):
        write_outputs(result, fixture[2], config, output)


def test_zip_and_directory_reading_preserves_source(fixture, tmp_path):
    tables, provenance, _ = fixture
    archive_path = tmp_path / "SYNTHETIC-export.zip"
    directory = tmp_path / "SYNTHETIC-csv"
    directory.mkdir()
    with ZipFile(archive_path, "w") as archive:
        for table, fields in TABLES.items():
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(tables[table])
            data = stream.getvalue().encode("utf-8-sig")
            archive.writestr(f"{table}.csv", data)
            (directory / f"{table}.csv").write_bytes(data)
        manifest = json.dumps(provenance["manifest"]).encode()
        archive.writestr("manifest.json", manifest)
        (directory / "manifest.json").write_bytes(manifest)
    before = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    zipped, meta = read_export(archive_path)
    unpacked, _ = read_export(directory)
    assert zipped == unpacked
    assert (
        meta["zip_sha256"]
        == before
        == hashlib.sha256(archive_path.read_bytes()).hexdigest()
    )


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "beginner"),
        (4, "beginner"),
        (5, "intermediate"),
        (7, "intermediate"),
        (8, "advanced"),
        (10, "advanced"),
    ],
)
def test_teacher_rubric_boundaries(score, expected):
    assert proficiency(score) == expected


def test_unknown_attempt_numbers_are_unavailable_not_duplicates(fixture):
    tables, provenance, _ = fixture
    for index in range(2):
        row = {
            **tables["student_answers"][0],
            "source_event_id": f"SYNTHETIC-legacy-{index}",
            "client_event_id": f"SYNTHETIC-legacy-client-{index}",
            "attempt_number": "",
        }
        tables["student_answers"].append(row)
        tables["game_events"].append({**row, "event_type": "ANSWER_CORRECT"})
    provenance["manifest"]["counts"]["student_answers"] += 2
    provenance["manifest"]["counts"]["source_gameplay_events"] += 2
    result = audit(fixture)
    assert result["source_checks"]["student_answers"]["duplicate_attempt_keys"] == 0
    assert (
        result["source_checks"]["student_answers"][
            "logical_attempt_identity_unavailable"
        ]
        == 2
    )
    # Incomplete numbered coverage still blocks that session; never invent it.
    assert len(result["observations"]) == 1


def test_drag_completion_events_are_per_operation_step(fixture):
    tables, provenance, review = fixture
    task = "SYNTHETIC-task-0"
    review.variant_catalog[task].expected_operations.append("/2")
    source_answer = tables["student_answers"][0]
    for index, kind in enumerate(
        ("QUESTION_SHOWN", "ANSWER_SUBMITTED", "ANSWER_CORRECT", "TASK_COMPLETED")
    ):
        event = {
            **tables["game_events"][2],
            "source_event_id": f"SYNTHETIC-extra-step-{index}",
            "client_event_id": f"SYNTHETIC-extra-step-client-{index}",
            "event_type": kind,
            "step_index": "1",
            "attempt_number": "1" if kind.startswith("ANSWER") else "",
            "event_timestamp": f"2026-10-15T09:00:0{5 + index}+00:00",
        }
        tables["game_events"].append(event)
        if kind == "ANSWER_CORRECT":
            tables["student_answers"].append(
                {
                    **source_answer,
                    **event,
                    "expected_response": "/2",
                    "submitted_answer": "/2",
                }
            )
    provenance["manifest"]["counts"]["student_answers"] += 1
    provenance["manifest"]["counts"]["source_gameplay_events"] += 4
    rows = audit(fixture)["observations"]
    assert len(rows) == 2
    drag = next(row for row in rows if row["game_type"] == "drag_drop")
    assert drag["total_steps"] == 7 and drag["tasks_completed"] == 6


@pytest.mark.parametrize(
    "classifier", ["logistic_regression", "decision_tree", "random_forest"]
)
def test_experimental_artifact_reload_and_label_free_predictions(
    fixture, tmp_path, classifier
):
    """Six invented learners solely to verify the gated artifact lifecycle."""
    from app.modules.game.ml.research_training import EvaluationConfig

    tables, provenance, review = fixture
    invented = {name: [] for name in TABLES}
    review.verified_sessions.clear()
    review.teacher_scores.clear()
    # Fixed synthetic class layout gives all classes in both seed-42 partitions.
    for number, score in enumerate((2, 6, 2, 6, 9, 9), start=1):
        sid, code = f"SYNTHETIC-artifact-session-{number}", f"STU_{number:03}"
        for name, rows in tables.items():
            for source in rows:
                if source["game_session_id"] != "SYNTHETIC-session-6":
                    continue
                row = {**source, "game_session_id": sid, "student_id_recorded": code}
                if "student_code" in row:
                    row["student_code"] = code
                for key in (
                    "source_event_id",
                    "client_event_id",
                    "source_result_id",
                    "source_session_uuid",
                ):
                    if key in row:
                        row[key] += f"-learner-{number}"
                invented[name].append(row)
        # Validate via JSON just as an explicit review file is read by the CLI.
        review.teacher_scores[code] = score
    review_data = review.model_dump(mode="json")
    review_data["verified_sessions"] = {
        f"SYNTHETIC-artifact-session-{number}": {
            "student_code": f"STU_{number:03}",
            "concept": "linear_equations",
            "game_type": "drag_drop",
            "source_reference": "SYNTHETIC authenticity fixture",
        }
        for number in range(1, 7)
    }
    reviewed = CollectionReview.model_validate_json(json.dumps(review_data))
    provenance["manifest"]["counts"] = {
        "game_sessions": 6,
        "student_answers": 36,
        "source_gameplay_events": 156,
        "game_analytics": 6,
    }
    result = audit_collection(invented, provenance, reviewed)
    assert len(result["observations"]) == 6
    config = ExperimentConfig(
        target="mastery",
        class_labels=CLASSES,
        classifier=classifier,
        evaluation=EvaluationConfig(min_examples=4, min_learners=6, test_size=0.5),
    )
    output = tmp_path / "SYNTHETIC-artifacts"
    status = write_outputs(
        result, reviewed, config, output, train=True, data_kind="synthetic_development"
    )
    assert status["training"]["status"] == "PRELIMINARY EXPERIMENTAL"
    predictions = json.loads((output / "offline_predictions.json").read_text())
    for name in ("score_only", "score_plus_behaviour"):
        assert len(predictions[name]) == 6
        metadata = json.loads(
            (output / "experimental_models" / name / "metadata.json").read_text()
        )
        assert metadata["status"] == "PRELIMINARY_EXPERIMENTAL_NOT_RESEARCH_VALIDATED"
        assert metadata["training_data"]["kind"] == "synthetic_development"
        assert metadata["label_provenance"][0]["assessed_at"] is None
        assert metadata["label_provenance"][0]["assessed_on"] == "2026-10-15"
        assert metadata["split"]["train_test_learner_overlap"] == 0
