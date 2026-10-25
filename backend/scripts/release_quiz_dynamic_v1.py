"""Release the teacher-approved dynamic Quiz bank as pp1_dynamic_v1.

The approved content is the reviewed draft file, pinned by SHA-256 (teacher
approval 2026-10-21, signed copy pending; see quiz_dynamic_60_teacher_review.md).
The draft file is not edited. Released rows get their own bank_version and
teacher_validated=true. Misconception mappings must already exist; their
taxonomy validation is a separate review and is not changed here.

From backend/:
  python -m scripts.release_quiz_dynamic_v1                                   # validate files only
  python -m scripts.release_quiz_dynamic_v1 --configured-database             # read-only dry run
  python -m scripts.release_quiz_dynamic_v1 --configured-database --apply     # insert
--configured-database uses DATABASE_URL from settings; --database-url URL targets another database.
"""

import argparse
import hashlib
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.modules.quiz.models import MisconceptionMapping, QuizQuestion, QuizQuestionOption
from scripts.seed_quiz_dynamic import BANK_PATH, MAPPING_NAMES, load_bank

RELEASE_VERSION = "pp1_dynamic_v1"
APPROVED_BANK_SHA256 = "c3c251674d54b1848ddd0adde159fb33346b98233850ccb02539e86c93da83b8"
REVIEW_PATH = BANK_PATH.with_name("quiz_dynamic_60_teacher_review.md")
NAMESPACE = uuid.UUID("5d0f6f2e-8f3b-4c1e-9b7a-2f4c6a1d9e30")
SOURCE_REF = "Teacher-approved 2026-10-21 (signed copy pending); bank SHA-256 c3c25167"


def load_released_bank() -> list[dict]:
    if hashlib.sha256(BANK_PATH.read_bytes()).hexdigest() != APPROVED_BANK_SHA256:
        raise ValueError("Bank file differs from the teacher-approved version; re-approval required")
    review = REVIEW_PATH.read_text(encoding="utf-8")
    if review.count("distractor tags approved: Approved") != 60:
        raise ValueError("Teacher review does not record all 60 items as approved")
    return [{**item, "bank_version": RELEASE_VERSION} for item in load_bank()]


def release_bank(database: Session, bank: list[dict], apply: bool) -> tuple[int, int]:
    """Return (to insert or inserted, already released). Never overwrites."""
    existing_codes = set(database.scalars(select(MisconceptionMapping.misconception_code)))
    if missing := set(MAPPING_NAMES) - existing_codes:
        raise ValueError(f"Misconception mappings missing: {sorted(missing)}")
    inserted = skipped = 0
    for item in bank:
        existing = database.scalar(select(QuizQuestion).where(QuizQuestion.question_code == item["question_code"]))
        if existing:
            options = database.scalars(select(QuizQuestionOption).where(QuizQuestionOption.question_id == existing.id)).all()
            actual = {o.option_code: (o.option_text_en, o.is_correct, o.misconception_code) for o in options}
            expected = {o["option_code"]: (o["text"], o["is_correct"], o["misconception_code"]) for o in item["options"]}
            if (existing.bank_version != RELEASE_VERSION or not existing.teacher_validated
                or existing.logical_slot != item["logical_slot"]
                or existing.question_text_en != item["question_text_en"]
                or existing.question_text_si != item["question_text_si"]
                or existing.subconcept_code != item["subconcept_code"]
                or existing.difficulty_level != item["difficulty_level"] or actual != expected):
                raise ValueError(f"Existing item differs; no overwrite: {item['question_code']}")
            skipped += 1
            continue
        inserted += 1
        if not apply:
            continue
        question = QuizQuestion(
            id=uuid.uuid5(NAMESPACE, item["question_code"]), question_code=item["question_code"],
            bank_version=RELEASE_VERSION, logical_slot=item["logical_slot"], concept_id="linear_equations",
            subconcept_code=item["subconcept_code"], question_type="multiple_choice",
            question_text_en=item["question_text_en"], question_text_si=item["question_text_si"],
            difficulty_level=item["difficulty_level"], assessment_use="pre",
            correct_answer_text=item["answer"], source_ref_en=SOURCE_REF, source_ref_si=SOURCE_REF,
            teacher_validated=True, is_active=True,
        )
        database.add(question)
        database.flush()
        database.add_all(QuizQuestionOption(
            id=uuid.uuid5(NAMESPACE, f"{item['question_code']}:{o['option_code']}"),
            question_id=question.id, option_code=o["option_code"], option_text_en=o["text"],
            option_text_si=o["text"], is_correct=o["is_correct"], misconception_code=o["misconception_code"],
        ) for o in item["options"])
    database.flush()
    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--configured-database", action="store_true")
    target.add_argument("--database-url")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    bank = load_released_bank()
    print(f"Validated 60 approved items for {RELEASE_VERSION} (bank SHA-256 {APPROVED_BANK_SHA256[:8]}).")
    if not (args.configured_database or args.database_url):
        if args.apply:
            raise SystemExit("--apply needs --configured-database or --database-url")
        return
    if args.configured_database:
        from app.core.config import settings
        raw = settings.database_url
    else:
        raw = args.database_url
    url = make_url(raw)
    print(f"Target: {url.get_backend_name()} {url.host or url.database}")
    engine = create_engine(raw)
    try:
        if args.apply:
            with Session(engine) as database, database.begin():
                inserted, skipped = release_bank(database, bank, apply=True)
            print(f"Inserted {inserted}; skipped {skipped} already released items.")
        else:
            with Session(engine) as database:
                pending, skipped = release_bank(database, bank, apply=False)
                database.rollback()
            print(f"Dry run: would insert {pending}; {skipped} already released. Re-run with --apply.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
