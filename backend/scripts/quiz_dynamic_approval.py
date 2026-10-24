"""Audit the isolated PP1 Quiz bank and keep version-bound approval evidence.

This script reads only ../tmp/quiz_dynamic_demo.sqlite (SQLite read-only mode).
It never updates Quiz rows, imports app settings, or opens a remote database.
Approval manifests are written under ../tmp/ with exclusive creation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "tmp" / "quiz_dynamic_demo.sqlite"
BANK_PATH = Path(__file__).with_name("quiz_dynamic_60_DRAFT.json")
REVIEW_PATH = Path(__file__).with_name("quiz_dynamic_60_teacher_review.md")
PENDING_PATH = ROOT / "tmp" / "quiz_dynamic_approval_pending.json"
FINAL_PATH = ROOT / "tmp" / "quiz_dynamic_approval_record.json"
BANK_VERSION = "pp1_dynamic_v1_DRAFT"
NAMESPACE = uuid.UUID("ee0379d7-8bbd-421b-9c07-4dfa86109831")
SCOPES = ("question_content", "sinhala_wording", "distractor_tags")
QUESTION_FIELDS = (
    "question_code", "bank_version", "logical_slot", "concept_id",
    "subconcept_code", "difficulty_level", "question_text_en", "answer",
)


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def item_fingerprints(item: dict) -> dict[str, str]:
    options = sorted(item["options"], key=lambda option: option["option_code"])
    question_content = {key: item[key] for key in QUESTION_FIELDS}
    question_content["options"] = [
        {key: option[key] for key in ("option_code", "text", "is_correct")}
        for option in options
    ]
    sinhala_wording = {
        "question_text_si": item["question_text_si"],
        # The draft bank has numeric options; the seed uses their same text for SI.
        "options": [{"option_code": option["option_code"], "option_text_si": option["text"]}
                    for option in options],
    }
    distractor_tags = {
        "options": [{"option_code": option["option_code"],
                     "misconception_code": option["misconception_code"]}
                    for option in options]
    }
    return {"question_content": digest(question_content),
            "sinhala_wording": digest(sinhala_wording),
            "distractor_tags": digest(distractor_tags)}


def snapshot() -> dict:
    if not DB_PATH.is_file():
        raise ValueError(f"Isolated development database is missing: {DB_PATH}")
    bank_bytes = BANK_PATH.read_bytes()
    bank = json.loads(bank_bytes.decode("utf-8"))
    if (len(bank) != 60 or len({item["question_code"] for item in bank}) != 60
        or Counter(item["logical_slot"] for item in bank)
           != {f"S{i:02d}": 6 for i in range(1, 11)}
        or Counter(item["difficulty_level"] for item in bank)
           != {"easy": 24, "medium": 24, "hard": 12}):
        raise ValueError("The source bank is not the expected 60-item, 10-slot draft")

    connection = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    try:
        connection.execute("BEGIN")  # One consistent read snapshot of the local bank.
        saved = connection.execute(
            "SELECT id, question_code, bank_version, logical_slot, concept_id, "
            "subconcept_code, question_type, question_text_en, question_text_si, "
            "difficulty_level, assessment_use, correct_answer_text, teacher_validated, "
            "is_active FROM quiz_questions WHERE bank_version=?", (BANK_VERSION,)
        ).fetchall()
        if len(saved) != 60:
            raise ValueError(f"Expected 60 local dynamic questions, found {len(saved)}")
        saved_by_code = {row["question_code"]: row for row in saved}
        if len(saved_by_code) != 60:
            raise ValueError("Duplicate local question codes")

        fingerprints = []
        validated_count = 0
        for item in sorted(bank, key=lambda value: value["question_code"]):
            code = item["question_code"]
            row = saved_by_code.get(code)
            if row is None:
                raise ValueError(f"Missing local question: {code}")
            expected = {
                "id": uuid.uuid5(NAMESPACE, code).hex,
                "question_code": code,
                "bank_version": BANK_VERSION,
                "logical_slot": item["logical_slot"],
                "concept_id": item["concept_id"],
                "subconcept_code": item["subconcept_code"],
                "question_type": "multiple_choice",
                "question_text_en": item["question_text_en"],
                "question_text_si": item["question_text_si"],
                "difficulty_level": item["difficulty_level"],
                "assessment_use": "pre",
                "correct_answer_text": item["answer"],
                "is_active": 1,
            }
            if any(row[key] != value for key, value in expected.items()):
                raise ValueError(f"Local question content differs from source bank: {code}")
            validated_count += int(row["teacher_validated"])
            if (item["bank_version"] != BANK_VERSION or item["teacher_validated"] is not False
                or item["review_status"] != "DRAFT_REVIEW"
                or item["research_use"] != "DEVELOPMENT_ONLY"):
                raise ValueError(f"Unexpected draft metadata: {code}")

            options = connection.execute(
                "SELECT id, option_code, option_text_en, option_text_si, is_correct, "
                "misconception_code FROM quiz_question_options WHERE question_id=? "
                "ORDER BY option_code", (row["id"],)
            ).fetchall()
            expected_options = sorted(item["options"], key=lambda value: value["option_code"])
            if len(options) != 4 or {option["option_code"] for option in options} != set("ABCD"):
                raise ValueError(f"Invalid local options: {code}")
            for actual, source in zip(options, expected_options):
                if (actual["id"] != uuid.uuid5(NAMESPACE, f"{code}:{source['option_code']}").hex
                    or actual["option_code"] != source["option_code"]
                    or actual["option_text_en"] != source["text"]
                    or actual["option_text_si"] != source["text"]
                    or bool(actual["is_correct"]) != source["is_correct"]
                    or actual["misconception_code"] != source["misconception_code"]):
                    raise ValueError(f"Local option differs from source bank: {code}")
            fingerprints.append({
                "question_code": code,
                "question_id": str(uuid.UUID(hex=row["id"])),
                "logical_slot": item["logical_slot"],
                **item_fingerprints(item),
            })
        return {
            "bank_version": BANK_VERSION,
            "source_bank_sha256": hashlib.sha256(bank_bytes).hexdigest(),
            "review_sheet_sha256": file_digest(REVIEW_PATH),
            "content_fingerprints_sha256": digest(fingerprints),
            "question_count": len(fingerprints),
            "teacher_validated_true_count": validated_count,
            "items": fingerprints,
        }
    finally:
        connection.close()


def write_new(path: Path, content: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(content, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def matching_snapshot(record: dict, current: dict) -> bool:
    return all(record.get(key) == current[key] for key in (
        "bank_version", "source_bank_sha256", "content_fingerprints_sha256",
        "question_count", "teacher_validated_true_count", "items",
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--verify", action="store_true", help="Read-only source/SQLite comparison")
    action.add_argument("--prepare", action="store_true", help="Create a pending local manifest")
    action.add_argument("--finalize", action="store_true", help="Create an evidence-linked approval record")
    parser.add_argument("--approval-date", help="Teacher-reported approval date, YYYY-MM-DD")
    parser.add_argument("--reported-scopes", nargs="+", choices=SCOPES,
                        help="Scopes reported approved; confirmation remains pending evidence")
    parser.add_argument("--approved-scopes", nargs="+", choices=SCOPES,
                        help="Scopes explicitly supported by the supplied evidence")
    parser.add_argument("--evidence-ref", help="Opaque reference to private approval evidence")
    parser.add_argument("--evidence-sha256", help="SHA-256 of the private evidence file")
    parser.add_argument("--reviewed-bank-sha256", help="Bank SHA-256 cited by the evidence")
    args = parser.parse_args()
    current = snapshot()
    print(f"Verified {current['question_count']} source/SQLite items; bank SHA-256: "
          f"{current['source_bank_sha256']}")
    print(f"Local teacher_validated=true: {current['teacher_validated_true_count']}/60")

    if args.prepare:
        if not args.approval_date or not args.reported_scopes:
            parser.error("--prepare requires --approval-date and --reported-scopes")
        date.fromisoformat(args.approval_date)
        if current["teacher_validated_true_count"]:
            raise ValueError("Dynamic selection depends on all draft validation flags remaining false")
        record = {
            "record_version": 1,
            "status": "reported_approval_evidence_pending",
            "approval_date_reported": args.approval_date,
            "reported_scopes": sorted(set(args.reported_scopes)),
            "evidence_reference": None,
            "notice": "User report only; not an authenticated teacher sign-off or research-use approval.",
            "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
            **current,
        }
        write_new(PENDING_PATH, record)
        print(f"Created pending local manifest: {PENDING_PATH}")
    elif args.finalize:
        if not PENDING_PATH.is_file():
            raise ValueError("Prepare the pending manifest first")
        pending = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        if not matching_snapshot(pending, current):
            raise ValueError("The bank or local SQLite contents changed after preparation")
        if not args.approved_scopes or not args.evidence_ref or not args.evidence_sha256 or not args.reviewed_bank_sha256:
            parser.error("--finalize requires scopes, evidence reference/hash, and reviewed bank hash")
        if not set(args.approved_scopes) <= set(pending["reported_scopes"]):
            raise ValueError("Evidence scopes exceed the reported approval scopes")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", args.evidence_sha256):
            raise ValueError("Evidence SHA-256 must have 64 hexadecimal characters")
        if args.reviewed_bank_sha256.lower() != current["source_bank_sha256"]:
            raise ValueError("Evidence does not identify this exact source bank version")
        if current["teacher_validated_true_count"]:
            raise ValueError("Dynamic selection depends on all draft validation flags remaining false")
        final = {
            **pending,
            "status": "evidence_reference_recorded",
            "approved_scopes": sorted(set(args.approved_scopes)),
            "pending_scopes": sorted(set(SCOPES) - set(args.approved_scopes)),
            "evidence_reference": args.evidence_ref.strip(),
            "evidence_sha256": args.evidence_sha256.lower(),
            "reviewed_bank_sha256": args.reviewed_bank_sha256.lower(),
            "notice": "Reference and hash recorded; human review must authenticate evidence and scope.",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        if not final["evidence_reference"]:
            raise ValueError("Evidence reference must not be blank")
        write_new(FINAL_PATH, final)
        print(f"Created evidence-linked local record: {FINAL_PATH}")
    else:
        for path in (PENDING_PATH, FINAL_PATH):
            if path.is_file():
                record = json.loads(path.read_text(encoding="utf-8"))
                if not matching_snapshot(record, current):
                    raise ValueError(f"Manifest no longer matches the source and SQLite bank: {path}")
                print(f"Matching {record['status']} manifest: {path}")


if __name__ == "__main__":
    main()
