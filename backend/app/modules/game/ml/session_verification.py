"""Researcher review sheets and validated, offline imports of exact decisions."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .collection_research import (
    CLASSES,
    COHORT,
    DEVELOPMENT_SESSIONS,
    INVALID_CODE_DECISION,
    INVALID_CODE_REASON,
    CollectionReview,
    VerifiedSession,
    audit_collection,
    has_invalid_student_code,
    proficiency,
    read_export,
    write_outputs,
)

FIELDS = (
    "game_session_id",
    "student_code",
    "game_mode",
    "started_at",
    "completed_at",
    "completion_status",
    "answer_count",
    "teacher_label",
    "existing_verification_status",
    "researcher_decision",
    "verification_basis",
    "review_notes",
)
READ_ONLY_FIELDS = FIELDS[:9]
DECISIONS = frozenset(
    {"RESEARCH_VERIFIED", "DEVELOPMENT_TEST", "UNKNOWN", INVALID_CODE_DECISION}
)


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def fingerprint(provenance: dict) -> dict:
    return {key: provenance.get(key) for key in ("file_sha256", "zip_sha256")}


def review_rows(
    tables: dict, provenance: dict, baseline: CollectionReview
) -> list[dict]:
    """Review candidate learners, invalid codes and exact established decisions."""
    ids = [row["game_session_id"] for row in tables["game_sessions"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Source contains duplicate session IDs")
    if set(baseline.verified_sessions) - set(ids):
        raise ValueError("Previously verified sessions are missing from this export")
    audited = audit_collection(tables, provenance, baseline)
    statuses = {row["session_id"]: row for row in audited["session_review"]}
    rows = []
    for source in sorted(
        tables["game_sessions"], key=lambda row: row["game_session_id"]
    ):
        sid = source["game_session_id"]
        if (
            source["student_code"] not in COHORT
            and sid not in DEVELOPMENT_SESSIONS
            and sid not in baseline.development_sessions
            and sid not in baseline.verified_sessions
            and not has_invalid_student_code(source)
        ):
            continue
        decision, basis = "UNKNOWN", ""
        if has_invalid_student_code(source):
            decision, basis = INVALID_CODE_DECISION, INVALID_CODE_REASON
        elif sid in DEVELOPMENT_SESSIONS:
            decision, basis = (
                "DEVELOPMENT_TEST",
                "Exact researcher-confirmed development session ID",
            )
        elif sid in baseline.development_sessions:
            decision, basis = "DEVELOPMENT_TEST", baseline.development_sessions[sid]
        elif sid in baseline.verified_sessions:
            decision, basis = (
                "RESEARCH_VERIFIED",
                baseline.verified_sessions[sid].source_reference,
            )
        teacher_score = baseline.teacher_scores.get(source["student_code"])
        rows.append(
            {
                "game_session_id": sid,
                "student_code": source["student_code"],
                "game_mode": source["game_type"],
                "started_at": source["started_at"],
                "completed_at": source["completed_at"],
                "completion_status": source["status"],
                "answer_count": str(statuses[sid]["answers"]),
                "teacher_label": proficiency(teacher_score)
                if teacher_score is not None
                else "",
                "existing_verification_status": statuses[sid]["decision"],
                "researcher_decision": decision,
                "verification_basis": basis,
                "review_notes": "",
            }
        )
    return rows


def save_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def generate_sheet(
    tables: dict, provenance: dict, baseline: CollectionReview, output: Path
) -> dict:
    rows = review_rows(tables, provenance, baseline)
    baseline_data = baseline.model_dump(mode="json")
    snapshot = {
        "schema_version": "game-session-review-sheet-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_fingerprint": fingerprint(provenance),
        "baseline_sha256": digest(baseline_data),
        "read_only_rows": [{key: row[key] for key in READ_ONLY_FIELDS} for row in rows],
    }
    output.mkdir(parents=True, exist_ok=False)
    with (output / "session_review_sheet.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    save_json(output / "review_baseline.json", baseline_data)
    save_json(output / "review_snapshot.json", snapshot)
    result = {
        "sheet": str((output / "session_review_sheet.csv").resolve()),
        "review_sheet_counts": dict(
            Counter(row["researcher_decision"] for row in rows)
        ),
        "rows": len(rows),
        "outside_review_scope_sessions": len(tables["game_sessions"]) - len(rows),
    }
    save_json(output / "generation_summary.json", result)
    return result


def import_decisions(
    sheet: Path,
    snapshot: dict,
    tables: dict,
    provenance: dict,
    baseline: CollectionReview,
) -> tuple[CollectionReview, dict]:
    """Reject changed source/context, omissions and conflicting decisions first."""
    if snapshot.get("schema_version") != "game-session-review-sheet-v1":
        raise ValueError("Unsupported review snapshot version")
    if snapshot.get("source_fingerprint") != fingerprint(provenance):
        raise ValueError("Source export changed since the review sheet was generated")
    if snapshot.get("baseline_sha256") != digest(baseline.model_dump(mode="json")):
        raise ValueError("Review baseline changed since sheet generation")
    expected_rows = review_rows(tables, provenance, baseline)
    readonly = [{key: row[key] for key in READ_ONLY_FIELDS} for row in expected_rows]
    if snapshot.get("read_only_rows") != readonly:
        raise ValueError("Review snapshot conflicts with source session context")
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError(
                "Review sheet must preserve the documented columns and order"
            )
        rows = list(reader)
    originals = {row["game_session_id"]: row for row in tables["game_sessions"]}
    expected = {row["game_session_id"]: row for row in expected_rows}
    seen = set()
    updated = baseline.model_dump(mode="json")
    decisions = []
    for row in rows:
        if set(row) != set(FIELDS) or any(value is None for value in row.values()):
            raise ValueError("Review sheet row has missing or extra cells")
        sid = row["game_session_id"]
        if sid not in originals:
            raise ValueError(
                f"Reviewed session does not exist in the source export: {sid}"
            )
        if sid in seen:
            raise ValueError(
                f"Duplicate/conflicting review decisions for session: {sid}"
            )
        seen.add(sid)
        if sid not in expected:
            raise ValueError(
                f"Session is outside this review sheet's original scope: {sid}"
            )
        for key in READ_ONLY_FIELDS:
            if row[key] != expected[sid][key]:
                raise ValueError(
                    f"Read-only field {key} does not match source/baseline for {sid}"
                )
        decision = (row.get("researcher_decision") or "").strip()
        basis = (row.get("verification_basis") or "").strip()
        if decision not in DECISIONS:
            raise ValueError(f"Invalid researcher decision for {sid}: {decision!r}")
        invalid_code = has_invalid_student_code(originals[sid])
        if invalid_code and decision != INVALID_CODE_DECISION:
            raise ValueError(f"Invalid student-code exclusion must be preserved: {sid}")
        if not invalid_code and decision == INVALID_CODE_DECISION:
            raise ValueError(f"Session does not record an excluded invalid code: {sid}")
        if not invalid_code and (
            sid in DEVELOPMENT_SESSIONS or sid in baseline.development_sessions
        ):
            if decision != "DEVELOPMENT_TEST":
                raise ValueError(
                    f"Previously confirmed development exclusion must be preserved: {sid}"
                )
        if (
            not invalid_code
            and sid in baseline.verified_sessions
            and decision != "RESEARCH_VERIFIED"
        ):
            raise ValueError(f"Previously verified session must be preserved: {sid}")
        if decision != "UNKNOWN" and not basis:
            raise ValueError(f"A verification_basis is required for {decision}: {sid}")
        if decision == "RESEARCH_VERIFIED":
            source = originals[sid]
            approval = VerifiedSession(
                student_code=source["student_code"],
                concept=source["concept_id"],
                game_type=source["game_type"],
                source_reference=basis,
            )
            updated["verified_sessions"][sid] = approval.model_dump(mode="json")
        elif decision == "DEVELOPMENT_TEST":
            updated["development_sessions"][sid] = basis
        elif decision == INVALID_CODE_DECISION:
            # The researcher's invalid-code correction overrides any older
            # approval in this fresh derived review, never the raw records.
            updated["verified_sessions"].pop(sid, None)
        decisions.append(
            {
                "game_session_id": sid,
                "student_code": row["student_code"],
                "researcher_decision": decision,
                "verification_basis": basis,
                "review_notes": row.get("review_notes") or "",
            }
        )
    if seen != set(expected):
        raise ValueError(
            "Review sheet omits original session rows; keep undecided rows as UNKNOWN"
        )
    reviewed = CollectionReview.model_validate_json(json.dumps(updated))
    receipt = {
        "imported_at_utc": datetime.now(UTC).isoformat(),
        "review_sheet_sha256": hashlib.sha256(sheet.read_bytes()).hexdigest(),
        "review_snapshot_sha256": digest(snapshot),
        "updated_review_sha256": digest(updated),
        "source_fingerprint": fingerprint(provenance),
        "review_sheet_counts": dict(
            Counter(row["researcher_decision"] for row in decisions)
        ),
        "decisions": decisions,
        "source_records_modified": False,
    }
    return reviewed, receipt


def apply_sheet(
    sheet: Path,
    snapshot: dict,
    tables: dict,
    provenance: dict,
    baseline: CollectionReview,
    config,
    output: Path,
    *,
    train: bool = False,
) -> dict:
    if output.exists():
        raise FileExistsError("Output already exists; choose a fresh import directory")
    reviewed, receipt = import_decisions(sheet, snapshot, tables, provenance, baseline)
    provenance = {**provenance, "researcher_review_import": receipt}
    audited = audit_collection(tables, provenance, reviewed)
    result = write_outputs(audited, reviewed, config, output, train=train)
    save_json(output / "researcher_decisions.json", receipt)
    save_json(
        output / "incomplete_sessions.json",
        [
            row
            for row in audited["session_review"]
            if row["completion"] != "completed"
            or row["saved_assessment_complete"] != "True"
        ],
    )
    save_json(
        output / "unknown_sessions.json",
        [
            row
            for row in audited["session_review"]
            if row["decision"] == "REVIEW REQUIRED"
        ],
    )
    return {
        **result,
        "review_sheet_counts": receipt["review_sheet_counts"],
        "audit_summary": audited["summary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser(
        "generate",
        help="Create a fresh editable review sheet; never approves unknown sessions",
    )
    generate.add_argument("--export", type=Path, required=True)
    generate.add_argument("--review", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    imported = commands.add_parser(
        "import", help="Validate decisions and run existing evidence/training gates"
    )
    imported.add_argument("--export", type=Path, required=True)
    imported.add_argument("--sheet", type=Path, required=True)
    imported.add_argument("--snapshot", type=Path, required=True)
    imported.add_argument("--output", type=Path, required=True)
    imported.add_argument("--training-config", type=Path)
    imported.add_argument("--train", action="store_true")
    args = parser.parse_args()
    try:
        tables, provenance = read_export(args.export)
        if args.command == "generate":
            baseline = CollectionReview.model_validate_json(
                args.review.read_text(encoding="utf-8")
            )
            result = generate_sheet(tables, provenance, baseline, args.output)
        else:
            from .research_training import ExperimentConfig

            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
            baseline = CollectionReview.model_validate_json(
                (args.snapshot.parent / "review_baseline.json").read_text(
                    encoding="utf-8"
                )
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
                    "Use the existing proficiency mastery target, exact rubric classes and empty common context"
                )
            result = apply_sheet(
                args.sheet,
                snapshot,
                tables,
                provenance,
                baseline,
                config,
                args.output,
                train=args.train,
            )
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Offline session review failed: {error}\n")


if __name__ == "__main__":
    main()
