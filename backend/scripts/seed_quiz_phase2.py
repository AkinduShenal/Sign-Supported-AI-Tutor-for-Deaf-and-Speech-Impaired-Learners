"""Explicit development seed for the review-pending pre-tutor question bank.

From backend/: python -m scripts.seed_quiz_phase2 --apply
Without --apply, the script only reports what it would add. It never runs at startup.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.quiz.models import (
    MisconceptionMapping,
    QuizQuestion,
    QuizQuestionOption,
)


BANK_PATH = Path(__file__).with_name("quiz_pre_prototype.json")
REVIEW_NOTE = "Development prototype; teacher and Sinhala wording review pending."


def load_bank() -> dict:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    questions = bank["questions"]
    codes = [question["code"] for question in questions]
    if (
        bank["status"] != "development_prototype_teacher_review_pending"
        or bank["concept_id"] != "linear_equations"
        or bank["assessment_use"] != "pre"
        or len(questions) != 10
        or len(set(codes)) != 10
        or Counter(question["difficulty"] for question in questions)
        != {"easy": 4, "medium": 4, "hard": 2}
    ):
        raise ValueError("Prototype bank must contain ten unique pre questions (4/4/2)")
    mapping_codes = {item["code"] for item in bank["misconceptions"]}
    for question in questions:
        options = question["options"]
        if (
            not question["text_en"]
            or not question["text_si"]
            or len(options) != 4
            or {option[0] for option in options} != {"A", "B", "C", "D"}
            or sum(option[2] is True for option in options) != 1
            or any(option[3] not in mapping_codes | {None} for option in options)
        ):
            raise ValueError(
                f"Invalid options or bilingual wording for {question['code']}"
            )
    return bank


def seed_bank(database: Session, bank: dict) -> tuple[int, int]:
    codes = {item["code"] for item in bank["questions"]}
    active_pre = database.scalars(
        select(QuizQuestion).where(
            QuizQuestion.concept_id == bank["concept_id"],
            QuizQuestion.assessment_use.in_(("pre", "both")),
            QuizQuestion.is_active.is_(True),
        )
    ).all()
    foreign_codes = {item.question_code for item in active_pre} - codes
    if foreign_codes:
        raise ValueError(
            "Other active pre questions exist; seed stopped to protect the ten-question assessment: "
            + ", ".join(sorted(foreign_codes))
        )

    for item in bank["misconceptions"]:
        existing = database.scalar(
            select(MisconceptionMapping).where(
                MisconceptionMapping.misconception_code == item["code"]
            )
        )
        if existing is None:
            database.add(
                MisconceptionMapping(
                    concept_id=bank["concept_id"],
                    misconception_code=item["code"],
                    name_en=item["name_en"],
                    teacher_validated=False,
                    validation_notes=REVIEW_NOTE,
                )
            )
    database.flush()

    inserted = skipped = 0
    for item in bank["questions"]:
        existing = database.scalar(
            select(QuizQuestion).where(QuizQuestion.question_code == item["code"])
        )
        if existing is not None:
            options = database.scalars(
                select(QuizQuestionOption).where(
                    QuizQuestionOption.question_id == existing.id
                )
            ).all()
            if (
                existing.concept_id != bank["concept_id"]
                or existing.assessment_use != "pre"
                or existing.difficulty_level != item["difficulty"]
                or not existing.is_active
                or len(options) != 4
                or {option.option_code for option in options} != {"A", "B", "C", "D"}
                or sum(option.is_correct for option in options) != 1
            ):
                raise ValueError(
                    f"Existing question {item['code']} needs manual review"
                )
            skipped += 1
            continue

        question = QuizQuestion(
            question_code=item["code"],
            concept_id=bank["concept_id"],
            subconcept_code=item["subconcept"],
            question_type="multiple_choice",
            question_text_en=item["text_en"],
            question_text_si=item["text_si"],
            difficulty_level=item["difficulty"],
            assessment_use="pre",
            source_ref_en=REVIEW_NOTE,
            source_ref_si=REVIEW_NOTE,
            teacher_validated=False,
            is_active=True,
        )
        database.add(question)
        database.flush()
        database.add_all(
            QuizQuestionOption(
                question_id=question.id,
                option_code=code,
                option_text_en=answer,
                option_text_si=answer,
                is_correct=is_correct,
                misconception_code=misconception_code,
            )
            for code, answer, is_correct, misconception_code in item["options"]
        )
        inserted += 1
    database.flush()
    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the prototype bank")
    args = parser.parse_args()
    bank = load_bank()
    print("Review-pending prototype: 10 pre questions (4 easy, 4 medium, 2 hard)")
    if not args.apply:
        print("Dry run only. Run with --apply to insert missing rows.")
        return
    with SessionLocal() as database, database.begin():
        inserted, skipped = seed_bank(database, bank)
    print(f"Inserted {inserted} questions; skipped {skipped} existing questions.")


if __name__ == "__main__":
    main()
