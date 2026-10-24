"""Synthetic engineering fixtures only. No real learners, teachers, or database."""

from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app.modules.quiz.research_m3.pipeline import (
    _label_reasons,
    join_validated_record,
    run_pipeline,
)
from app.modules.quiz.research_m3.schema import (
    FORM_VERSION,
    PREDICTOR_COLUMNS,
    SCHEMAS,
    TAXONOMY_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "research" / "quiz_m3"
BASE = datetime(2026, 1, 1, tzinfo=UTC)
SESSION_ID = "QUIZ-00000000-0000-4000-8000-000000000001"
LEARNER = "STU_999999"  # Synthetic engineering identifier, never a real roster record.


def stamp(minutes: int) -> str:
    return (BASE + timedelta(minutes=minutes)).isoformat()


def uid(number: int) -> str:
    return str(UUID(int=number + 1))


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def template(name: str) -> list[dict[str, str]]:
    with (TEMPLATES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fixture(
    tmp_path: Path, *, approve: bool = True
) -> tuple[dict[str, Path], dict[str, list[dict[str, str]]]]:
    """All synthetic fixtures are temporary and cannot qualify as real data."""
    taxonomy = template("00_proposed_taxonomy.csv")
    items = template("01_teacher_assessment_items.csv")
    if approve:
        for row in (*taxonomy, *items):
            row["teacher_review_status"] = "approved"
            row["approval_reference"] = "SYNTHETIC-TEST-ONLY"
    sessions = [
        {
            "source_session_id": uid(1),
            "quiz_session_id": SESSION_ID,
            "student_id_recorded": LEARNER,
            "student_code": LEARNER,
            "concept_id": "linear_equations",
            "learning_cycle_id": uid(2),
            "assessment_phase": "pre_tutor",
            "quiz_attempt_number": "1",
            "status": "completed",
            "assessment_complete": "True",
            "responses_saved": "10",
            "started_at": stamp(0),
            "completed_at": stamp(20),
        }
    ]
    responses = [
        {
            "source_response_id": uid(100 + i),
            "quiz_session_id": SESSION_ID,
            "student_id_recorded": LEARNER,
            "student_code": LEARNER,
            "assessment_phase": "pre_tutor",
            "assessment_complete": "True",
            "question_id": uid(200 + i),
            "question_code": f"DEV-PRE-LE-{i + 1:02d}",
            "question_order": str(i + 1),
            "concept_id": "linear_equations",
            "subconcept_code": "two_step_equations",
            "difficulty_level": ("easy" if i < 4 else "medium" if i < 8 else "hard"),
            "selected_option_id": uid(300 + i),
            "is_correct": "False" if i < 2 else "True",
            "response_time_sec": str(5 + i),
            "confidence_level": ("high" if i < 2 else "medium"),
            "misconception_code": "inverse_operation" if i < 2 else "",
            "answered_at": stamp(2 + i),
            "saved_at": stamp(2 + i),
        }
        for i in range(10)
    ]
    assessment = {
        "assessment_id": "SYNTHETIC-ASMT-1",
        "quiz_session_id": SESSION_ID,
        "student_code": LEARNER,
        "form_version": FORM_VERSION,
        "assessment_started_at": stamp(30),
        "assessment_completed_at": stamp(50),
        "tutoring_status": "not_started",
        "tutoring_started_at": "",
        "no_hints_or_feedback": "true",
        "assessor_code": "SYNTHETIC-ASSESSOR",
        "assessor_blinded_to_quiz": "true",
        "record_origin": "synthetic",
        "research_authorized": "false",
        "authorization_reference": "",
        "consent_evidence_reference": "",
    }
    evidence = [
        {
            "evidence_id": f"SYNTHETIC-E-{item}-{rater}",
            "assessment_id": assessment["assessment_id"],
            "item_id": item,
            "rater_code": rater,
            "recorded_at": stamp(60),
            "working_steps": "x+7=15 then x=22"
            if item.endswith("01")
            else "x-6=9 then x=3",
            "observed_error": "Adds instead of subtracting"
            if item.endswith("01")
            else "Subtracts instead of adding",
            "proposed_category": "M1",
            "verification_status": "verified",
            "evidence_quality": "sufficient",
            "notes": "Synthetic test evidence only",
        }
        for item in ("M3A-I01", "M3A-I02")
        for rater in ("SYNTHETIC-R1", "SYNTHETIC-R2")
    ]
    label = {
        "label_id": "SYNTHETIC-LABEL-1",
        "assessment_id": assessment["assessment_id"],
        "quiz_session_id": SESSION_ID,
        "student_code": LEARNER,
        "form_version": FORM_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "consensus_category": "M1",
        "verification_status": "verified",
        "consensus_method": "agreement",
        "rater_codes": "SYNTHETIC-R1|SYNTHETIC-R2",
        "disagreement_flag": "false",
        "evidence_ids": "|".join(row["evidence_id"] for row in evidence),
        "resolution_note": "",
        "verified_by_code": "SYNTHETIC-REVIEWER",
        "verified_at": stamp(70),
    }
    tables = {
        "taxonomy": taxonomy,
        "items": items,
        "assessments": [assessment],
        "evidence": evidence,
        "labels": [label],
        "quiz_sessions": sessions,
        "quiz_responses": responses,
    }
    filenames = {
        "taxonomy": "00_proposed_taxonomy.csv",
        "items": "01_teacher_assessment_items.csv",
        "assessments": "02_teacher_assessment_sessions.csv",
        "evidence": "03_teacher_item_evidence.csv",
        "labels": "04_teacher_consensus_labels.csv",
        "quiz_sessions": "quiz_sessions.csv",
        "quiz_responses": "quiz_responses.csv",
    }
    source_cols = {
        "quiz_sessions": tuple(sessions[0]),
        "quiz_responses": tuple(responses[0]),
    }
    paths = {key: tmp_path / name for key, name in filenames.items()}
    for key, path in paths.items():
        columns = (
            SCHEMAS[filenames[key]].columns
            if key not in source_cols
            else source_cols[key]
        )
        write_csv(path, columns, tables[key])
    return paths, tables


def run(tmp_path: Path, mutate=None, *, approve=True):
    paths, tables = fixture(tmp_path, approve=approve)
    if mutate:
        mutate(tables)
        for key in (
            "quiz_sessions",
            "quiz_responses",
            "assessments",
            "evidence",
            "labels",
        ):
            columns = (
                tuple(tables[key][0])
                if tables[key]
                else SCHEMAS[paths[key].name].columns
            )
            write_csv(paths[key], columns, tables[key])
    out = tmp_path / "output"
    report = run_pipeline(paths, out)
    return report, out, tables


def test_schema_headers_and_proposed_state():
    for name, schema in SCHEMAS.items():
        with (TEMPLATES / name).open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        assert tuple(reader.fieldnames) == schema.columns
        assert all(set(row) == set(schema.columns) for row in rows)
    assert {row["category_code"] for row in template("00_proposed_taxonomy.csv")} == {
        "M0",
        "M1",
        "M2",
        "M3",
        "M4",
        "REVIEW",
    }
    assert all(
        row["teacher_review_status"] == "pending"
        for row in template("01_teacher_assessment_items.csv")
    )


def test_independent_blueprint_uses_different_equations_from_live_prototype():
    bank = json.loads(
        (ROOT / "backend" / "scripts" / "quiz_pre_prototype.json").read_text(
            encoding="utf-8"
        )
    )

    def equation(text: str) -> str:
        return re.sub(r"\s+", "", text.split("Solve ", 1)[1].split(".", 1)[0])

    original = {equation(row["text_en"]) for row in bank["questions"]}
    proposed = {
        equation(row["prompt_en"])
        for row in template("01_teacher_assessment_items.csv")
    }
    assert len(proposed) == 8
    assert proposed.isdisjoint(original)


def test_synthetic_records_never_become_training_rows(tmp_path):
    report, out, _ = run(tmp_path)
    assert report["valid_quiz_feature_rows"] == 1
    assert report["eligible_training_records"] == 0
    assert report["readiness"] == "NOT TRAINING READY"
    assert report["quarantine_reason_counts"]["not_verified_real_record"] == 1
    assert report["eligible_class_distribution"] == {
        code: 0 for code in ("M0", "M1", "M2", "M3", "M4")
    }
    with (out / "05_quiz_ml_features.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        feature = next(csv.DictReader(handle))
    assert feature["option_inverse_operation_count"] == "2"
    assert feature["high_confidence_wrong_count"] == "2"
    assert "teacher_category" not in feature and "assessment_id" not in feature
    assert (
        "student_code" not in PREDICTOR_COLUMNS
        and "quiz_session_id" not in PREDICTOR_COLUMNS
    )


def test_development_test_records_never_become_training_rows(tmp_path):
    report, _, _ = run(
        tmp_path, lambda t: t["assessments"][0].update(record_origin="development_test")
    )
    assert report["eligible_training_records"] == 0
    assert report["quarantine_reason_counts"]["not_verified_real_record"] == 1
    assert report["verified_real_teacher_label_count"] == 0


def test_verified_independent_join_logic_with_synthetic_fixture(tmp_path):
    report, out, tables = run(tmp_path)
    with (out / "05_quiz_ml_features.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        feature = next(csv.DictReader(handle))
    assessment, label = tables["assessments"][0], tables["labels"][0]
    assert (
        _label_reasons(
            label,
            assessment,
            tables["evidence"],
            {row["item_id"]: row for row in tables["items"]},
            True,
        )
        == set()
    )
    joined = join_validated_record(feature, assessment, label)
    assert joined["teacher_category"] == "M1"
    assert joined["assessment_id"] == assessment["assessment_id"]
    assert joined["option_inverse_operation_count"] == "2"
    assert (
        report["eligible_training_records"] == 0
    )  # Synthetic origin still blocks output.


def test_disagreement_requires_explicit_independent_adjudication(tmp_path):
    _, _, tables = run(tmp_path)
    assessment, label = tables["assessments"][0], tables["labels"][0]
    evidence = deepcopy(tables["evidence"])
    evidence[0]["proposed_category"] = "M3"
    items = {row["item_id"]: row for row in tables["items"]}
    assert "unresolved_competing_teacher_labels" in _label_reasons(
        label, assessment, evidence, items, True
    )
    label = {
        **label,
        "disagreement_flag": "true",
        "consensus_method": "adjudicated",
        "resolution_note": "SYNTHETIC adjudicator reviewed the working steps",
    }
    assert _label_reasons(label, assessment, evidence, items, True) == set()
    label["verified_by_code"] = "SYNTHETIC-R1"
    assert "unresolved_competing_teacher_labels" in _label_reasons(
        label, assessment, evidence, items, True
    )


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (
            lambda t: t["quiz_sessions"].append(deepcopy(t["quiz_sessions"][0])),
            "duplicate_or_missing_quiz_session_id",
        ),
        (
            lambda t: t["quiz_responses"][1].update(
                source_response_id=t["quiz_responses"][0]["source_response_id"]
            ),
            "duplicate_or_missing_source_response_id",
        ),
        (
            lambda t: t["quiz_responses"][1].update(misconception_code="M1"),
            "invalid_quiz_response_value",
        ),
        (
            lambda t: t["quiz_responses"][1].update(assessment_phase="post_tutor"),
            "quiz_response_identity_conflict",
        ),
        (
            lambda t: t["quiz_sessions"][0].update(assessment_phase="post_tutor"),
            "not_pre_tutor_linear_equations",
        ),
        (
            lambda t: t["quiz_sessions"][0].update(student_code="STU_888888"),
            "invalid_or_conflicting_quiz_student_code",
        ),
    ],
)
def test_invalid_quiz_source_quarantined(tmp_path, mutation, reason):
    report, _, _ = run(tmp_path, mutation)
    assert report["valid_quiz_feature_rows"] == 0
    assert report["source_quiz_issue_counts"][reason] >= 1


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (
            lambda t: t["assessments"][0].update(student_code="STU_888888"),
            "assessment_quiz_student_conflict",
        ),
        (
            lambda t: t["assessments"][0].update(assessment_started_at=stamp(10)),
            "assessment_not_after_completed_quiz",
        ),
        (
            lambda t: t["assessments"][0].update(
                tutoring_status="started", tutoring_started_at=stamp(40)
            ),
            "assessment_not_before_tutoring",
        ),
        (
            lambda t: t["assessments"][0].update(no_hints_or_feedback="false"),
            "assessment_hints_or_feedback_unknown_or_present",
        ),
        (
            lambda t: t["assessments"][0].update(form_version="wrong"),
            "assessment_form_not_approved_or_version_mismatch",
        ),
        (
            lambda t: t["labels"][0].update(verification_status="pending"),
            "teacher_label_unverified",
        ),
        (
            lambda t: t["evidence"][0].update(working_steps=""),
            "evidence_unverified_or_insufficient",
        ),
        (
            lambda t: t["evidence"][1].update(proposed_category="M3"),
            "unresolved_competing_teacher_labels",
        ),
        (
            lambda t: t["labels"][0].update(consensus_category="inverse_operation"),
            "invalid_or_review_only_teacher_target",
        ),
        (
            lambda t: t["labels"][0].update(evidence_ids="SYNTHETIC-NONEXISTENT"),
            "evidence_link_missing_or_cross_assessment",
        ),
    ],
)
def test_assessment_and_label_problems_quarantined(tmp_path, mutation, reason):
    report, _, _ = run(tmp_path, mutation)
    assert report["eligible_training_records"] == 0
    assert report["quarantine_reason_counts"][reason] >= 1


def test_unapproved_artifacts_and_duplicate_assessment(tmp_path):
    report, _, _ = run(
        tmp_path,
        lambda t: t["assessments"].append(deepcopy(t["assessments"][0])),
        approve=False,
    )
    assert (
        report["quarantine_reason_counts"][
            "assessment_form_not_approved_or_version_mismatch"
        ]
        >= 1
    )
    assert report["quarantine_reason_counts"]["duplicate_or_missing_assessment_id"] >= 1
    assert report["quarantine_reason_counts"]["taxonomy_not_teacher_approved"] >= 1


def test_missing_schema_and_no_overwrite(tmp_path):
    paths, _ = fixture(tmp_path)
    paths["evidence"].write_text("wrong_header\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid columns"):
        run_pipeline(paths, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    paths, _ = fixture(tmp_path)
    (tmp_path / "output").mkdir()
    with pytest.raises(ValueError, match="already exists"):
        run_pipeline(paths, tmp_path / "output")
