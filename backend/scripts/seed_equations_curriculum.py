"""Seed only Milestone 4 Batch 2 curriculum data, never schema or game questions.

From backend/: python -m scripts.seed_equations_curriculum [--apply]
The default validates/reports the bundled manifest without opening a database.
"""

import argparse
import json
import re
import uuid
from collections import Counter
from pathlib import Path, PurePosixPath

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.curriculum.models import (
    ConceptContent,
    CurriculumConcept,
    CurriculumDocument,
    CurriculumUnit,
    CurriculumVersion,
    MathConcept,
)

MANIFEST_PATH = Path(__file__).with_name("equations_curriculum.json")
SEED_NAMESPACE = uuid.UUID("d501fc2e-b075-4c13-a9e4-59f26c92d2d0")
VERSION_CODE = "SL_G10_MATH_CURRENT"
CONCEPT_TYPES = {
    "equations": "topic",
    "simple_equations": "subtopic",
    "basic_linear_equation": "skill",
    "variable_both_sides": "skill",
    "bracket_equation": "skill",
    "fractional_equation": "skill",
    "algebraic_fraction_equation": "skill",
    "equation_word_problem": "skill",
    "simultaneous_equations": "subtopic",
    "quadratic_equations": "subtopic",
}
CURRICULUM_TABLES = (
    "curriculum_versions",
    "curriculum_units",
    "math_concepts",
    "curriculum_concepts",
    "curriculum_documents",
    "concept_content",
)


class SeedConflictError(ValueError):
    """Existing data differs; stop rather than overwrite another writer's work."""


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict) -> None:
    version, unit = manifest["version"], manifest["unit"]
    if (
        version["version_code"] != VERSION_CODE
        or version["grade_level"] != 10
        or version["subject_code"] != "mathematics"
        or version["start_year"] is not None
        or version["end_year"] is not None
        or unit["unit_code"] != "EQUATIONS"
        or unit["sequence_order"] != 15
        or manifest["page_numbering"] != "one_based_pdf_page"
    ):
        raise ValueError("Unexpected Batch 2 version, unit or page convention")
    concepts = manifest["concepts"]
    if [item["concept_id"] for item in concepts] != list(CONCEPT_TYPES):
        raise ValueError("Batch 2 requires exactly the ten ordered canonical concepts")
    for index, item in enumerate(concepts, 1):
        if (
            item["concept_type"] != CONCEPT_TYPES[item["concept_id"]]
            or item["mapping"]["sequence_order"] != index
            or not item["mapping"]["learning_objective"]
        ):
            raise ValueError("Unexpected concept type, navigation order or objective")
    documents = manifest["documents"]
    if Counter(item["record"]["language_code"] for item in documents) != {
        "en": 1,
        "si": 1,
    }:
        raise ValueError("Exactly one English and one Sinhala source are required")
    for item in documents:
        record, source = item["record"], item["source"]
        path = PurePosixPath(record["file_path"])
        if (
            source["page_count"] != 10
            or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in record["file_path"]
            or ":" in record["file_path"]
            or not record["file_path"].startswith("curriculum/")
            or record["document_type"] != "lesson_pdf"
        ):
            raise ValueError("Invalid source fingerprint or portable document path")
    keys, natural_keys = set(), set()
    coverage: dict[str, set[str]] = {}
    for item in manifest["content"]:
        key = item["key"]
        natural_key = (
            item["concept_id"],
            item["language_code"],
            item["content_type"],
            item["title"],
            item["content_version"],
        )
        if (
            key in keys
            or natural_key in natural_keys
            or item["concept_id"] not in CONCEPT_TYPES
            or item["language_code"] not in {"en", "si"}
            or item["content_type"]
            not in {"learning_objective", "summary", "explanation", "worked_example"}
            or item["status"] != "draft"
            or item["content_version"] != 1
            or not item["content"].strip()
            or "\ufffd" in item["content"]
            or not 1 <= item["source_page_start"] <= item["source_page_end"] <= 10
            or (
                item["language_code"] == "si"
                and not re.search(r"[\u0d80-\u0dff]", item["content"])
            )
        ):
            raise ValueError(f"Invalid, duplicated or untraceable content: {key}")
        keys.add(key)
        natural_keys.add(natural_key)
        coverage.setdefault(item["concept_id"], set()).add(item["content_type"])
    for concept_id in (
        "simple_equations",
        "simultaneous_equations",
        "quadratic_equations",
    ):
        if not {"learning_objective", "summary"} <= coverage.get(concept_id, set()):
            raise ValueError(f"Missing section objective/summary: {concept_id}")
    if not {"explanation", "worked_example"} <= coverage["simple_equations"]:
        raise ValueError("Simple Equations needs an explanation and source example")


def _id(key: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, key)


def _ensure(database: Session, model, lookup: dict, values: dict, report: dict):
    rows = database.scalars(select(model).filter_by(**lookup)).all()
    if len(rows) > 1:
        raise SeedConflictError(f"Ambiguous existing {model.__tablename__} seed key")
    if rows:
        row = rows[0]
        differences = [
            field
            for field, value in values.items()
            if field != "id" and getattr(row, field) != value
        ]
        # A teacher may promote identical content after this import. Never
        # downgrade it, and still reject edited text or an archived record.
        if (
            model is ConceptContent
            and differences == ["status"]
            and row.status in {"reviewed", "approved"}
        ):
            differences = []
        if differences:
            raise SeedConflictError(
                f"Existing {model.__tablename__} differs in: {', '.join(differences)}"
            )
        report["reused"][model.__tablename__] += 1
        return row
    if "id" in values and database.get(model, values["id"]) is not None:
        raise SeedConflictError(
            f"Existing {model.__tablename__} has a conflicting seed ID"
        )
    row = model(**values)
    database.add(row)
    database.flush()
    report["inserted"][model.__tablename__] += 1
    return row


def seed_curriculum(database: Session, manifest: dict) -> dict:
    """Insert missing rows only; caller owns the transaction and commit/rollback.

    No DDL, deletes or component-table access. Natural keys accept existing UUIDs;
    deterministic UUIDs also protect seed content without a natural-key constraint.
    """
    validate_manifest(manifest)
    if database.get_bind().dialect.name == "postgresql":
        # Serializes concurrent executions of this seed until transaction end.
        database.execute(text("SELECT pg_advisory_xact_lock(10110006)"))
    report = {
        action: dict.fromkeys(CURRICULUM_TABLES, 0) for action in ("inserted", "reused")
    }
    version = _ensure(
        database,
        CurriculumVersion,
        {"version_code": VERSION_CODE},
        {"id": _id("version"), **manifest["version"]},
        report,
    )
    unit = _ensure(
        database,
        CurriculumUnit,
        {"curriculum_version_id": version.id, "unit_code": "EQUATIONS"},
        {"id": _id("unit"), "curriculum_version_id": version.id, **manifest["unit"]},
        report,
    )
    mappings = {}
    for item in manifest["concepts"]:
        fields = {key: value for key, value in item.items() if key != "mapping"}
        _ensure(
            database, MathConcept, {"concept_id": item["concept_id"]}, fields, report
        )
        lookup = {
            "curriculum_version_id": version.id,
            "unit_id": unit.id,
            "concept_id": item["concept_id"],
        }
        mappings[item["concept_id"]] = _ensure(
            database,
            CurriculumConcept,
            lookup,
            {"id": _id("mapping:" + item["concept_id"]), **lookup, **item["mapping"]},
            report,
        )
    documents = {}
    for item in manifest["documents"]:
        record = item["record"]
        lookup = {
            "curriculum_version_id": version.id,
            "document_code": record["document_code"],
            "language_code": record["language_code"],
        }
        documents[record["language_code"]] = _ensure(
            database,
            CurriculumDocument,
            lookup,
            {"id": _id("document:" + record["language_code"]), **lookup, **record},
            report,
        )
    for item in manifest["content"]:
        fields = {
            key: value
            for key, value in item.items()
            if key not in {"key", "concept_id"}
        }
        fields["curriculum_concept_id"] = mappings[item["concept_id"]].id
        fields["source_document_id"] = documents[item["language_code"]].id
        lookup = {
            key: fields[key]
            for key in (
                "curriculum_concept_id",
                "language_code",
                "content_type",
                "title",
                "content_version",
            )
        }
        _ensure(
            database,
            ConceptContent,
            lookup,
            {"id": _id("content:" + item["key"]), **fields},
            report,
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Commit missing curriculum rows"
    )
    args = parser.parse_args()
    manifest = load_manifest()
    print(
        "Batch 2: 1 version, 1 unit, 10 concepts, 10 mappings, 2 documents, "
        f"{len(manifest['content'])} draft content rows."
    )
    if not args.apply:
        print("Manifest validated; no database connection. Use --apply to seed.")
        return
    # Lazy import keeps dry runs/tests independent of credentials and app startup.
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as database, database.begin():
            revisions = (
                database.execute(text("SELECT version_num FROM alembic_version"))
                .scalars()
                .all()
            )
            if revisions not in (["20261011_0006"], ["20261011_0007"]):
                raise SeedConflictError(
                    "Expected revision 20261011_0006 or 20261011_0007; inspect before seeding"
                )
            report = seed_curriculum(database, manifest)
    except (SeedConflictError, SQLAlchemyError):
        # Connection errors may contain a DSN. Keep credentials out of CLI output.
        parser.exit(
            1,
            "Seed failed and transaction rolled back; check revision, connectivity and data conflicts.\n",
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
