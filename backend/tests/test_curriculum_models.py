"""Database behavior, with real FK enforcement even on SQLite.

Optionally also run on an explicitly supplied, disposable local PostgreSQL DB:
CURRICULUM_TEST_DATABASE_URL=postgresql+psycopg://.../curriculum_test_models
No fixture reads the application's DATABASE_URL or writes to Supabase.
"""

import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.curriculum.models import (
    ConceptContent,
    CurriculumConcept,
    CurriculumDocument,
    CurriculumUnit,
    CurriculumVersion,
    MathConcept,
)

POSTGRES_TEST_URL = os.environ.get("CURRICULUM_TEST_DATABASE_URL")
BACKENDS = ["sqlite"] + (["postgresql"] if POSTGRES_TEST_URL else [])


@pytest.fixture(params=BACKENDS)
def database(request):
    if request.param == "postgresql":
        url = make_url(POSTGRES_TEST_URL)
        if url.host not in {"localhost", "127.0.0.1", "::1"} or not (
            url.database or ""
        ).startswith("curriculum_test_"):
            pytest.fail(
                "Curriculum PostgreSQL tests require a disposable local curriculum_test_* DB"
            )
        engine = create_engine(url)
    else:
        engine = create_engine("sqlite+pysqlite:///:memory:")

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "alembic")
    )
    revision = ScriptDirectory.from_config(config).get_revision("20261011_0006").module
    # Run the real migration, then use ORM models against its tables.
    with engine.begin() as connection:
        context = MigrationContext.configure(
            connection, opts={"target_metadata": Base.metadata}
        )
        with Operations.context(context):
            revision.upgrade()
    try:
        with Session(engine) as session:
            yield session
    finally:
        with engine.begin() as connection:
            context = MigrationContext.configure(
                connection, opts={"target_metadata": Base.metadata}
            )
            with Operations.context(context):
                revision.downgrade()
        engine.dispose()


def _version(database, code="TEST_V1", **values):
    row = CurriculumVersion(version_code=code, version_name="Test curriculum", **values)
    database.add(row)
    database.flush()
    return row


def _curriculum(database):
    version = _version(database)
    unit = CurriculumUnit(
        curriculum_version_id=version.id, unit_code="TEST_UNIT", sequence_order=0
    )
    concept = MathConcept(
        concept_id="test_skill", name_en="Test skill", concept_type="skill"
    )
    database.add_all([unit, concept])
    database.flush()
    mapping = CurriculumConcept(
        curriculum_version_id=version.id,
        unit_id=unit.id,
        concept_id=concept.concept_id,
        sequence_order=0,
    )
    database.add(mapping)
    database.flush()
    return version, unit, concept, mapping


def _document(version_id, **overrides):
    return CurriculumDocument(
        **{
            "curriculum_version_id": version_id,
            "document_code": "TEST_DOC",
            "title": "Test source",
            "language_code": "en",
            "document_type": "textbook",
            "file_path": "test-only/source.pdf",
            **overrides,
        }
    )


def _content(mapping_id, **overrides):
    return ConceptContent(
        **{
            "curriculum_concept_id": mapping_id,
            "language_code": "en",
            "content_type": "explanation",
            "content": "Test-only content",
            **overrides,
        }
    )


def test_version_creation_and_database_defaults(database):
    # Literal SQL bypasses ORM/client defaults, exercising the actual DDL.
    database.execute(
        text(
            "INSERT INTO curriculum_versions (id, version_code, version_name) "
            "VALUES (:id, :code, :name)"
        ),
        {"id": uuid.uuid4().hex, "code": "TEST_RAW", "name": "Test raw defaults"},
    )
    database.commit()
    version = database.scalar(
        select(CurriculumVersion).where(CurriculumVersion.version_code == "TEST_RAW")
    )
    assert version.grade_level == 10
    assert version.subject_code == "mathematics"
    assert version.status == "draft"
    assert version.created_at is not None and version.updated_at is not None


def test_duplicate_version_code_rejected(database):
    _version(database)
    with pytest.raises(IntegrityError):
        _version(database)


@pytest.mark.parametrize(
    "values",
    [
        {"start_year": 2029, "end_year": 2026},
        {"grade_level": 0},
        {"status": "unknown"},
    ],
)
def test_invalid_version_metadata_rejected(database, values):
    with pytest.raises(IntegrityError):
        _version(database, **values)


def test_open_ended_version_years_allowed(database):
    _version(database, start_year=2026)
    _version(database, "TEST_V2", end_year=2029)


def test_unit_requires_existing_version(database):
    database.add(
        CurriculumUnit(
            curriculum_version_id=uuid.uuid4(), unit_code="TEST_UNIT", sequence_order=0
        )
    )
    with pytest.raises(IntegrityError):
        database.flush()


def test_unit_code_is_unique_within_version_only(database):
    first, second = _version(database), _version(database, "TEST_V2")
    for version in (first, second):
        database.add(
            CurriculumUnit(
                curriculum_version_id=version.id,
                unit_code="TEST_UNIT",
                sequence_order=0,
            )
        )
        database.flush()
    database.add(
        CurriculumUnit(
            curriculum_version_id=first.id, unit_code="TEST_UNIT", sequence_order=1
        )
    )
    with pytest.raises(IntegrityError):
        database.flush()


def test_stable_string_concept_and_bilingual_text_round_trip(database):
    concept = MathConcept(
        concept_id="test_skill",
        name_en="Test skill",
        name_si="පරීක්ෂණය",
        concept_type="skill",
    )
    database.add(concept)
    database.commit()
    stored = database.get(MathConcept, "test_skill")
    assert stored.concept_id == "test_skill"
    assert stored.name_si == "පරීක්ෂණය"


def test_valid_concept_mapping(database):
    version, unit, concept, mapping = _curriculum(database)
    database.commit()
    assert mapping.curriculum_version_id == version.id
    assert mapping.unit_id == unit.id and mapping.concept_id == concept.concept_id
    assert mapping.is_mandatory is True


@pytest.mark.parametrize("missing", ["curriculum_version_id", "unit_id", "concept_id"])
def test_mapping_requires_existing_parents(database, missing):
    version, unit, concept, _ = _curriculum(database)
    values = {
        "curriculum_version_id": version.id,
        "unit_id": unit.id,
        "concept_id": concept.concept_id,
        "sequence_order": 1,
    }
    values[missing] = "missing_concept" if missing == "concept_id" else uuid.uuid4()
    database.add(CurriculumConcept(**values))
    with pytest.raises(IntegrityError):
        database.flush()


def test_mapping_cannot_use_unit_from_another_version(database):
    _, unit, concept, _ = _curriculum(database)
    other = _version(database, "TEST_V2")
    database.add(
        CurriculumConcept(
            curriculum_version_id=other.id,
            unit_id=unit.id,
            concept_id=concept.concept_id,
            sequence_order=0,
        )
    )
    with pytest.raises(IntegrityError):
        database.flush()


def test_duplicate_mapping_rejected(database):
    version, unit, concept, _ = _curriculum(database)
    database.add(
        CurriculumConcept(
            curriculum_version_id=version.id,
            unit_id=unit.id,
            concept_id=concept.concept_id,
            sequence_order=1,
        )
    )
    with pytest.raises(IntegrityError):
        database.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"language_code": "fr"},
        {"document_type": "video"},
        {"status": "draft"},
    ],
)
def test_invalid_document_metadata_rejected(database, values):
    version = _version(database)
    database.add(_document(version.id, **values))
    with pytest.raises(IntegrityError):
        database.flush()


def test_document_code_can_have_both_languages_but_no_duplicate(database):
    version = _version(database)
    database.add_all([_document(version.id, language_code="si"), _document(version.id)])
    database.flush()
    database.add(_document(version.id))
    with pytest.raises(IntegrityError):
        database.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"language_code": "fr"},
        {"content_type": "question_bank"},
        {"status": "active"},
        {"source_page_start": 0},
        {"source_page_end": -1},
        {"source_page_start": 8, "source_page_end": 7},
        {"content_version": 0},
    ],
)
def test_invalid_content_metadata_rejected(database, values):
    *_, mapping = _curriculum(database)
    database.add(_content(mapping.id, **values))
    with pytest.raises(IntegrityError):
        database.flush()


@pytest.mark.parametrize("language", ["en", "si"])
def test_content_without_source_document_allowed(database, language):
    *_, mapping = _curriculum(database)
    content = _content(mapping.id, language_code=language)
    database.add(content)
    database.commit()
    assert content.source_document_id is None
    assert content.content_version == 1 and content.status == "draft"


@pytest.mark.parametrize("field", ["curriculum_concept_id", "source_document_id"])
def test_content_rejects_missing_references(database, field):
    *_, mapping = _curriculum(database)
    content = _content(mapping.id)
    setattr(content, field, uuid.uuid4())
    database.add(content)
    with pytest.raises(IntegrityError):
        database.flush()


def test_deleting_document_preserves_content_and_page_history(database):
    version, _, _, mapping = _curriculum(database)
    document = _document(version.id)
    database.add(document)
    database.flush()
    content = _content(
        mapping.id,
        source_document_id=document.id,
        source_page_start=3,
        source_page_end=4,
    )
    database.add(content)
    database.commit()
    content_id = content.id
    database.execute(
        delete(CurriculumDocument).where(CurriculumDocument.id == document.id)
    )
    database.commit()
    database.expire_all()
    preserved = database.get(ConceptContent, content_id)
    assert preserved is not None and preserved.source_document_id is None
    assert preserved.content == "Test-only content"
    assert (preserved.source_page_start, preserved.source_page_end) == (3, 4)


def test_deleting_referenced_concept_is_restricted(database):
    _, _, concept, _ = _curriculum(database)
    with pytest.raises(IntegrityError):
        database.execute(
            delete(MathConcept).where(MathConcept.concept_id == concept.concept_id)
        )
