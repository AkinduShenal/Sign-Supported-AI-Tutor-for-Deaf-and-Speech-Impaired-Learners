# Game module (backend)

Offline next-task hint prediction foundations are documented in
[`ml/README.md`](ml/README.md). This development-only package is separate from
the existing heuristic analytics and has no database or API integration.

**Owner:** RehanOP007 (Game component). Other components: please don't edit
files here. Open an issue or ask the owner instead.

Backend for the Equation Game. Its routes are served under `/api/v1/game`.

**Full file-by-file structure, architecture, database shape, Milestone 3
progress and known gaps:** see
[`GAME_MODAL_FILE_STRUCTURE.md`](../../../../GAME_MODAL_FILE_STRUCTURE.md)
at the repo root — that document is the source of truth for this
component, kept up to date as the single continuation guide. This file is
intentionally just a pointer.

## Shared contract with the AI Tutor

Intended ownership: Game creates and updates Game sessions/results; Tutor reads
results and persists only Tutor-owned predictions. The current
`tutor/service.py` also inserts missing `GameResult`/`QuizResult` records from
its combined request payload. That fallback is an unresolved ownership defect,
not an approved persistence responsibility. It can fail when no parent Game
session exists. Tutor's request schema is still a payload contract, not an
automatic read-only retrieval integration.

Renaming/removing columns or allowed values requires coordination with the Tutor
owner. Any additive change still needs schema/default/nullability review.

As of 2026-10-12, Game persistence/analytics are implemented; the last verified
Supabase revision is `20261011_0007`. Shared curriculum Batches 1–2 and the
Game bank Batch 3 are complete. Phaser still uses its local variants and
existing `linear_equations` identifier.
See [database status](../../../../DATABASE_CHECKLIST.md) for remaining migration
coverage and the distinction between current code and verified live evidence.

## Migrations

**Read [`MIGRATION_GUIDE.md`](../../../../MIGRATION_GUIDE.md) at the repo
root before writing or running any Alembic migration against this
database** — it's shared with Quiz and AI Tutor, large parts of its
schema were built directly on Supabase outside any migration file, and
`alembic revision --autogenerate` can propose dropping other teams'
tables/columns it doesn't recognize (this has already
happened once here). That guide covers the full workflow: hand-authoring
scoped migrations, `stamp` vs `upgrade`, and what to do if the history
ever looks inconsistent with the live database.

## Milestone 4 Batch 3 — Game content bank

`content_models.py` defines the two Game-owned content tables. Revision 0007 and
the repeat-safe seed are Supabase-verified as of 2026-10-12: **8 draft activities,
18 draft LEQ_BANK variants, 6 per tier**. Existing learner evidence, API and
Phaser behavior are unchanged. The [bank report](../../../scripts/EQUATIONS_GAME_ACTIVITIES.md)
lists exact schema, IDs, answers, source pages, tests and the immutable-ID rule.
Read API and renderer integration remain Batch 4.
