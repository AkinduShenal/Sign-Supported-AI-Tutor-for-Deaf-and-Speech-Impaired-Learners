# Milestone 4 Batch 3 — Game activity and variant bank

Implementation started **2026-10-11**; final verification **2026-10-12**.
This batch adds a Game-owned content source. The working Phaser assessment still
uses its existing local variants. Content retrieval and Phaser integration belong
to Batch 4 and are not implemented here.

## A. Repository assessment

`app/modules/game/models.py` already contains learner sessions, events, aggregate
attempts and results. The two content classes live separately in
`app/modules/game/content_models.py`, registered in `alembic/env.py`. Curriculum
foreign keys use the existing version/unit/concept mappings; no concept was added
for the two-step activity. Existing Game, Quiz and Tutor persistence is unchanged.

The existing frontend IDs identify different mathematics from several requested
questions. The user approved **LEQ_BANK_E_001…006**, **LEQ_BANK_M_001…006** and
**LEQ_BANK_H_001…006** for this new bank. Historical IDs and stored evidence keep
their existing meanings. No FK was added from `game_task_attempts.variant_id`.

## B. Files

New implementation files, relative to the repository root:

- `backend/app/modules/game/content_models.py`
- `backend/alembic/versions/20261011_0007_add_game_activity_bank.py`
- `backend/scripts/equations_game_activities.json`
- `backend/scripts/seed_equations_game_activities.py`
- `backend/tests/test_game_activity_bank.py`
- `backend/scripts/EQUATIONS_GAME_ACTIVITIES.md` (this report)

Supporting changes: `backend/alembic/env.py` imports the content models;
`backend/scripts/seed_equations_curriculum.py` accepts revision 0007 as well as 0006
so fresh databases can migrate to head before the Batch 2 seed; curriculum tests
retain their 0006 scope while recognizing the new head and excluding later tables
from historical fixtures. Related project status Markdown links to this report.
Applied migration files 0001–0006 are preserved. In
`backend/scripts/equations_curriculum.json`, only `simple_equations.name_si`
was aligned with the team-confirmed intentional correction; no database
curriculum row was rewritten by this work.

## C. Migration and reproducibility

Revision **20261011_0007**, parent **20261011_0006**, is the only new head. Upgrade
creates exactly two tables and six explicit indexes. It contains no seed data,
updates, deletes, old-table alterations or stamps. Downgrade drops the variants
before activities and destroys their content; it is tested only on disposable
databases and is not a shared-database recovery shortcut.

The existing history still lacks newer Quiz schema and two legacy Tutor tables.
A successful fresh chain proves this batch and its recorded dependencies are
reproducible; it does **not** establish equivalence to the entire Supabase schema.
The historical upgrade fixture uses reflected baseline Quiz columns rather than
silently adding its missing newer fields.

## D. Activity table

`game_activity_bank`, 13 columns. Required unless marked nullable:

| Column | PostgreSQL type | Database default / role |
| --- | --- | --- |
| activity_id | varchar(100) | Primary key; no default |
| curriculum_concept_id | uuid | FK to curriculum_concepts.id; DELETE RESTRICT |
| difficulty_level | varchar(20) | easy / medium / hard |
| activity_type | varchar(50) | Open vocabulary; no enum constraint |
| title_en | varchar(255) | Required |
| title_si | varchar(255) | Nullable |
| instruction_en | text | Required |
| instruction_si | text | Nullable |
| activity_config | jsonb | `'{}'` |
| activity_version | integer | `1`, must be positive |
| status | varchar(20) | `'draft'`; draft/reviewed/approved/archived |
| created_at | timestamptz | now() |
| updated_at | timestamptz | now(); ORM updates advance it |

Constraints: `pk_game_activity_bank`,
`fk_game_activity_bank_curriculum_concept_id_curriculum_concepts`,
`ck_game_activity_bank_difficulty_level_valid`,
`ck_game_activity_bank_activity_version_positive`,
`ck_game_activity_bank_status_valid`.

Indexes: `ix_game_activity_bank_curriculum_concept_id`,
`ix_game_activity_bank_difficulty_level`, `ix_game_activity_bank_status`.
The primary key also has its unique PostgreSQL index.

## E. Variant table

`game_activity_variants`, 13 columns. Required unless marked nullable:

| Column | PostgreSQL type | Database default / role |
| --- | --- | --- |
| variant_id | varchar(100) | Primary key; no default |
| activity_id | varchar(100) | FK to game_activity_bank.activity_id; DELETE RESTRICT |
| variant_version | integer | `1`, must be positive |
| prompt_en | text | Required |
| prompt_si | text | Nullable |
| question_config | jsonb | Required; no default |
| answer_key | jsonb | Required; no default |
| source_document_id | uuid | Nullable FK to curriculum_documents.id; DELETE SET NULL |
| source_page_start | integer | Nullable; positive when present |
| source_page_end | integer | Nullable; positive and >= start when both present |
| status | varchar(20) | `'draft'`; draft/reviewed/approved/archived |
| created_at | timestamptz | now() |
| updated_at | timestamptz | now(); ORM updates advance it |

Constraints: `pk_game_activity_variants`,
`fk_game_activity_variants_activity_id_game_activity_bank`,
`fk_game_activity_variants_source_document_id_curriculum_89f9`,
`ck_game_activity_variants_variant_version_positive`,
`ck_game_activity_variants_status_valid`,
`ck_game_activity_variants_source_page_start_positive`,
`ck_game_activity_variants_source_page_end_positive`,
`ck_game_activity_variants_source_page_range_valid`.

Indexes: `ix_game_activity_variants_activity_id`,
`ix_game_activity_variants_source_document_id`, `ix_game_activity_variants_status`.
The primary key also has its unique PostgreSQL index. Across both tables there
are 26 columns, 2 PKs, 3 FKs, 8 checks, 6 explicit indexes and 8 total indexes.
Raw SQL writers must set `updated_at` explicitly, matching curriculum conventions;
there is no timestamp trigger.

The source FK's metadata name is
`fk_game_activity_variants_source_document_id_curriculum_documents`; SQLAlchemy
shortens it to the stored PostgreSQL name above because it exceeds 63 characters.

## F. Activities

All activities are **draft**, version 1. All have hints/retry enabled, trackable
interaction, no essential audio, and nullable Sinhala wording.

| Activity ID | Canonical concept | Difficulty | Type |
| --- | --- | --- | --- |
| LEQ_BASIC_ADD_SUB | basic_linear_equation | easy | equation_choice |
| LEQ_BASIC_MUL_DIV | basic_linear_equation | easy | equation_choice |
| LEQ_VARIABLE_BOTH_SIDES | variable_both_sides | medium | equation_sequence |
| LEQ_BRACKETS | bracket_equation | medium | equation_sequence |
| LEQ_TWO_STEP | basic_linear_equation | medium | equation_sequence |
| LEQ_FRACTIONAL | fractional_equation | hard | equation_sequence |
| LEQ_ALGEBRAIC_FRACTION | algebraic_fraction_equation | hard | equation_sequence |
| LEQ_WORD_PROBLEM | equation_word_problem | hard | word_problem |

## G. Variants and provenance

All 18 variants are **draft**, version 1, `prompt_si = NULL`. Source pages are
**one-based PDF pages**, not printed textbook numbers. Source references resolve
to the existing English `SL_G10_MATH_LESSON_15` document in the selected curriculum
version. Five are source-aligned with project choices/steps; thirteen are
project-authored equivalents with null source fields. None is an approved
assessment item. Official English PDF fingerprint and registration details remain
in [the Batch 2 report](EQUATIONS_CURRICULUM.md).

| Variant ID | Activity ID | Tier | Equation / story | x | Source relation |
| --- | --- | --- | --- | ---: | --- |
| LEQ_BANK_E_001 | LEQ_BASIC_ADD_SUB | easy | x + 3 = 7 | 4 | Project equivalent |
| LEQ_BANK_E_002 | LEQ_BASIC_ADD_SUB | easy | x + 5 = 12 | 7 | Project equivalent |
| LEQ_BANK_E_003 | LEQ_BASIC_ADD_SUB | easy | x - 4 = 6 | 10 | Project equivalent |
| LEQ_BANK_E_004 | LEQ_BASIC_ADD_SUB | easy | x - 7 = 5 | 12 | Project equivalent |
| LEQ_BANK_E_005 | LEQ_BASIC_MUL_DIV | easy | 3x = 12 | 4 | Project equivalent |
| LEQ_BANK_E_006 | LEQ_BASIC_MUL_DIV | easy | x / 4 = 3 | 12 | Project equivalent |
| LEQ_BANK_M_001 | LEQ_VARIABLE_BOTH_SIDES | medium | 2x + 8 = x + 12 | 4 | PDF 1, Review Exercise 1(a) |
| LEQ_BANK_M_002 | LEQ_VARIABLE_BOTH_SIDES | medium | 3x - 5 = x + 9 | 7 | Project equivalent |
| LEQ_BANK_M_003 | LEQ_BRACKETS | medium | 2(x - 3) = 8 | 7 | Project equivalent |
| LEQ_BANK_M_004 | LEQ_BRACKETS | medium | 3(x + 2) = 18 | 4 | Project equivalent |
| LEQ_BANK_M_005 | LEQ_TWO_STEP | medium | 2x + 5 = 17 | 6 | Project equivalent |
| LEQ_BANK_M_006 | LEQ_TWO_STEP | medium | 4x - 7 = 13 | 5 | Project equivalent |
| LEQ_BANK_H_001 | LEQ_FRACTIONAL | hard | x / 2 + 3 = 7 | 8 | Project equivalent |
| LEQ_BANK_H_002 | LEQ_FRACTIONAL | hard | (x - 2) / 3 = 4 | 14 | Project equivalent |
| LEQ_BANK_H_003 | LEQ_ALGEBRAIC_FRACTION | hard | 12/x - 12/(2x) = 2; x != 0 | 3 | PDF 1–2, divisor example |
| LEQ_BANK_H_004 | LEQ_ALGEBRAIC_FRACTION | hard | 3/(x + 2) = 1/2; x != -2 | 4 | PDF 3, Example 3 |
| LEQ_BANK_H_005 | LEQ_WORD_PROBLEM | hard | 60 items / x learners, give away 3, keep 2 | 12 | Adapted PDF 3, Example 1 |
| LEQ_BANK_H_006 | LEQ_WORD_PROBLEM | hard | Father + x children share Rs270, each Rs45 | 5 | Adapted PDF 4, Exercise 15.1(1) |

The numeric final choices match the requested bank. Six easy variants have one
final-answer step. Twelve medium/hard variants have operation/construction steps
followed by final numeric choices. Each step has consecutive numbering, equation,
choice IDs/labels, hint and result equation. Answers are separate in `answer_key`,
with matching step numbers and correct choice IDs. JSON contains data only.

## Seeding and version rules

From `backend/`, using a configured **local** database first:

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m scripts.seed_equations_curriculum --apply
.venv/Scripts/python.exe -m scripts.seed_equations_game_activities
.venv/Scripts/python.exe -m scripts.seed_equations_game_activities --apply
.venv/Scripts/python.exe -m scripts.seed_equations_game_activities --apply
```

Omitting `--apply` validates the manifest without loading database settings or
opening a connection. Apply requires revision 0007 and the existing active Batch 2
curriculum/version/unit/mappings/English source. It does not seed curriculum.

The CLI owns one transaction; a late conflict rolls back earlier inserts. Its
PostgreSQL transaction advisory lock serializes concurrent instances of this
importer. Stable primary keys identify content. The utility never updates/deletes
rows or overwrites content. Identical reviewed/approved rows may be reused without
lowering their status; changed or archived content fails loudly. Database errors
are sanitized so connection credentials are not printed.

Treat `variant_id` and its mathematical meaning as immutable. A material change
requires a **new ID** (or a future explicitly designed historical-version scheme).
Incrementing `variant_version` alone cannot make overwriting the same primary-key
row safe. Existing evidence retains its recorded equation and selected answers.
Teacher/Sinhala review and promotion are separate future work.

## H. Supabase verification

**Verified 2026-10-12.** Preflight revision 0006; both bank tables absent. Applied
`alembic upgrade head` to 0007, without stamping or modifying old tables. New
catalog matches ORM types/nullability/defaults/indexes and all constraints are
validated. First seed inserted 8/18; second inserted zero and reused 8/18.
Second-run data fingerprints include timestamps and were identical.

All 20 pre-existing application tables kept their counts during migration and
again during seeding, measured against each operation’s baseline. Nineteen complete
row fingerprints matched across the upgrade window; the sole difference in
`math_concepts` was the intentional Sinhala correction confirmed by the team.
While verification was paused, separate Game activity changed counts: `game_sessions` 212 → 213, `gameplay_events` 811 → 824, `game_task_attempts` 52 → 53.
These records were preserved; the observed growth was not attributed to the bank seed.
Using a fresh baseline after the correction and Game traffic, all 20 old-table fingerprints
were identical after both bank seed runs. Old table catalog definitions, policies, triggers and grants
were unchanged; only Alembic's version row changed as expected. The two new
tables were the only additions, bringing the public total to 23 tables.

| Table | Before migration | Before seed | After first seed | After second seed |
| --- | ---: | ---: | ---: | ---: |
| ai_tutor_finishers | 0 | 0 | 0 | 0 |
| alembic_version | 1 | 1 | 1 | 1 |
| tutor_strategy_predictions | 2 | 2 | 2 | 2 |
| ai_tutor_ml_insights | 0 | 0 | 0 | 0 |
| game_results | 4 | 4 | 4 | 4 |
| game_sessions | 212 | 213 | 213 | 213 |
| quiz_results | 8 | 8 | 8 | 8 |
| gameplay_events | 811 | 824 | 824 | 824 |
| misconception_mappings | 4 | 4 | 4 | 4 |
| quiz_questions | 10 | 10 | 10 | 10 |
| quiz_question_options | 40 | 40 | 40 | 40 |
| quiz_sessions | 6 | 6 | 6 | 6 |
| quiz_responses | 50 | 50 | 50 | 50 |
| quiz_comparisons | 0 | 0 | 0 | 0 |
| game_task_attempts | 52 | 53 | 53 | 53 |
| game_activity_bank | Absent | 0 | 8 | 8 |
| game_activity_variants | Absent | 0 | 18 | 18 |
| curriculum_versions | 1 | 1 | 1 | 1 |
| curriculum_units | 1 | 1 | 1 | 1 |
| curriculum_concepts | 10 | 10 | 10 | 10 |
| math_concepts | 10 | 10 | 10 | 10 |
| curriculum_documents | 2 | 2 | 2 | 2 |
| concept_content | 11 | 11 | 11 | 11 |

## I. Tests, lint and formatting

Final results (2026-10-12):

- Bank content/constraint tests: **28 passed**, covering SQLite and local PostgreSQL.
- Full recorded chain + populated 0006-to-0007 upgrade + model/catalog comparison:
  **1 passed**, with two existing Alembic configuration deprecation warnings.
- Scoped backend regression run, excluding bank, Tutor strategy and Avatar asset
  tests: **145 passed, 1 skipped**, with one existing Starlette/httpx warning;
  the skipped test was the legacy opt-in PostgreSQL chain.
- Isolated Tutor strategy run: **8 passed**, one existing Starlette/httpx warning.
- Ruff lint for backend: **passed**. Formatting checks for changed Python: **passed**.
- Avatar-inclusive broad test attempt: **interrupted**, so no full-suite pass claimed.
- Frontend test/build/lint: **not rerun** for this batch.
- After aligning the confirmed Sinhala label, curriculum seed and bank tests
  were rerun: **44 passed, 1 skipped** (the opt-in full-chain check had already
  passed separately). This repeat run overlaps the earlier tests above.

The initial historical-Quiz fixture was corrected to use the actual old columns;
the full-chain test now calls Alembic in-process to avoid Windows subprocess
startup timeouts. Neither required changes to applied migrations.

Tests cover real revisions, enforced FKs/checks/defaults,
fresh history and populated upgrade, schema/model comparison, 8/18 and 6/6/6,
mathematical answers and intermediate equations, manifest failures, prerequisite
failures, idempotency, promotion preservation, transaction rollback and unchanged
Game/Quiz/Tutor/curriculum data. Local PostgreSQL URLs are guarded against remote
targets and require disposable database names beginning `game_content_test_`.

Always set `DATABASE_URL=sqlite+pysqlite:///:memory:` for backend regression tests.
Run Tutor tests in their own process because existing Quiz fixtures can clear the
shared Tutor dependency override. Never let test defaults use shared Supabase.

Opt-in environment variables: `GAME_CONTENT_TEST_DATABASE_URL` for bank seed/
constraint fixtures, and a separate empty `GAME_CONTENT_MIGRATION_TEST_DATABASE_URL`
for full history/upgrade checks. The full-chain DB remains populated until its
disposable container is removed; use a fresh empty database for another run.
The Batch 3 test container was removed after verification. Fixtures remove only
their disposable test objects. Frontend checks are not required for this backend-only change;
earlier frontend results must not be reported as fresh Batch 3 runs.

## J. Existing-system impact

Phaser code, local variants, selection/usage logic, six-task 2+2+2 flow, frontend
Game API, backend Game API/analytics, Tutor, Quiz and ML logic are unchanged.
Batch 3 does not fix Tutor's missing-result insertion fallback or the missing
Quiz migrations. Those remain separate ownership/reconciliation work.

## K. Batch 4 readiness

The structured content supports a later read API and renderer adapter. Batch 4
must keep answer keys off learner-facing responses, define draft-content preview
versus approved selection, map concepts/IDs explicitly, preserve attempt snapshots
and version meaning, and retain the 2+2+2 assessment blueprint. Authentication,
content exposure/grants, Sinhala wording and teacher review still require decisions.
No retrieval endpoint or Phaser integration has been added automatically.

## Related Markdown updated

`README.md`, `MIGRATION_GUIDE.md`, `STATUS_CHECKLIST.md`, `DATABASE_CHECKLIST.md`,
`GAME_MODAL_FILE_STRUCTURE.md`, `CLAUDE.md`, `backend/app/modules/game/README.md`,
`backend/app/modules/curriculum/README.md`, `backend/scripts/EQUATIONS_CURRICULUM.md`,
and the status banner in
`frontend/src/game/Milestone_3.md`. Existing implementation changes from earlier
work were preserved; this batch creates no commit or push.

## Confirmed curriculum correction

During the upgrade verification window, `math_concepts.simple_equations.name_si`
changed from `සරල සමීකරණ විසඳීම තවදුරටත්` to `සරල සමීකරණ`. The team confirmed this
was intentional. A read-only reconstruction replacing only that field with its
previous value reproduced the original whole-table fingerprint, proving there
was no other row/field difference in that table. Migration 0007 contains no
operation on curriculum rows. The current database value was preserved; the
local Batch 2 manifest was aligned so repeat seeds accept the correction.
Game seeding used a fresh baseline after the confirmed change.

A pre-implementation hash snapshot of 121 existing frontend, Game/Quiz/Tutor
implementation, asset and applied-migration files matched after this batch.
This check excludes documentation; existing user edits were preserved.
