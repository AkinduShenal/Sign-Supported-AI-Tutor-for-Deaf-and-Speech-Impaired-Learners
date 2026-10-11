"""Batch 3 Game bank. Default: validate only. From backend/: python -m scripts.seed_equations_game_activities --apply."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.curriculum.models import (
    CurriculumConcept,
    CurriculumDocument,
    CurriculumUnit,
    CurriculumVersion,
)
from app.modules.game.content_models import GameActivity, GameActivityVariant

MANIFEST_PATH = Path(__file__).with_name("equations_game_activities.json")
TABLE_NAMES = ("game_activity_bank", "game_activity_variants")
ACTIVITY_CONCEPTS = {
    "LEQ_BASIC_ADD_SUB": ("basic_linear_equation", "easy"),
    "LEQ_BASIC_MUL_DIV": ("basic_linear_equation", "easy"),
    "LEQ_VARIABLE_BOTH_SIDES": ("variable_both_sides", "medium"),
    "LEQ_BRACKETS": ("bracket_equation", "medium"),
    "LEQ_TWO_STEP": ("basic_linear_equation", "medium"),
    "LEQ_FRACTIONAL": ("fractional_equation", "hard"),
    "LEQ_ALGEBRAIC_FRACTION": ("algebraic_fraction_equation", "hard"),
    "LEQ_WORD_PROBLEM": ("equation_word_problem", "hard"),
}


class SeedConflictError(ValueError):
    """Stable content differs or prerequisite curriculum is missing. Never overwrite."""


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ActivityConfig(Record):
    renderer: Literal["equation_cards", "equation_sequence"]
    supports_hints: Literal[True]
    supports_retry: Literal[True]
    essential_audio: Literal[False]
    interaction_trackable: Literal[True]


class Activity(Record):
    activity_id: str = Field(min_length=1, max_length=100)
    concept_id: str
    difficulty_level: Literal["easy", "medium", "hard"]
    activity_type: str = Field(min_length=1, max_length=50)
    title_en: str = Field(min_length=1, max_length=255)
    title_si: str | None
    instruction_en: str = Field(min_length=1)
    instruction_si: str | None
    activity_config: ActivityConfig
    activity_version: int = Field(gt=0)
    status: Literal["draft"]


class Choice(Record):
    choice_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class Step(Record):
    step_number: int = Field(gt=0)
    step_kind: Literal["operation", "equation_construction", "final_answer"]
    equation: str = Field(min_length=1)
    choices: list[Choice] = Field(min_length=2)
    hint_en: str = Field(min_length=1)
    result_equation: str = Field(min_length=1)


class Provenance(Record):
    relation: Literal["source_aligned", "project_authored_equivalent"]
    note: str = Field(min_length=1)


class QuestionConfig(Record):
    schema_version: Literal[1]
    render_type: Literal["equation_cards", "equation_sequence"]
    variable: Literal["x"]
    starting_equation: str = Field(min_length=1)
    excluded_values: list[str]
    positive_integer_required: bool
    essential_audio: Literal[False]
    provenance: Provenance
    steps: list[Step] = Field(min_length=1)


class StepAnswer(Record):
    step_number: int = Field(gt=0)
    correct_choice_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class AnswerKey(Record):
    final_answer: str = Field(min_length=1)
    step_answers: list[StepAnswer] = Field(min_length=1)


class Variant(Record):
    variant_id: str = Field(pattern=r"^LEQ_BANK_[EMH]_00[1-6]$")
    activity_id: str
    variant_version: int = Field(gt=0)
    prompt_en: str = Field(min_length=1)
    prompt_si: str | None
    question_config: QuestionConfig
    answer_key: AnswerKey
    source_language: Literal["en"] | None
    source_page_start: int | None = Field(ge=1, le=10)
    source_page_end: int | None = Field(ge=1, le=10)
    status: Literal["draft"]

    @model_validator(mode="after")
    def valid_steps_and_source(self):
        config, key = self.question_config, self.answer_key
        numbers = list(range(1, len(config.steps) + 1))
        if [s.step_number for s in config.steps] != numbers or [
            a.step_number for a in key.step_answers
        ] != numbers:
            raise ValueError(
                "Steps and answer keys must have matching consecutive numbering"
            )
        current = config.starting_equation
        for step, answer in zip(config.steps, key.step_answers, strict=True):
            choices = {c.choice_id: c.label for c in step.choices}
            if len(choices) != len(step.choices) or len(set(choices.values())) != len(
                choices
            ):
                raise ValueError(
                    "Choice IDs and labels must be unique within each step"
                )
            if (
                choices.get(answer.correct_choice_id) != answer.answer
                or step.equation != current
            ):
                raise ValueError(
                    "Answer must match its choice and equations must form a sequence"
                )
            current = step.result_equation
        if (
            config.steps[-1].step_kind != "final_answer"
            or key.step_answers[-1].answer != key.final_answer
            or current != f"x = {key.final_answer}"
        ):
            raise ValueError("Final step must agree with final answer")
        if any(s.step_kind == "final_answer" for s in config.steps[:-1]):
            raise ValueError("Only the last step can be the final answer")
        if (config.render_type == "equation_cards") != (len(config.steps) == 1):
            raise ValueError("Renderer must match step structure")
        if key.final_answer in config.excluded_values:
            raise ValueError("Answer violates denominator restriction")
        if config.positive_integer_required and (
            not key.final_answer.isdecimal() or int(key.final_answer) <= 0
        ):
            raise ValueError("A learner/person count must be a positive integer")
        source = (self.source_language, self.source_page_start, self.source_page_end)
        if config.provenance.relation == "source_aligned":
            if (
                any(value is None for value in source)
                or self.source_page_end < self.source_page_start
            ):
                raise ValueError(
                    "Source-aligned content requires a verified ordered page range"
                )
        elif any(value is not None for value in source):
            raise ValueError("Project equivalents must not claim a direct source")
        return self


class Manifest(Record):
    schema_version: Literal[1]
    curriculum_version_code: Literal["SL_G10_MATH_CURRENT"]
    unit_code: Literal["EQUATIONS"]
    page_numbering: Literal["one_based_pdf_page"]
    activities: list[Activity]
    variants: list[Variant]

    @model_validator(mode="after")
    def valid_bank(self):
        activities = {a.activity_id: a for a in self.activities}
        if len(self.activities) != 8 or set(activities) != set(ACTIVITY_CONCEPTS):
            raise ValueError("Exactly the eight requested activities are required")
        for aid, row in activities.items():
            if (row.concept_id, row.difficulty_level) != ACTIVITY_CONCEPTS[aid]:
                raise ValueError("Unexpected activity concept/difficulty mapping")
        expected = {f"LEQ_BANK_{tier}_{n:03}" for tier in "EMH" for n in range(1, 7)}
        if (
            len(self.variants) != 18
            or {v.variant_id for v in self.variants} != expected
        ):
            raise ValueError("Exactly 18 distinct new BANK IDs are required")
        counts = Counter()
        for variant in self.variants:
            if variant.activity_id not in activities:
                raise ValueError("Unknown activity")
            activity = activities[variant.activity_id]
            if variant.variant_id.split("_")[2] != activity.difficulty_level[0].upper():
                raise ValueError("Variant ID tier differs from activity difficulty")
            if activity.activity_config.renderer != variant.question_config.render_type:
                raise ValueError("Activity renderer differs from variant renderer")
            counts[activity.difficulty_level] += 1
        if counts != {"easy": 6, "medium": 6, "hard": 6}:
            raise ValueError("Six variants per difficulty are required")
        return self


def validate_manifest(manifest: dict) -> None:
    Manifest.model_validate(manifest)


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def _ensure(database: Session, model, key: str, values: dict, report: dict) -> None:
    row = database.get(model, values[key])
    if row is not None:
        differences = [
            name for name, value in values.items() if getattr(row, name) != value
        ]
        # Identical reviewed/approved content stays promoted; edited/archived content conflicts.
        if differences == ["status"] and row.status in {"reviewed", "approved"}:
            differences = []
        if differences:
            raise SeedConflictError(
                f"Stable ID {values[key]} conflicts in: {', '.join(differences)}"
            )
        report["reused"][model.__tablename__] += 1
        return
    database.add(model(**values))
    database.flush()
    report["inserted"][model.__tablename__] += 1


def seed_game_activities(database: Session, manifest: dict) -> dict:
    """Insert only into the two content tables. Caller MUST own transaction rollback."""
    validate_manifest(manifest)
    if database.get_bind().dialect.name == "postgresql":
        database.execute(text("SELECT pg_advisory_xact_lock(10110007)"))
    version = database.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.version_code == manifest["curriculum_version_code"]
        )
    )
    if version is None or version.status != "active":
        raise SeedConflictError("Seed Batch 2 active curriculum before the Game bank")
    unit = database.scalar(
        select(CurriculumUnit).filter_by(
            curriculum_version_id=version.id,
            unit_code=manifest["unit_code"],
            status="active",
        )
    )
    if unit is None:
        raise SeedConflictError("Missing active Equations curriculum unit")
    mappings = {
        row.concept_id: row
        for row in database.scalars(
            select(CurriculumConcept).filter_by(
                curriculum_version_id=version.id, unit_id=unit.id, status="active"
            )
        )
    }
    required = {a["concept_id"] for a in manifest["activities"]}
    if not required <= mappings.keys():
        raise SeedConflictError("Missing active Simple Equations curriculum mappings")
    document = database.scalar(
        select(CurriculumDocument).filter_by(
            curriculum_version_id=version.id,
            document_code="SL_G10_MATH_LESSON_15",
            language_code="en",
            status="active",
        )
    )
    if document is None:
        raise SeedConflictError("Missing registered English Lesson 15 source")
    report = {
        action: dict.fromkeys(TABLE_NAMES, 0) for action in ("inserted", "reused")
    }
    for item in manifest["activities"]:
        values = {k: v for k, v in item.items() if k != "concept_id"}
        values["curriculum_concept_id"] = mappings[item["concept_id"]].id
        _ensure(database, GameActivity, "activity_id", values, report)
    for item in manifest["variants"]:
        values = {k: v for k, v in item.items() if k != "source_language"}
        values["source_document_id"] = document.id if item["source_language"] else None
        _ensure(database, GameActivityVariant, "variant_id", values, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Commit missing bank content"
    )
    args = parser.parse_args()
    manifest = load_manifest()
    print(
        "Validated 8 draft activities and 18 draft variants: 6 easy, 6 medium, 6 hard."
    )
    if not args.apply:
        print(
            "No database connection. Use --apply to seed after upgrading to 0007 and seeding Batch 2."
        )
        return
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as database, database.begin():
            revisions = (
                database.execute(text("SELECT version_num FROM alembic_version"))
                .scalars()
                .all()
            )
            if revisions != ["20261011_0007"]:
                raise SeedConflictError(
                    "Expected revision 20261011_0007; inspect before seeding"
                )
            report = seed_game_activities(database, manifest)
    except SeedConflictError as exc:
        parser.exit(1, f"Seed rolled back: {exc}\n")
    except SQLAlchemyError:
        parser.exit(
            1,
            "Seed rolled back; check connectivity/schema. Database error details suppressed to protect credentials.\n",
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
