# Game module (backend)

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

The AI Tutor reads `GameResult` from `models.py` (`tutor/service.py`), and its
input contract is `GameResult` in `app/modules/tutor/schemas.py`. Renaming or
removing a column or allowed value breaks the Tutor, so agree such changes with
the Tutor owner first. Adding new nullable columns is safe.

## Migrations

**Read [`MIGRATION_GUIDE.md`](../../../../MIGRATION_GUIDE.md) at the repo
root before writing or running any Alembic migration against this
database** — it's shared with Quiz and AI Tutor, large parts of its
schema were built directly on Supabase outside any migration file, and
`alembic revision --autogenerate` **will** generate a migration that
drops other teams' tables/columns it doesn't recognize (this has already
happened once here). That guide covers the full workflow: hand-authoring
scoped migrations, `stamp` vs `upgrade`, and what to do if the history
ever looks inconsistent with the live database.
