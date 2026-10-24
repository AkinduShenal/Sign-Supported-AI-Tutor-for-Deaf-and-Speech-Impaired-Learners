"""Import the 60 review-pending Quiz items into an isolated local database.

From backend/: python -m scripts.seed_quiz_dynamic --database-url sqlite:///quiz_demo.db --apply
The URL is mandatory; no application DATABASE_URL or .env is consulted.
"""

import argparse
import json
import uuid
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.modules.quiz.models import MisconceptionMapping, QuizQuestion, QuizQuestionOption

BANK_PATH = Path(__file__).with_name("quiz_dynamic_60_DRAFT.json")
VERSION = "pp1_dynamic_v1_DRAFT"
NAMESPACE = uuid.UUID("ee0379d7-8bbd-421b-9c07-4dfa86109831")
MAPPING_NAMES = {
    "inverse_operation": "Inverse operation error",
    "sign_error": "Sign error",
    "arithmetic_error": "Arithmetic error",
    "concept_confusion": "Concept confusion",
}


def require_local_url(raw: str) -> None:
    url = make_url(raw)
    if url.get_backend_name() == "sqlite":
        return
    if url.get_backend_name() == "postgresql" and url.host in {"localhost", "127.0.0.1", "::1"}:
        return
    raise ValueError("Dynamic Quiz import accepts only an explicit local SQLite/PostgreSQL URL")


def load_bank() -> list[dict]:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    if len(bank) != 60 or len({q["question_code"] for q in bank}) != 60:
        raise ValueError("Expected 60 unique draft questions")
    if Counter(q["logical_slot"] for q in bank) != {f"S{i:02d}": 6 for i in range(1, 11)}:
        raise ValueError("Expected six variants per slot")
    if Counter(q["difficulty_level"] for q in bank) != {"easy": 24, "medium": 24, "hard": 12}:
        raise ValueError("Unexpected difficulty distribution")
    for q in bank:
        options = q["options"]
        if (q["bank_version"] != VERSION or q["teacher_validated"] is not False
            or q["review_status"] != "DRAFT_REVIEW" or q["research_use"] != "DEVELOPMENT_ONLY"
            or q["concept_id"] != "linear_equations" or not q["question_text_si"]
            or len(options) != 4 or {o["option_code"] for o in options} != set("ABCD")
            or len({o["text"] for o in options}) != 4
            or sum(o["is_correct"] is True for o in options) != 1
            or next(o["text"] for o in options if o["is_correct"]) != q["answer"]
            or any(o["misconception_code"] not in (set(MAPPING_NAMES) | {None}) for o in options)):
            raise ValueError(f"Invalid draft item: {q['question_code']}")
    return bank


def seed_bank(database: Session, bank: list[dict]) -> tuple[int, int]:
    for code, name in MAPPING_NAMES.items():
        if database.scalar(select(MisconceptionMapping).where(MisconceptionMapping.misconception_code == code)) is None:
            database.add(MisconceptionMapping(concept_id="linear_equations", misconception_code=code,
                                              name_en=name, teacher_validated=False,
                                              validation_notes="PP1 draft: teacher review pending"))
    database.flush()
    inserted = skipped = 0
    for item in bank:
        existing = database.scalar(select(QuizQuestion).where(QuizQuestion.question_code == item["question_code"]))
        if existing:
            options = database.scalars(select(QuizQuestionOption).where(QuizQuestionOption.question_id == existing.id)).all()
            actual = {o.option_code: (o.option_text_en, o.is_correct, o.misconception_code) for o in options}
            expected = {o["option_code"]: (o["text"], o["is_correct"], o["misconception_code"]) for o in item["options"]}
            if (existing.bank_version != VERSION or existing.logical_slot != item["logical_slot"]
                or existing.question_text_en != item["question_text_en"] or existing.question_text_si != item["question_text_si"]
                or existing.subconcept_code != item["subconcept_code"] or existing.difficulty_level != item["difficulty_level"]
                or existing.teacher_validated or actual != expected):
                raise ValueError(f"Existing item differs; no overwrite: {item['question_code']}")
            skipped += 1
            continue
        question = QuizQuestion(
            id=uuid.uuid5(NAMESPACE, item["question_code"]), question_code=item["question_code"],
            bank_version=VERSION, logical_slot=item["logical_slot"], concept_id="linear_equations",
            subconcept_code=item["subconcept_code"], question_type="multiple_choice",
            question_text_en=item["question_text_en"], question_text_si=item["question_text_si"],
            difficulty_level=item["difficulty_level"], assessment_use="pre",
            correct_answer_text=item["answer"], source_ref_en="PP1 draft; teacher review pending",
            source_ref_si="PP1 draft; teacher review pending", teacher_validated=False, is_active=True,
        )
        database.add(question)
        database.flush()
        database.add_all(QuizQuestionOption(
            id=uuid.uuid5(NAMESPACE, f"{item['question_code']}:{o['option_code']}"),
            question_id=question.id, option_code=o["option_code"], option_text_en=o["text"],
            option_text_si=o["text"], is_correct=o["is_correct"], misconception_code=o["misconception_code"],
        ) for o in item["options"])
        inserted += 1
    database.flush()
    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require_local_url(args.database_url)
    bank = load_bank()
    if not args.apply:
        print("Validated 60 draft items. Dry run; no database connection made.")
        return
    engine = create_engine(args.database_url)
    with Session(engine) as database, database.begin():
        inserted, skipped = seed_bank(database, bank)
    print(f"Inserted {inserted}; skipped {skipped} matching items")


if __name__ == "__main__": main()
