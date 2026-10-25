"""Fail-closed, local-CSV-only M3-A feature extraction and teacher-label join."""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from .schema import (
    CATEGORIES,
    FORM_VERSION,
    OPTION_TAGS,
    ORIGINS,
    PREDICTOR_COLUMNS,
    SCHEMAS,
    SOURCE_RESPONSE_COLUMNS,
    SOURCE_SESSION_COLUMNS,
    TARGET_CATEGORIES,
    TAXONOMY_VERSION,
)

STUDENT_CODE = re.compile(r"STU_[0-9]{3,6}\Z")
DIFFICULTY_COUNTS = {"easy": 4, "medium": 4, "hard": 2}
FILE_INPUTS = {
    "taxonomy": "00_proposed_taxonomy.csv",
    "items": "01_teacher_assessment_items.csv",
    "assessments": "02_teacher_assessment_sessions.csv",
    "evidence": "03_teacher_item_evidence.csv",
    "labels": "04_teacher_consensus_labels.csv",
}


def read_csv(
    path: Path, required: set[str] | frozenset[str], *, exact: bool = False
) -> list[dict[str, str]]:
    """Reject malformed headers; never infer a missing identifier or label."""
    if not path.is_file():
        raise ValueError(f"Missing input CSV: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        if len(header) != len(set(header)):
            raise ValueError(f"Duplicate CSV column in {path.name}")
        absent = required - set(header)
        if absent or (exact and set(header) != required):
            raise ValueError(
                f"Invalid columns in {path.name}; missing={sorted(absent)}, extra={sorted(set(header) - required) if exact else []}"
            )
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"Malformed CSV row in {path.name}")
    return [{key: value.strip() for key, value in row.items()} for row in rows]


def parse_time(value: str) -> datetime | None:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except ValueError:
        return None


def yes(value: str) -> bool:
    return value.lower() == "true"


def split_codes(value: str) -> set[str]:
    parts = value.split("|") if value else []
    return {part.strip() for part in parts if part.strip()}


def valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def _unique(rows: list[dict[str, str]], field: str) -> set[str]:
    counts = Counter(row.get(field, "") for row in rows)
    return {key for key, count in counts.items() if not key or count > 1}


def _feature_row(
    session: dict[str, str], answers: list[dict[str, str]]
) -> dict[str, str]:
    times = [float(row["response_time_sec"]) for row in answers]
    correct = [yes(row["is_correct"]) for row in answers]
    row = {
        "quiz_session_id": session["quiz_session_id"],
        "student_code": session["student_code"],
        "concept_id": session["concept_id"],
        "quiz_completed_at": session["completed_at"],
        "question_count": str(len(answers)),
        "correct_count": str(sum(correct)),
        "accuracy": f"{statistics.mean(correct):.6f}",
        "response_time_mean_sec": f"{statistics.mean(times):.6f}",
        "response_time_median_sec": f"{statistics.median(times):.6f}",
        "high_confidence_wrong_count": str(
            sum(
                not yes(answer["is_correct"]) and answer["confidence_level"] == "high"
                for answer in answers
            )
        ),
    }
    for level in ("low", "medium", "high"):
        row[f"confidence_{level}_count"] = str(
            sum(answer["confidence_level"] == level for answer in answers)
        )
    for level in ("easy", "medium", "hard"):
        relevant = [answer for answer in answers if answer["difficulty_level"] == level]
        row[f"{level}_question_count"] = str(len(relevant))
        row[f"{level}_correct_count"] = str(
            sum(yes(answer["is_correct"]) for answer in relevant)
        )
    for tag in (
        "inverse_operation",
        "sign_error",
        "arithmetic_error",
        "concept_confusion",
    ):
        # Option tags are predictors only; they never become teacher targets.
        row[f"option_{tag}_count"] = str(
            sum(answer["misconception_code"] == tag for answer in answers)
        )
    return row


def _source_features(
    sessions: list[dict[str, str]],
    responses: list[dict[str, str]],
    exclude: dict[str, set[str]],
) -> dict[str, dict[str, str]]:
    bad_sessions = _unique(sessions, "quiz_session_id")
    bad_source_session_ids = _unique(sessions, "source_session_id")
    bad_response_ids = _unique(responses, "source_response_id")
    by_session: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in responses:
        by_session[row["quiz_session_id"]].append(row)
    features = {}
    for session in sessions:
        sid = session["quiz_session_id"]
        reasons = exclude[sid]
        if sid in bad_sessions:
            reasons.add("duplicate_or_missing_quiz_session_id")
        if session["source_session_id"] in bad_source_session_ids:
            reasons.add("duplicate_or_missing_source_session_id")
        if (
            not sid.startswith("QUIZ-")
            or not valid_uuid(sid[5:])
            or not valid_uuid(session["source_session_id"])
            or not valid_uuid(session["learning_cycle_id"])
        ):
            reasons.add("invalid_quiz_source_identifier")
        if (
            not STUDENT_CODE.fullmatch(session["student_code"])
            or session["student_code"] != session["student_id_recorded"]
        ):
            reasons.add("invalid_or_conflicting_quiz_student_code")
        if (
            session["assessment_phase"] != "pre_tutor"
            or session["concept_id"] != "linear_equations"
        ):
            reasons.add("not_pre_tutor_linear_equations")
        if session["status"] != "completed" or not yes(session["assessment_complete"]):
            reasons.add("quiz_incomplete")
        start, end = (
            parse_time(session["started_at"]),
            parse_time(session["completed_at"]),
        )
        if not start or not end or start >= end:
            reasons.add("invalid_quiz_chronology")
        answers = by_session.get(sid, [])
        if len(answers) != 10 or session["responses_saved"] != "10":
            reasons.add("quiz_answer_count_not_ten")
        if Counter(row["difficulty_level"] for row in answers) != DIFFICULTY_COUNTS:
            reasons.add("quiz_difficulty_coverage_mismatch")
        if (
            len({row["question_id"] for row in answers}) != len(answers)
            or len({row["question_order"] for row in answers}) != len(answers)
            or {row["question_order"] for row in answers}
            != {str(i) for i in range(1, 11)}
        ):
            reasons.add("duplicate_or_missing_question")
        if len({row["question_code"] for row in answers}) != len(answers) or any(
            not row["question_code"] for row in answers
        ):
            reasons.add("duplicate_or_missing_question_code")
        for answer in answers:
            if answer["source_response_id"] in bad_response_ids:
                reasons.add("duplicate_or_missing_source_response_id")
            if (
                not valid_uuid(answer["source_response_id"])
                or not valid_uuid(answer["question_id"])
                or not valid_uuid(answer["selected_option_id"])
            ):
                reasons.add("invalid_quiz_response_identifier")
            if (
                answer["student_code"] != session["student_code"]
                or answer["student_id_recorded"] != session["student_id_recorded"]
                or answer["assessment_phase"] != "pre_tutor"
                or answer["concept_id"] != session["concept_id"]
            ):
                reasons.add("quiz_response_identity_conflict")
            if (
                answer["confidence_level"] not in {"low", "medium", "high"}
                or answer["is_correct"].lower() not in {"true", "false"}
                or answer["misconception_code"] not in OPTION_TAGS
                or (yes(answer["is_correct"]) and answer["misconception_code"])
            ):
                reasons.add("invalid_quiz_response_value")
            try:
                if float(answer["response_time_sec"]) < 0 or not 0 <= float(
                    answer["response_time_sec"]
                ) < float("inf"):
                    reasons.add("invalid_response_time")
            except ValueError:
                reasons.add("invalid_response_time")
            answered = parse_time(answer["answered_at"])
            if not answered or (start and answered < start) or (end and answered > end):
                reasons.add("quiz_answer_outside_session")
        if not reasons:
            features[sid] = _feature_row(session, answers)
    for row in responses:
        if not row["quiz_session_id"] or row["quiz_session_id"] not in {
            s["quiz_session_id"] for s in sessions
        }:
            exclude[row["quiz_session_id"] or "<missing quiz session id>"].add(
                "orphan_quiz_response"
            )
    return features


def _approval(
    rows: list[dict[str, str]],
    expected: set[str],
    id_column: str,
    version_column: str,
    version: str,
) -> bool:
    if _unique(rows, id_column) or {row[id_column] for row in rows} != expected:
        return False
    return all(
        row[version_column] == version
        and row["teacher_review_status"] == "approved"
        and bool(row["approval_reference"])
        and all(
            row[column]
            for column in (
                "name",
                "definition",
                "example_error",
                "positive_criteria",
                "exclusion_criteria",
                "minimum_evidence",
                "possible_overlap",
            )
        )
        for row in rows
    )


def _assessment_reasons(
    assessment: dict[str, str], feature: dict[str, str] | None, form_approved: bool
) -> set[str]:
    reasons = set()
    if not feature:
        reasons.add("missing_or_invalid_quiz_feature")
    elif assessment["student_code"] != feature["student_code"]:
        reasons.add("assessment_quiz_student_conflict")
    if not STUDENT_CODE.fullmatch(assessment["student_code"]):
        reasons.add("invalid_assessment_student_code")
    if assessment["form_version"] != FORM_VERSION or not form_approved:
        reasons.add("assessment_form_not_approved_or_version_mismatch")
    start = parse_time(assessment["assessment_started_at"])
    end = parse_time(assessment["assessment_completed_at"])
    quiz_end = parse_time(feature["quiz_completed_at"]) if feature else None
    if not start or not end or start >= end or (quiz_end and quiz_end >= start):
        reasons.add("assessment_not_after_completed_quiz")
    if assessment["tutoring_status"] not in {"not_started", "started"}:
        reasons.add("tutoring_status_unknown")
    tutor_start = (
        parse_time(assessment["tutoring_started_at"])
        if assessment["tutoring_started_at"]
        else None
    )
    if assessment["tutoring_status"] == "started" and (
        not tutor_start or (end and tutor_start <= end)
    ):
        reasons.add("assessment_not_before_tutoring")
    if (
        assessment["tutoring_status"] == "not_started"
        and assessment["tutoring_started_at"]
    ):
        reasons.add("tutoring_status_timestamp_conflict")
    if not yes(assessment["no_hints_or_feedback"]):
        reasons.add("assessment_hints_or_feedback_unknown_or_present")
    if not yes(assessment["assessor_blinded_to_quiz"]):
        reasons.add("assessor_not_blinded_to_quiz")
    if not assessment["assessor_code"]:
        reasons.add("missing_assessor_code")
    if (
        assessment["record_origin"] not in ORIGINS
        or assessment["record_origin"] != "real"
    ):
        reasons.add("not_verified_real_record")
    if (
        not yes(assessment["research_authorized"])
        or not assessment["authorization_reference"]
        or not assessment["consent_evidence_reference"]
    ):
        reasons.add("research_authorization_or_consent_missing")
    return reasons


def _label_reasons(
    label: dict[str, str],
    assessment: dict[str, str],
    evidence: list[dict[str, str]],
    items: dict[str, dict[str, str]],
    taxonomy_approved: bool,
) -> set[str]:
    reasons = set()
    if (
        label["assessment_id"] != assessment["assessment_id"]
        or label["quiz_session_id"] != assessment["quiz_session_id"]
        or label["student_code"] != assessment["student_code"]
    ):
        reasons.add("consensus_assessment_identity_conflict")
    if (
        label["form_version"] != assessment["form_version"]
        or label["taxonomy_version"] != TAXONOMY_VERSION
    ):
        reasons.add("consensus_version_mismatch")
    category = label["consensus_category"]
    if category not in TARGET_CATEGORIES:
        reasons.add("invalid_or_review_only_teacher_target")
    if (
        label["verification_status"] != "verified"
        or not label["verified_by_code"]
        or not parse_time(label["verified_at"])
    ):
        reasons.add("teacher_label_unverified")
    if not taxonomy_approved:
        reasons.add("taxonomy_not_teacher_approved")
    raters = split_codes(label["rater_codes"])
    ids = split_codes(label["evidence_ids"])
    if (
        len(raters) < 2
        or len(raters) != len(label["rater_codes"].split("|"))
        or len(ids) != len(label["evidence_ids"].split("|"))
    ):
        reasons.add("insufficient_independent_raters_or_evidence_ids")
    selected = [row for row in evidence if row["evidence_id"] in ids]
    if len(selected) != len(ids) or any(
        row["assessment_id"] != assessment["assessment_id"] for row in selected
    ):
        reasons.add("evidence_link_missing_or_cross_assessment")
    if any(
        row["rater_code"] not in raters
        or row["verification_status"] != "verified"
        or row["proposed_category"] not in CATEGORIES
        or row["evidence_quality"] != "sufficient"
        or not row["working_steps"]
        or (
            row["proposed_category"] not in {"M0", "REVIEW"}
            and not row["observed_error"]
        )
        for row in selected
    ):
        reasons.add("evidence_unverified_or_insufficient")
    if {row["rater_code"] for row in selected} != raters:
        reasons.add("rater_evidence_mismatch")
    if any(
        row["item_id"] not in items
        or row["recorded_at"] == ""
        or not parse_time(row["recorded_at"])
        for row in selected
    ):
        reasons.add("invalid_item_or_evidence_timestamp")
    if any(
        row["item_id"] in items
        and items[row["item_id"]]["form_version"] != assessment["form_version"]
        for row in selected
    ):
        reasons.add("evidence_item_form_version_conflict")
    supporting = {
        row["item_id"] for row in selected if row["proposed_category"] == category
    }
    if len(supporting) < (4 if category == "M0" else 2):
        reasons.add("insufficient_distinct_supporting_items")
    if (
        len(
            {
                row["rater_code"]
                for row in selected
                if row["proposed_category"] == category
            }
        )
        < 2
    ):
        reasons.add("insufficient_independent_support_for_category")
    if any(
        category not in split_codes(items[row["item_id"]]["opportunity_codes"])
        for row in selected
        if row["proposed_category"] == category and row["item_id"] in items
    ):
        reasons.add("item_does_not_support_category")
    competing = {
        row["proposed_category"]
        for row in selected
        if row["proposed_category"] not in {category, "REVIEW"}
    }
    disagree = yes(label["disagreement_flag"])
    if competing and not (
        disagree
        and label["consensus_method"] == "adjudicated"
        and label["resolution_note"]
        and label["verified_by_code"] not in raters
    ):
        reasons.add("unresolved_competing_teacher_labels")
    if disagree != bool(competing) or label["consensus_method"] not in {
        "agreement",
        "adjudicated",
    }:
        reasons.add("inconsistent_disagreement_record")
    if disagree and label["consensus_method"] != "adjudicated":
        reasons.add("disagreement_not_adjudicated")
    if any(row["proposed_category"] == "REVIEW" for row in selected):
        reasons.add("ambiguous_item_evidence")
    return reasons


def join_validated_record(
    feature: dict[str, str], assessment: dict[str, str], label: dict[str, str]
) -> dict[str, str]:
    """Join already validated identities; never derive a target from option tags."""
    if (
        feature["quiz_session_id"] != assessment["quiz_session_id"]
        or feature["quiz_session_id"] != label["quiz_session_id"]
        or feature["student_code"] != assessment["student_code"]
        or feature["student_code"] != label["student_code"]
        or assessment["assessment_id"] != label["assessment_id"]
    ):
        raise ValueError("Validated join identity conflict")
    return {
        "quiz_session_id": feature["quiz_session_id"],
        "student_code": assessment["student_code"],
        "assessment_id": assessment["assessment_id"],
        "label_id": label["label_id"],
        "concept_id": feature["concept_id"],
        "quiz_completed_at": feature["quiz_completed_at"],
        "assessment_completed_at": assessment["assessment_completed_at"],
        "taxonomy_version": label["taxonomy_version"],
        "form_version": assessment["form_version"],
        "teacher_category": label["consensus_category"],
        **{column: feature[column] for column in PREDICTOR_COLUMNS},
    }


def _write_csv(
    path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    with path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_pipeline(paths: dict[str, Path], output_dir: Path) -> dict:
    """Read only named local CSVs; write new files only to an explicit fresh directory."""
    root = Path(__file__).resolve().parents[5]
    destination = output_dir.resolve()
    if destination.exists():
        raise ValueError("Output directory already exists; choose a new path")
    if destination.is_relative_to(root) and not destination.is_relative_to(
        root / "exports"
    ):
        raise ValueError(
            "Repository output must be under ignored exports/; choose a fresh path"
        )
    source_sessions = read_csv(paths["quiz_sessions"], SOURCE_SESSION_COLUMNS)
    source_responses = read_csv(paths["quiz_responses"], SOURCE_RESPONSE_COLUMNS)
    tables = {
        key: read_csv(paths[key], set(SCHEMAS[name].columns), exact=True)
        for key, name in FILE_INPUTS.items()
    }
    taxonomy, item_rows = tables["taxonomy"], tables["items"]
    taxonomy_approved = _approval(
        taxonomy, set(CATEGORIES), "category_code", "taxonomy_version", TAXONOMY_VERSION
    )
    form_approved = (
        bool(item_rows)
        and not _unique(item_rows, "item_id")
        and all(
            row["form_version"] == FORM_VERSION
            and row["concept_id"] == "linear_equations"
            and row["teacher_review_status"] == "approved"
            and row["approval_reference"]
            and row["prompt_en"]
            and row["expected_working"]
            and split_codes(row["opportunity_codes"]) <= CATEGORIES
            and row["working_steps_required"].lower() == "true"
            and row["hints_or_feedback_allowed"].lower() == "false"
            for row in item_rows
        )
        and all(
            sum(code in split_codes(row["opportunity_codes"]) for row in item_rows) >= 2
            for code in ("M1", "M2", "M3", "M4")
        )
    )
    items = {row["item_id"]: row for row in item_rows}
    exclude: dict[str, set[str]] = defaultdict(set)
    features = _source_features(source_sessions, source_responses, exclude)
    assessments = tables["assessments"]
    evidence = tables["evidence"]
    labels = tables["labels"]
    bad_assessments = _unique(assessments, "assessment_id")
    bad_evidence = _unique(evidence, "evidence_id")
    repeated_rater_items = {
        key
        for key, count in Counter(
            (row["assessment_id"], row["item_id"], row["rater_code"])
            for row in evidence
        ).items()
        if count > 1
    }
    bad_labels = _unique(labels, "label_id")
    quiz_assessment_counts = Counter(row["quiz_session_id"] for row in assessments)
    labels_by_assessment: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labels:
        labels_by_assessment[row["assessment_id"]].append(row)
    labeled = []
    assessment_quarantine_count = 0
    quarantined = [
        {
            "assessment_id": "",
            "quiz_session_id": sid,
            "student_code": "",
            "reasons": "|".join(sorted(reasons)),
        }
        for sid, reasons in sorted(exclude.items())
        if reasons
    ]
    for assessment in assessments:
        aid = assessment["assessment_id"] or "<missing assessment id>"
        sid = assessment["quiz_session_id"]
        reasons = _assessment_reasons(assessment, features.get(sid), form_approved)
        if aid in bad_assessments:
            reasons.add("duplicate_or_missing_assessment_id")
        if quiz_assessment_counts[sid] != 1 or not sid:
            reasons.add("multiple_or_missing_assessments_for_quiz")
        linked = labels_by_assessment.get(aid, [])
        if len(linked) != 1:
            reasons.add("missing_or_multiple_consensus_labels")
        else:
            label = linked[0]
            if label["label_id"] in bad_labels:
                reasons.add("duplicate_or_missing_label_id")
            selected_evidence = [
                row
                for row in evidence
                if row["evidence_id"] in split_codes(label["evidence_ids"])
            ]
            if any(row["evidence_id"] in bad_evidence for row in selected_evidence):
                reasons.add("duplicate_or_missing_evidence_id")
            if any(
                (row["assessment_id"], row["item_id"], row["rater_code"])
                in repeated_rater_items
                for row in selected_evidence
            ):
                reasons.add("duplicate_rater_item_observation")
            reasons.update(
                _label_reasons(label, assessment, evidence, items, taxonomy_approved)
            )
        if reasons:
            assessment_quarantine_count += 1
            quarantined.append(
                {
                    "assessment_id": aid,
                    "quiz_session_id": sid,
                    "student_code": assessment["student_code"],
                    "reasons": "|".join(sorted(reasons)),
                }
            )
            continue
        labeled.append(join_validated_record(features[sid], assessment, linked[0]))
    for label in labels:
        if label["assessment_id"] not in {row["assessment_id"] for row in assessments}:
            quarantined.append(
                {
                    "assessment_id": label["assessment_id"],
                    "quiz_session_id": label["quiz_session_id"],
                    "student_code": label["student_code"],
                    "reasons": "orphan_consensus_label",
                }
            )
    referenced_evidence_ids = (
        set().union(*(split_codes(label["evidence_ids"]) for label in labels))
        if labels
        else set()
    )
    for row in evidence:
        if row["assessment_id"] not in {item["assessment_id"] for item in assessments}:
            quarantined.append(
                {
                    "assessment_id": row["assessment_id"],
                    "quiz_session_id": "",
                    "student_code": "",
                    "reasons": "orphan_item_evidence",
                }
            )
        elif row["evidence_id"] in bad_evidence:
            quarantined.append(
                {
                    "assessment_id": row["assessment_id"],
                    "quiz_session_id": "",
                    "student_code": "",
                    "reasons": "duplicate_or_missing_evidence_id",
                }
            )
        elif row["evidence_id"] not in referenced_evidence_ids:
            quarantined.append(
                {
                    "assessment_id": row["assessment_id"],
                    "quiz_session_id": "",
                    "student_code": "",
                    "reasons": "unreferenced_item_evidence",
                }
            )
    missing = Counter()
    for table in (source_sessions, source_responses, *tables.values()):
        for row in table:
            missing.update(column for column, value in row.items() if not value)
    observed_distribution = Counter(row["teacher_category"] for row in labeled)
    distribution = {
        code: observed_distribution[code] for code in sorted(TARGET_CATEGORIES)
    }
    warnings = []
    if any(distribution.get(code, 0) == 0 for code in TARGET_CATEGORIES):
        warnings.append(
            "Some proposed target classes have no eligible independent learners"
        )
    observed_class_counts = [count for count in distribution.values() if count]
    if len(observed_class_counts) > 1 and max(observed_class_counts) > 3 * min(
        observed_class_counts
    ):
        warnings.append(
            "Class imbalance requires design review; the 3:1 flag is descriptive, not a sample-size rule"
        )
    if len({row["student_code"] for row in labeled}) < len(labeled):
        warnings.append(
            "Repeated learners require learner-grouped splitting; rows are not independent learners"
        )
    assessment_origin = {
        row["assessment_id"]: row["record_origin"] for row in assessments
    }
    quarantine_counts = Counter(
        reason for row in quarantined for reason in row["reasons"].split("|")
    )
    report = {
        "readiness": "NOT TRAINING READY",
        "readiness_note": "M3-A preparation cannot verify external teacher approval, consent authenticity, or a defensible learner-grouped validation plan. Human research review is required before training.",
        "taxonomy_teacher_approved_in_csv": taxonomy_approved,
        "assessment_form_teacher_approved_in_csv": form_approved,
        "quiz_feedback_protocol_note": "The live Quiz reveals feedback after each first answer; later official first answers may be influenced. The source CSV does not independently log hints or feedback exposure.",
        "unique_learner_count": len(
            {
                row["student_code"]
                for row in source_sessions
                if STUDENT_CODE.fullmatch(row["student_code"])
            }
        ),
        "completed_quiz_session_count": sum(
            row["status"] == "completed" and row["assessment_phase"] == "pre_tutor"
            for row in source_sessions
        ),
        "valid_quiz_feature_rows": len(features),
        "independently_assessed_real_learner_count": len(
            {
                row["student_code"]
                for row in assessments
                if row["student_code"] and row["record_origin"] == "real"
            }
        ),
        "verified_real_teacher_label_count": sum(
            row["verification_status"] == "verified"
            and assessment_origin.get(row["assessment_id"]) == "real"
            for row in labels
        ),
        "verified_label_rows_all_origins": sum(
            row["verification_status"] == "verified" for row in labels
        ),
        "unverified_label_row_count": sum(
            row["verification_status"] != "verified" for row in labels
        ),
        "unresolved_consensus_count": quarantine_counts[
            "unresolved_competing_teacher_labels"
        ],
        "code_or_session_conflict_count": sum(
            count
            for reason, count in quarantine_counts.items()
            if "conflict" in reason or "identity" in reason
        ),
        "eligible_training_records": len(labeled),
        "effective_independent_eligible_learners": len(
            {row["student_code"] for row in labeled}
        ),
        "eligible_class_distribution": distribution,
        "missing_value_counts_by_column": dict(sorted(missing.items())),
        "quarantined_assessment_count": assessment_quarantine_count,
        "quarantined_record_count": len(quarantined),
        "quarantine_reason_counts": dict(sorted(quarantine_counts.items())),
        "source_quiz_issue_counts": dict(
            sorted(
                Counter(
                    reason for reasons in exclude.values() for reason in reasons
                ).items()
            )
        ),
        "warnings": warnings,
    }
    destination.mkdir(parents=True, exist_ok=False)
    _write_csv(
        destination / "05_quiz_ml_features.csv",
        SCHEMAS["05_quiz_ml_features.csv"].columns,
        [features[key] for key in sorted(features)],
    )
    _write_csv(
        destination / "06_quiz_ml_labeled_dataset.csv",
        SCHEMAS["06_quiz_ml_labeled_dataset.csv"].columns,
        labeled,
    )
    _write_csv(
        destination / "quarantine.csv",
        ("assessment_id", "quiz_session_id", "student_code", "reasons"),
        quarantined,
    )
    (destination / "quality_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report
