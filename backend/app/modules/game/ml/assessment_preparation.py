"""Milestone 2.3.3: guarded offline review import and paired, date-aware preparation.

There is deliberately no training option. Existing outputs and input evidence are
never rewritten. A successful run ends with a hash manifest for its fresh folder.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from .collection_research import (
    CLASSES,
    COHORT,
    DEVELOPMENT_SESSIONS,
    INVALID_CODE_DECISION,
    CollectionReview,
    audit_collection,
    has_invalid_student_code,
    prepare_session,
    read_export,
    timestamp,
)
from .research_dataset import extract_research_features, feature_set
from .research_schema import validate_research_dataset
from .research_training import ExperimentConfig, learner_split, prepare_cohort
from .session_verification import (
    FIELDS,
    READ_ONLY_FIELDS,
    import_decisions,
    save_json,
)
from .teacher_assessments import BEFORE, TeacherAssessment, timing_category

ASSESSMENT_FIELDS = (
    "teacher_assessment_score_out_of_10",
    "teacher_label_source_status",
    "suggested_level_unverified",
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_sheet(path: Path, fields: tuple) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(fields):
            raise ValueError(f"Unexpected columns/order: {path.name}")
        rows = list(reader)
    if any(set(row) != set(fields) or None in row.values() for row in rows):
        raise ValueError("Missing or extra CSV cells")
    ids = [row["game_session_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate session IDs in input sheet")
    return rows


def checked_context(rows: list[dict], snapshot: dict, *, assessment: bool = False):
    originals = {row["game_session_id"]: row for row in snapshot["read_only_rows"]}
    if {row["game_session_id"] for row in rows} != set(originals):
        raise ValueError("Sheet must contain every frozen session ID exactly once")
    restored = []
    compatible = []
    for row in rows:
        original = originals[row["game_session_id"]]
        for key in READ_ONLY_FIELDS:
            if row[key] == original[key]:
                continue
            if assessment and key == "teacher_label":
                continue  # Independent assessment annotation, validated separately.
            if not (
                key == "existing_verification_status"
                and original[key] == "REVIEW REQUIRED"
                and row[key] == "genuine gameplay"
                and row["researcher_decision"] == "RESEARCH_VERIFIED"
            ):
                raise ValueError(
                    f"Protected {key} changed for {row['game_session_id']}"
                )
            restored.append(
                {
                    "session_id": row["game_session_id"],
                    "field": key,
                    "researcher_annotation": row[key],
                    "restored_snapshot_value": original[key],
                }
            )
        compatible.append({**original, **{key: row[key] for key in FIELDS[9:]}})
    return compatible, restored


def write_csv(path: Path, rows: list[dict], fields=None):
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate_assessments(
    rows: list[dict],
    review_rows: list[dict],
    snapshot: dict,
    source_hash: str,
    baseline: CollectionReview,
    resolutions: dict[str, str],
) -> tuple[dict, dict]:
    _, restored = checked_context(rows, snapshot, assessment=True)
    decisions = {row["game_session_id"]: row for row in review_rows}
    grouped = defaultdict(list)
    for number, row in enumerate(rows, 2):
        latest = decisions[row["game_session_id"]]
        if any(row[key] != latest[key] for key in FIELDS[9:]):
            raise ValueError(
                f"Assessment and reviewed CSV decisions conflict: {row['game_session_id']}"
            )
        code = row["student_code"]
        if code not in COHORT:
            if (
                any(
                    row[key]
                    for key in (
                        ASSESSMENT_FIELDS[0],
                        "teacher_label",
                        ASSESSMENT_FIELDS[2],
                    )
                )
                or row[ASSESSMENT_FIELDS[1]] != "NO_MATCHING_TEACHER_ASSESSMENT"
            ):
                raise ValueError(
                    "Excluded/unknown code has unexpected assessment evidence"
                )
            continue
        grouped[code].append((number, row))
    if set(grouped) != COHORT:
        raise ValueError(
            "Independent assessment coverage must include all 16 confirmed codes"
        )
    if set(resolutions) - COHORT:
        raise ValueError("Resolution references an invalid student code")
    assessments = {}
    for code, entries in sorted(grouped.items()):
        values = {
            tuple(row[key] for key in ("teacher_label", *ASSESSMENT_FIELDS))
            for _, row in entries
        }
        if len(values) != 1:
            raise ValueError(f"Conflicting repeated assessment evidence for {code}")
        level, text, status, suggested = values.pop()
        if not text.isascii() or not text.isdigit():
            raise ValueError(f"Teacher score must be an integer for {code}")
        score = int(text)
        if code in baseline.teacher_scores and score != baseline.teacher_scores[code]:
            raise ValueError(f"Previously supplied teacher score changed for {code}")
        known_revision = code in baseline.teacher_scores
        assessments[code] = TeacherAssessment(
            student_code=code,
            score=score,
            original_score_text=text,
            assessed_on=date(2026, 10, 15 if int(code[4:]) <= 7 else 16),
            original_teacher_level=level,
            original_source_status=status,
            original_suggested_level_unverified=suggested,
            source_csv_sha256=source_hash,
            source_row_numbers=[number for number, _ in entries],
            score_level_resolution_reference=resolutions.get(code),
            revision_before_assessment=True if known_revision else None,
            revision_description=baseline.revision_description
            if known_revision
            else None,
        )
    return assessments, {
        "assessment_rows": len(rows),
        "independently_assessed_learners": len(assessments),
        "additional_columns": list(ASSESSMENT_FIELDS),
        "assessment_status_annotations": restored,
        "separate_assessment_label_annotations": [
            {
                "session_id": row["game_session_id"],
                "student_code": row["student_code"],
                "frozen_review_label": original["teacher_label"],
                "assessment_csv_label": row["teacher_label"],
            }
            for row in rows
            for original in snapshot["read_only_rows"]
            if original["game_session_id"] == row["game_session_id"]
            and original["teacher_label"] != row["teacher_label"]
        ],
        "unresolved_codes": [
            code for code, item in assessments.items() if not item.usable
        ],
        "classification_source_counts": dict(
            Counter(item.classification_source for item in assessments.values())
        ),
        "source_status_counts": dict(
            Counter(item.original_source_status for item in assessments.values())
        ),
        "class_distribution": {
            label: sum(
                item.usable and item.report()["target_level"] == label
                for item in assessments.values()
            )
            for label in CLASSES
        },
    }


def paired_dataset(observations: list) -> dict:
    records = validate_research_dataset(observations)
    features = {}
    for name in ("score_only", "score_plus_behaviour"):
        features[name] = [
            {
                "student_code": row.student_code,
                "session_id": row.session_id,
                **{
                    key: extract_research_features(row).values[key]
                    for key in feature_set(name).names
                },
            }
            for row in records
        ]
    learners = {row.student_code: row.mastery_label.value for row in records}
    return {
        "observations": [row.model_dump(mode="json") for row in records],
        "features": features,
        "feature_definitions": {
            name: list(feature_set(name).names) for name in features
        },
        "learner_class_distribution": {
            level: sum(value == level for value in learners.values())
            for level in CLASSES
        },
        "observation_class_distribution": {
            level: sum(row.mastery_label.value == level for row in records)
            for level in CLASSES
        },
        "learners": sorted(learners),
    }


def prepare_datasets(
    tables: dict,
    provenance: dict,
    reviewed: CollectionReview,
    assessments: dict,
    review_ids: set,
) -> tuple[dict, dict, list]:
    # This original audit supplies all unchanged global checks and BOTH exact
    # quarantines. Authenticity never overrides an integrity failure.
    integrity = audit_collection(tables, provenance, reviewed)
    quarantined = set(integrity["quarantine"]["session_ids"])
    index = {}
    for name in ("student_answers", "game_events", "game_analytics"):
        index[name] = defaultdict(list)
        for row in tables[name]:
            index[name][row["game_session_id"]].append(row)
    retrospective, prospective, decisions, links = [], [], [], []
    for session in sorted(
        tables["game_sessions"], key=lambda row: row["game_session_id"]
    ):
        sid, code = session["game_session_id"], session["student_code"]
        if sid not in review_ids:
            continue
        evidence = {name: index[name][sid] for name in index}
        item = assessments.get(code)
        category = None
        if item is not None:
            start = min(
                [
                    timestamp(session["started_at"]),
                    *(
                        timestamp(row["event_timestamp"])
                        for row in evidence["game_events"]
                    ),
                ],
            )
            # For incomplete sessions a last observed event is not a completion.
            end = (
                max(
                    [
                        timestamp(session["completed_at"]),
                        *(
                            timestamp(row["event_timestamp"])
                            for row in evidence["game_events"]
                        ),
                    ],
                )
                if session["completed_at"]
                else None
            )
            category = timing_category(start, end, item.assessed_on, item.timezone)
        reason = None
        retro_ok = pro_ok = False
        if has_invalid_student_code(session):
            reason = INVALID_CODE_DECISION
        elif sid in DEVELOPMENT_SESSIONS or sid in reviewed.development_sessions:
            reason = "EXCLUDED_DEVELOPMENT"
        elif sid in quarantined:
            reason = "QUARANTINED_INTEGRITY"
        elif integrity["global_issues"]:
            reason = "BLOCKED_GLOBAL_INTEGRITY"
        elif sid not in reviewed.verified_sessions:
            reason = "AUTHENTICITY_NOT_VERIFIED"
        elif (
            session["status"] != "completed"
            or session["saved_assessment_complete"] != "True"
        ):
            reason = "INCOMPLETE"
        elif item is None or not item.usable:
            reason = "INDEPENDENT_LABEL_UNAVAILABLE_OR_CONFLICTED"
        else:
            try:
                row, linked = prepare_session(
                    session,
                    evidence["student_answers"],
                    evidence["game_events"],
                    evidence["game_analytics"],
                    reviewed,
                    independent_assessment=item,
                    analysis_purpose="retrospective",
                )
                retrospective.append(row)
                links.append(
                    {
                        **linked,
                        "assessment_timing_category": category,
                        "actual_recorded_tutor_phase": session["assessment_phase"],
                    }
                )
                retro_ok = True
                if category == BEFORE:
                    before, _ = prepare_session(
                        session,
                        evidence["student_answers"],
                        evidence["game_events"],
                        evidence["game_analytics"],
                        reviewed,
                        independent_assessment=item,
                        analysis_purpose="prospective",
                    )
                    prospective.append(before)
                    pro_ok = True
            except (ValueError, KeyError, TypeError) as error:
                reason = f"EVIDENCE_BLOCKED: {error}"
        decisions.append(
            {
                "session_id": sid,
                "student_code": code,
                "game_mode": session["game_type"],
                "started_at": session["started_at"],
                "completed_at": session["completed_at"],
                "completion": session["status"],
                "saved_assessment_complete": session["saved_assessment_complete"],
                "answer_count": len(evidence["student_answers"]),
                "event_count": len(evidence["game_events"]),
                "assessment_date": item.assessed_on.isoformat() if item else None,
                "assessment_timing_category": category,
                "timing_basis": "audited window"
                if session["completed_at"]
                else "start date only; incomplete",
                "actual_recorded_tutor_phase": session["assessment_phase"],
                "researcher_verified": sid in reviewed.verified_sessions,
                "integrity_quarantined": sid in quarantined,
                "classification_source": item.classification_source if item else None,
                "retrospective_eligible": retro_ok,
                "prospective_eligible": pro_ok,
                "exclusion_reason": reason,
                "prospective_exclusion_reason": reason
                or (None if pro_ok else category),
            }
        )
    datasets = {
        "retrospective": paired_dataset(retrospective),
        "prospective": paired_dataset(prospective),
    }
    return (
        datasets,
        {
            key: integrity[key]
            for key in (
                "source_provenance",
                "source_checks",
                "global_issues",
                "session_integrity_issues",
                "quarantine",
                "approved_ids_missing_from_export",
            )
        },
        [decisions, links],
    )


def readiness(dataset: dict, config, integrity: dict, decisions: list) -> dict:
    reasons = list(integrity["global_issues"])
    if integrity["approved_ids_missing_from_export"]:
        reasons.append("Previously verified session IDs missing from export")
    if any(
        (row["exclusion_reason"] or "").startswith("EVIDENCE_BLOCKED:")
        for row in decisions
    ):
        reasons.append("Some completed verified sessions failed source evidence checks")
    missing_classes = [
        level for level in CLASSES if not dataset["learner_class_distribution"][level]
    ]
    if missing_classes:
        reasons.append(
            "No eligible independent learners for required classes: "
            + ", ".join(missing_classes)
        )
    details = None
    try:
        cohort = prepare_cohort(dataset["observations"], config)
        details = learner_split(cohort, config).details
    except ValueError as error:
        reasons.append(str(error))
    return {
        "mechanical_evaluation_status": "BLOCKED"
        if reasons
        else "FEASIBLE_PRELIMINARY_ONLY",
        "learner_grouped_split_status": "PASS" if details is not None else "BLOCKED",
        "blocking_reasons": reasons,
        "fixed_grouped_split": details,
        "eligible_observations": len(dataset["observations"]),
        "independent_learners": len(dataset["learners"]),
        "independent_teacher_label_coverage": {
            "labeled_eligible_observations": sum(
                row["mastery_label"] is not None for row in dataset["observations"]
            ),
            "eligible_observations": len(dataset["observations"]),
            "independently_assessed_eligible_learners": len(dataset["learners"]),
        },
        "learner_class_distribution": dataset["learner_class_distribution"],
        "classes_without_two_independent_learners": [
            level
            for level in CLASSES
            if dataset["learner_class_distribution"][level] < 2
        ],
        "observation_class_distribution": dataset["observation_class_distribution"],
        "model_a_observations": len(dataset["features"]["score_only"]),
        "model_b_observations": len(dataset["features"]["score_plus_behaviour"]),
        "training_performed": False,
        "training_authorized_by_this_milestone": False,
        "research_power_established": False,
    }


def prepare(
    *,
    export: Path,
    sheet: Path,
    assessment_csv: Path,
    snapshot_path: Path,
    baseline_path: Path,
    output: Path,
    resolutions: dict[str, str] | None = None,
    milestone: str = "2.3.3",
):
    if milestone not in ("2.3.3", "2.3.4"):
        raise ValueError("Unsupported preparation milestone")
    if output.exists():
        raise FileExistsError(
            "Preparation snapshot exists; choose a fresh output folder"
        )
    inputs = {
        "export": export,
        "review_sheet": sheet,
        "assessment_csv": assessment_csv,
        "review_snapshot": snapshot_path,
        "review_baseline": baseline_path,
    }
    if any(output.resolve() in path.resolve().parents for path in inputs.values()):
        raise ValueError("Output cannot contain input evidence")
    hashes = {key: file_hash(path) for key, path in inputs.items()}
    tables, provenance = read_export(export)
    baseline = CollectionReview.model_validate_json(
        baseline_path.read_text(encoding="utf-8")
    )
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    edited = read_sheet(sheet, FIELDS)
    compatible, restored = checked_context(edited, snapshot)
    assessment_rows = read_sheet(assessment_csv, (*FIELDS, *ASSESSMENT_FIELDS))
    assessments, assessment_report = validate_assessments(
        assessment_rows,
        edited,
        snapshot,
        hashes["assessment_csv"],
        baseline,
        resolutions or {},
    )
    raw_rejection = None
    try:
        import_decisions(sheet, snapshot, tables, provenance, baseline)
    except ValueError as error:
        raw_rejection = str(error)
    output.mkdir(parents=True, exist_ok=False)
    compatible_path = output / "session_review_sheet.IMPORT_COMPATIBLE.csv"
    write_csv(compatible_path, compatible, FIELDS)
    reviewed, receipt = import_decisions(
        compatible_path, snapshot, tables, provenance, baseline
    )
    if any(
        reviewed.verified_sessions.get(sid) != item
        for sid, item in baseline.verified_sessions.items()
    ):
        raise ValueError("Previously verified approval provenance changed")
    config = ExperimentConfig(target="mastery", class_labels=CLASSES)
    datasets, integrity, (decisions, links) = prepare_datasets(
        tables,
        provenance,
        reviewed,
        assessments,
        {row["game_session_id"] for row in compatible},
    )
    ready = {
        name: readiness(data, config, integrity, decisions)
        for name, data in datasets.items()
    }
    report = {
        "milestone": milestone,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "data_kind": "real_collected",
        "models_trained": False,
        "model_artifacts": [],
        "source_evidence": {
            key: {"path": str(path.resolve()), "sha256": hashes[key]}
            for key, path in inputs.items()
        },
        "implementation_sha256": {
            name: file_hash(Path(__file__).with_name(name))
            for name in (
                "assessment_preparation.py",
                "teacher_assessments.py",
                "collection_research.py",
                "session_verification.py",
                "research_schema.py",
                "research_dataset.py",
                "research_training.py",
            )
        },
        "researcher_review": {
            "exact_session_ids_validated": len(edited),
            "raw_sheet_import_rejection": raw_rejection,
            "compatible_copy_restored_protected_cells": len(restored),
            "restored_annotations": restored,
            "imported_decision_counts": receipt["review_sheet_counts"],
            "rejected_decisions_after_compatible_import": [],
            "previously_verified_sessions_preserved": sorted(
                baseline.verified_sessions
            ),
            "verification_basis_assessment": (
                "All non-UNKNOWN decisions have the nonblank basis required by the unchanged "
                "importer. The repeated school-play statement is an explicit researcher "
                "assertion, not independent corroboration from collection logs or analytics. "
                "No supporting evidence was manufactured. Incompleteness and integrity "
                "remain separate from authenticity."
            ),
        },
        "verified_genuine_learners": len(
            {item.student_code for item in reviewed.verified_sessions.values()}
        ),
        "verified_genuine_sessions": len(reviewed.verified_sessions),
        "raw_completed_candidate_sessions": sum(
            row["student_code"] in COHORT and row["completion"] == "completed"
            for row in decisions
        ),
        "incomplete_candidate_sessions": sum(
            row["student_code"] in COHORT and row["completion"] != "completed"
            for row in decisions
        ),
        "teacher_assessments": assessment_report,
        "assessment_timing_all_candidate_sessions": dict(
            Counter(
                row["assessment_timing_category"]
                for row in decisions
                if row["student_code"] in COHORT
            )
        ),
        "assessment_timing_eligible_retrospective": dict(
            Counter(
                row["assessment_timing_category"]
                for row in decisions
                if row["retrospective_eligible"]
            )
        ),
        "excluded_session_counts": dict(
            Counter(
                row["exclusion_reason"] for row in decisions if row["exclusion_reason"]
            )
        ),
        "completed_evidence_failures": [
            row
            for row in decisions
            if (row["exclusion_reason"] or "").startswith("EVIDENCE_BLOCKED:")
        ],
        "attempt_chronology_policy": "recorded-attempt-sequence-ties-v1",
        "attempt_chronology_handling": [
            {
                "session_id": link["session_id"],
                "student_code": link["student_code"],
                "decisions": link["attempt_chronology_decisions"],
            }
            for link in links
            if link.get("attempt_chronology_decisions")
        ],
        "integrity_quarantine_session_ids": integrity["quarantine"]["session_ids"],
        "configuration": config.model_dump(mode="json"),
        "readiness": ready,
        "interpretation_limits": [
            "Same-day assessment ordering is unknown; no teacher assessment times were invented.",
            "Retrospective data includes same-day and post-assessment gameplay and is not prospective prediction evidence.",
            "Tutor phase is copied from each Game session; teacher-assessment timing does not establish intervention timing.",
            "CSV DOCUMENTED_TEACHER_LEVEL statuses are preserved source claims; original teacher assessment sheets are not supplied.",
            "The same learner's teacher assessment may label multiple sessions; sessions are not independent learners.",
            "Independent revision provenance is known for the original seven only; additional learners' revision status is unknown.",
            "Duration reliability and historic content versions remain unverified; no accuracy or model superiority claim is made.",
            "Accepted timestamp ties establish a validated recorded logical attempt sequence; exact within-millisecond wall-clock order and the historical client build remain unproven.",
        ],
    }
    save_json(output / "researcher_decisions.json", receipt)
    save_json(
        output / "imported_session_verification.json", reviewed.model_dump(mode="json")
    )
    save_json(
        output / "independent_assessments.input.json",
        {
            "schema_version": "game-independent-teacher-assessments-2.3.3",
            "records": [item.model_dump(mode="json") for item in assessments.values()],
        },
    )
    save_json(
        output / "teacher_score_label_provenance.json",
        [item.report() for item in assessments.values()],
    )
    save_json(output / "source_integrity.json", integrity)
    save_json(output / "integrity_quarantine.json", integrity["quarantine"])
    save_json(output / "session_source_links.json", links)
    save_json(
        output / "attempt_chronology_audit.json",
        {
            "policy": report["attempt_chronology_policy"],
            "handling": report["attempt_chronology_handling"],
            "affected_observations": [
                row
                for row in datasets["retrospective"]["observations"]
                if any(
                    item["session_id"] == row["session_id"]
                    for item in report["attempt_chronology_handling"]
                )
            ],
            "affected_model_features": {
                model: [
                    row
                    for row in rows
                    if any(
                        item["session_id"] == row["session_id"]
                        for item in report["attempt_chronology_handling"]
                    )
                ]
                for model, rows in datasets["retrospective"]["features"].items()
            },
            "source_rows_modified": False,
        },
    )
    failure_ids = {row["session_id"] for row in report["completed_evidence_failures"]}
    save_json(
        output / "completed_evidence_failures.json",
        {
            "policy": "Retain complete original rows; existing evidence guards unchanged. No inferred corrections.",
            "failures": report["completed_evidence_failures"],
            "source_evidence": {
                name: [row for row in rows if row["game_session_id"] in failure_ids]
                for name, rows in tables.items()
            },
        },
    )
    write_csv(output / "session_eligibility_and_timing.csv", decisions)
    save_json(
        output / "incomplete_sessions.json",
        [row for row in decisions if row["completion"] != "completed"],
    )
    for name, data in datasets.items():
        folder = output / name
        folder.mkdir()
        save_json(folder / "cleaned_observations.json", data["observations"])
        save_json(folder / "training_readiness.json", ready[name])
        save_json(folder / "feature_definitions.json", data["feature_definitions"])
        for model, rows in data["features"].items():
            save_json(folder / f"{model}_features.json", rows)
    report["input_hashes_unchanged"] = all(
        file_hash(path) == hashes[key] for key, path in inputs.items()
    )
    if not report["input_hashes_unchanged"]:
        raise ValueError(
            "Input evidence changed during preparation; discard this incomplete snapshot"
        )
    save_json(output / "preparation_report.json", report)
    (output / "READINESS_REPORT.md").write_text(
        render_report(report, assessments), encoding="utf-8"
    )
    save_json(
        output / "snapshot_manifest.json",
        {
            "milestone": milestone,
            "complete": True,
            "models_trained": False,
            "files_sha256": {
                str(path.relative_to(output)).replace("\\", "/"): file_hash(path)
                for path in sorted(output.rglob("*"))
                if path.is_file()
            },
            "manifest_hash_scope": "All snapshot files except this manifest; fresh folders only.",
        },
    )
    return report


def render_report(report: dict, assessments: dict) -> str:
    lines = [
        f"# Milestone {report['milestone']} — independent teacher assessments and readiness",
        "",
        "Preparation only. No models trained or saved. Source CSVs/ZIP and earlier snapshots preserved.",
        "",
        "## Researcher verification",
        "",
        f"All {report['researcher_review']['exact_session_ids_validated']} exact IDs validated. "
        f"{report['researcher_review']['compatible_copy_restored_protected_cells']} protected status annotations "
        "restored from the frozen snapshot in a separate import copy. The raw edited sheet remains unchanged.",
        "",
        f"Imported: {report['researcher_review']['imported_decision_counts']}. No decisions rejected after compatibility restoration.",
        "",
        report["researcher_review"]["verification_basis_assessment"],
        "",
        "## Independent teacher evidence",
        "",
        "Dates are researcher-confirmed, date only, Asia/Colombo. Original CSV statuses and conflicting values are preserved.",
        "",
        "| Learner | Original score /10 | Date | Original level | Used level | Classification source |",
        "|---|---:|---|---|---|---|",
    ]
    for code, item in assessments.items():
        lines.append(
            f"| {code} | {item.score} | {item.assessed_on} | {item.original_teacher_level or 'not supplied'} | "
            f"{item.report()['target_level'] or 'BLOCKED'} | {item.classification_source} |"
        )
    for code, item in assessments.items():
        if item.conflict:
            lines += [
                "",
                f"{code}: original {item.score}/10 and {item.original_teacher_level} preserved. "
                f"Resolution: {item.score_level_resolution_reference or 'AWAITING RESEARCHER CLARIFICATION'}. "
                f"Classification source: {item.classification_source}.",
                "",
            ]
    lines += [
        "",
        f"Verified genuine learners / sessions: {report['verified_genuine_learners']} / {report['verified_genuine_sessions']}.",
        f"Candidate completed / incomplete: {report['raw_completed_candidate_sessions']} / {report['incomplete_candidate_sessions']}.",
        f"All 16 independently assessed; learner classes: {report['teacher_assessments']['class_distribution']}.",
        f"Classification sources: {report['teacher_assessments']['classification_source_counts']}.",
        "",
        "## Timing and paired datasets",
        "",
        f"All candidate timing: {report['assessment_timing_all_candidate_sessions']}.",
        f"Eligible retrospective timing: {report['assessment_timing_eligible_retrospective']}.",
        f"Exclusions (primary reasons): {report['excluded_session_counts']}.",
        f"Exact integrity quarantines retained: {report['integrity_quarantine_session_ids']}. "
        "An invalid-code primary exclusion does not erase an overlapping integrity quarantine.",
        "",
    ]
    if report["completed_evidence_failures"]:
        lines += ["### Completed sessions failing existing evidence checks", ""]
        for row in report["completed_evidence_failures"]:
            lines.append(
                f"- {row['student_code']} / `{row['session_id']}`: {row['exclusion_reason']}."
            )
        lines += [
            "",
            "Full unchanged evidence is retained in `completed_evidence_failures.json`. "
            "Review the original event/answer timestamps and attempt sequence separately; "
            "researcher authenticity does not override these checks.",
            "",
        ]
    if report["attempt_chronology_handling"]:
        lines += [
            "### Audited attempt timestamp ties",
            "",
            "The monotonic recorded attempt counter and complete submission events establish logical order. "
            "Exact wall-clock order inside a timestamp tie remains unresolved; CSV and random UUID ordering are ignored.",
            "",
        ]
        for item in report["attempt_chronology_handling"]:
            lines.append(
                f"- {item['student_code']} / `{item['session_id']}`: {len(item['decisions'])} step(s) accepted under `{report['attempt_chronology_policy']}`."
            )
        lines += [
            "",
            "Original rows, timestamps, numbered submission evidence and tie groups are retained in `attempt_chronology_audit.json`.",
            "",
        ]
    for purpose, ready in report["readiness"].items():
        lines += [
            f"### {purpose.capitalize()}",
            "",
            f"Model A / B: {ready['model_a_observations']} / {ready['model_b_observations']} observations; "
            f"{ready['independent_learners']} independent learners.",
            f"Learner classes: {ready['learner_class_distribution']}.",
            f"Observation classes: {ready['observation_class_distribution']}.",
            f"Fixed learner-grouped split: {ready['learner_grouped_split_status']}; "
            f"overall evidence/readiness gate: {ready['mechanical_evaluation_status']}.",
            "",
        ]
        lines += [f"- {reason}" for reason in ready["blocking_reasons"]]
        if ready["fixed_grouped_split"]:
            for partition in ("train", "test"):
                part = ready["fixed_grouped_split"][partition]
                lines.append(
                    f"- Fixed {partition}: {part['learners']} learners, {part['observations']} observations; {part['label_distribution']}."
                )
        lines.append("")
    lines += [
        "## Remaining issues and next step",
        "",
        *[f"- {item}" for item in report["interpretation_limits"]],
        "",
        "Review this snapshot and explicitly agree the analysis purpose before any later training request. "
        "A mechanically feasible retrospective split permits only a preliminary retrospective experiment, "
        "not a prospective or deployment claim. If prospective readiness remains blocked, collect more "
        "verified completed sessions demonstrably before independently timed assessments, with enough "
        "learners in every class for the unchanged fixed learner-grouped split. Never search seeds or "
        "lower guardrails to obtain a favorable split.",
        "",
        "The snapshot manifest records SHA256 for every generated artifact except the manifest itself. "
        "The command refuses to overwrite an existing output folder.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("export", "sheet", "assessment-csv", "snapshot", "baseline", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--milestone", choices=("2.3.3", "2.3.4"), default="2.3.3")
    parser.add_argument(
        "--score-rubric-resolution",
        action="append",
        default=[],
        metavar="STUDENT_CODE=RESEARCHER_REFERENCE",
    )
    args = parser.parse_args()
    resolutions = {}
    for value in args.score_rubric_resolution:
        code, separator, reference = value.partition("=")
        if not separator or not reference.strip() or code in resolutions:
            parser.error(
                "Resolution requires one unique STUDENT_CODE=RESEARCHER_REFERENCE"
            )
        resolutions[code] = reference
    result = prepare(
        export=args.export,
        sheet=args.sheet,
        assessment_csv=args.assessment_csv,
        snapshot_path=args.snapshot,
        baseline_path=args.baseline,
        output=args.output,
        resolutions=resolutions,
        milestone=args.milestone,
    )
    print(
        json.dumps(
            {"output": str(args.output), "readiness": result["readiness"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
