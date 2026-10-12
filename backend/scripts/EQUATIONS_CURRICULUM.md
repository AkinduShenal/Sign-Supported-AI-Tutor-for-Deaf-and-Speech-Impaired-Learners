# Milestone 4 Batch 2: Equations curriculum seed

This data seed uses the six existing curriculum tables at Alembic revision
`20261011_0006`. It does not change migration history or create any schema.
The bundled JSON is the reviewable source manifest; the Python module implements
validation and transactional insertion.

Update **2026-10-12**: Batch 3 added the Game activity/variant bank at revision
`20261011_0007`; this utility now accepts 0006 or 0007. The team confirmed the
intentional `simple_equations.name_si` correction to `සරල සමීකරණ`. Only that
field in the local manifest was aligned with the existing database value;
no curriculum database row was rewritten during Batch 3. The Batch 2 results
below remain historical. See [the Batch 3 report](EQUATIONS_GAME_ACTIVITIES.md).

## Running it

From `backend/`, using the backend virtual environment:

```powershell
python -m scripts.seed_equations_curriculum
python -m scripts.seed_equations_curriculum --apply
```

The first command validates the manifest and reports its intended size without
loading database settings or connecting. `--apply` uses the existing application's
`DATABASE_URL` settings and requires revision **0006 or 0007**. Confirm the target before
using it. No migration or stamp is run. An exception rolls back the entire seed.

The seed finds existing versions, units, concepts, mappings and documents by
their stable business keys, accepting matching records with different UUIDs.
Content is found by mapping, language, type, title and content version; UUIDv5
identifiers also prevent duplicates of this seed's content keys. PostgreSQL
executions of this utility share a transaction advisory lock.

Only missing records are inserted. Existing differences cause a conflict and
rollback rather than overwriting another developer's or teacher's work. Identical
content promoted to `reviewed` or `approved` is reused without downgrading it.
No existing text, IDs or timestamps change on a repeat run. Coordinate future
revisions explicitly; do not rename a content key/title to bypass a conflict.
Arbitrary writers do not participate in this utility's advisory lock, and the
schema has no content natural-key uniqueness constraint.

## Structure and stable identifiers

Expected seed records: **1 version, 1 unit, 10 concepts, 10 mappings,
2 documents and 11 content pieces**.

`SL_G10_MATH_CURRENT` is active, grade 10, subject `mathematics`. The supplied
excerpts do not establish a formal syllabus year, publisher or publication year;
these fields remain null. This represents the imported source set, not the
entire populated Grade 10 curriculum.

The active unit is `EQUATIONS`, English `Equations`, Sinhala `සමීකරණ`.
Its sequence order **15** means the textbook lesson number. Mapping orders below
are navigation positions within the unit.

| Mapping order | Stable concept ID | Type | Interpretation |
| --- | --- | --- | --- |
| 1 | `equations` | topic | Official Lesson 15 |
| 2 | `simple_equations` | subtopic | Official section 15.1 |
| 3 | `basic_linear_equation` | skill | Simple Equations decomposition |
| 4 | `variable_both_sides` | skill | Simple Equations decomposition |
| 5 | `bracket_equation` | skill | Simple Equations decomposition |
| 6 | `fractional_equation` | skill | Simple Equations decomposition |
| 7 | `algebraic_fraction_equation` | skill | Simple Equations decomposition |
| 8 | `equation_word_problem` | skill | Simple Equations decomposition |
| 9 | `simultaneous_equations` | subtopic | Official section 15.2 |
| 10 | `quadratic_equations` | subtopic | Official section 15.3 |

The six skills are the project's instructional decomposition of source material,
not additional official numbered headings. The existing schema stores concepts
and ordered mappings, not parent/child edges; this hierarchy is conceptual.
All mappings have concise source-aligned objectives. Existing component concept
IDs, including `linear_equations`, are preserved and acquire no new foreign keys.
The current Game scope remains section 15.1.

## Source documents and extraction

The user supplied `15 Equations eng medium.pdf` and
`15 Equations sin medium.pdf`. Both are **10-page lesson excerpts**, with printed
textbook pages 150–159. The seed contains metadata only. **Neither PDF binary was
uploaded or committed.** Registered paths reserve portable future storage keys;
they are not evidence that a Storage object currently exists.

Both document records use code `SL_G10_MATH_LESSON_15`, type `lesson_pdf`, status
`active`, and the imported curriculum version.

| Language | Title | Logical file path |
| --- | --- | --- |
| en | Lesson 15 — Equations | `curriculum/grade10/mathematics/equations_en.pdf` |
| si | 15 — සමීකරණ | `curriculum/grade10/mathematics/equations_si.pdf` |

Source SHA-256 fingerprints (also recorded in the manifest and descriptions):

```text
en f81fa7c7776ee0e640b20922dd1613994dd43ccd5225a81ae3e510f77f340f12
si b47f3ffd6dd82a4dd34fcc198c0772536d675bd642941b1b0a7f2a4c4aaa6f41
```

The English excerpt is image-based: text extraction returned no text. Selected
page images were read manually; content is concise structured paraphrase and a
source-based worked problem, not automatically approved OCR. The worked problem
is the opening divisor problem: `12/x - 12/(2x) = 2`, yielding numbers 3 and 6.

The Sinhala excerpt extracts as legacy-encoded text. That extraction was excluded.
Only four official headings and three short objective fragments were manually
transcribed from the rendered pages. The six skill names have no invented Sinhala
translations. Full Sinhala summaries, explanations, examples and descriptions
remain pending reliable transcription and teacher/Unicode review.

All source page integers are **one-based PDF pages**, not printed page numbers.
Objectives for all three sections appear on PDF page 1. Section 15.2 begins on
PDF page 5 in both languages. Section 15.3 begins on **English page 8 and Sinhala
page 9**; the two files cannot share section offsets blindly.

## Imported content

Every row has version **1**, status **draft**, and references its concept mapping
and the same-language source document in the same curriculum version. Source
review does not replace teacher approval. No entire lesson or exercise bank is
imported, and no quadratic-formula content is added.

| Concept | Language | Type | PDF pages | Status |
| --- | --- | --- | --- | --- |
| simple_equations | en | learning_objective | 1 | draft |
| simple_equations | en | summary | 1–3 | draft |
| simple_equations | en | explanation | 1–2 | draft |
| simple_equations | en | worked_example | 1–2 | draft |
| simultaneous_equations | en | learning_objective | 1 | draft |
| simultaneous_equations | en | summary | 5 | draft |
| quadratic_equations | en | learning_objective | 1 | draft |
| quadratic_equations | en | summary | 8–9 | draft |
| simple_equations | si | learning_objective | 1 | draft |
| simultaneous_equations | si | learning_objective | 1 | draft |
| quadratic_equations | si | learning_objective | 1 | draft |

## Tests and isolation

```powershell
python -m pytest -q -p no:cacheprovider tests/test_curriculum_seed.py
python -m ruff check .
python -m ruff format --check scripts/seed_equations_curriculum.py tests/test_curriculum_seed.py
```

For PostgreSQL seed tests, set `CURRICULUM_SEED_TEST_DATABASE_URL` to a disposable
local PostgreSQL database named `curriculum_test_*`. The fixture builds/removes
tables and rejects nonlocal hosts or other database names. It never uses the
application's `DATABASE_URL`. Model and full-chain migration tests use separate
`CURRICULUM_TEST_DATABASE_URL` and `CURRICULUM_MIGRATION_TEST_DATABASE_URL` databases.

Always override `DATABASE_URL` with a local-only value when running the broader
suite. Current Quiz test fixtures remove a module-level Tutor database override;
a combined run can consequently fall through to the application's configured
database. Until that separate test-isolation issue is corrected, run all backend
tests in these two processes (with the three PostgreSQL test URLs set if desired):

```powershell
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
python -m pytest -q -p no:cacheprovider --ignore=tests/test_tutor_strategy.py
python -m pytest -q -p no:cacheprovider tests/test_tutor_strategy.py
```

This does not skip Tutor coverage: the second command runs all eight Tutor tests
with their own SQLite fixture. No Quiz or Tutor source/test files are changed by
Batch 2.

Tests cover first/repeat counts, record identities and timestamps, valid document
and mapping references, page bounds, natural-key reuse, conflict rollback,
preservation of teacher edits/promotions, malformed source metadata/content, and
an offline CLI dry run. Populated synthetic Game, Quiz and Tutor rows are compared
before/after both runs. Captured SQL rejects DDL, UPDATE and DELETE, and checks
that inserts target only the six curriculum tables.

## Scope and next batch

This batch introduces no frontend, Phaser, Game assessment, Quiz, Tutor, ML or
question-selection changes. It creates no activity/variant bank or 18 questions.
Canonical IDs are ready to reference in a separately authorized Batch 3 design;
content is draft, Sinhala ingestion remains incomplete, and component identifier
normalization must be an explicit future decision. Batch 3 is not started here.

## Batch 2 verification — 2026-10-11

Supabase preflight confirmed revision `20261011_0006`, empty curriculum tables,
and exact curriculum column/default/type/nullability, constraint and index catalog
agreement with the PostgreSQL schema built by the local migration-chain test.
No live upgrade, downgrade or stamp was executed.

The actual seed CLI was then executed twice. A SQL guard allowed only SELECTs
and INSERTs into the six curriculum tables during those executions.

| Table | Before | After first run | After second run | Second-run inserts |
| --- | --- | --- | --- | --- |
| curriculum_versions | 0 | 1 | 1 | 0 |
| curriculum_units | 0 | 1 | 1 | 0 |
| math_concepts | 0 | 10 | 10 | 0 |
| curriculum_concepts | 0 | 10 | 10 | 0 |
| curriculum_documents | 0 | 2 | 2 | 0 |
| concept_content | 0 | 11 | 11 | 0 |

Content totals: **8 English, 3 Sinhala**, all draft. Zero invalid mapping/document
references, language/version mismatches, page ranges or replacement characters
were found. Row fingerprints of all public tables were identical between the
first and second runs, including curriculum UUIDs and timestamps.

The 14 existing public application tables retained both counts and whole-row
fingerprints across seeding. `alembic_version` was also unchanged. All public
table names, column/default/type/nullability definitions, constraints and indexes
were unchanged. Existing application counts before and after both runs:

| Table | Unchanged count |
| --- | --- |
| game_sessions | 210 |
| game_results | 4 |
| gameplay_events | 804 |
| game_task_attempts | 51 |
| quiz_results | 7 |
| quiz_sessions | 5 |
| quiz_responses | 40 |
| quiz_questions | 10 |
| quiz_question_options | 40 |
| quiz_comparisons | 0 |
| misconception_mappings | 4 |
| tutor_strategy_predictions | 2 |
| ai_tutor_finishers | 0 |
| ai_tutor_ml_insights | 0 |

Local validation:

- New seed tests: **16 SQLite cases and 8 PostgreSQL cases passed**.
- All **201 backend test cases passed across isolated executions**: 192 tests in
  the broader group, 8 Tutor tests in their own process, and the full-chain
  PostgreSQL migration test rerun successfully in a fresh database. The broader
  rerun initially reused a nonempty migration-test database and correctly failed
  its empty-target guard; only that check required another fresh database.
- An initial combined run produced 196 passes and 5 Tutor failures because of
  the pre-existing Quiz/Tutor override interference described above. Those five
  requests reached the configured Supabase connection. Game inserts were rejected
  by its parent-session foreign key; the Tutor service rolled back each failed
  transaction before prediction persistence. Subsequent test processes explicitly
  forced the application database to local SQLite. This initial run is not
  represented as an all-green or fully isolated test run.
- Actual CLI against local PostgreSQL built through migrations 0001–0006: first
  run inserted expected counts; second inserted zero and reused all 35 records.
- `python -m ruff check .`: passed for the backend.
- `python -m ruff format --check scripts/seed_equations_curriculum.py
  tests/test_curriculum_seed.py`: both files already formatted.
- `git diff --check -- backend`: passed. Existing Starlette/httpx deprecation
  warning remains. No frontend build was needed or run.

The temporary PostgreSQL 17 Docker instance and its disposable databases were
used only for local tests. Unrelated frontend working-tree changes were left
untouched; no commit or push is included in this batch.
