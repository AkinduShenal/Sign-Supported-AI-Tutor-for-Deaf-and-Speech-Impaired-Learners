# Database Migration Guide — Read This Before Touching Alembic

This repository's Postgres database is **one shared Supabase instance**,
used by all four components (Quiz, Game, AI Tutor, Remedial). Every
developer's migrations land in the same `alembic_version` history and the
same live tables. A careless migration doesn't just affect your own
component — it can silently alter or destroy another developer's tables,
and it affects every other developer's next `alembic upgrade` the moment
they pull your branch.

This document exists because this has already gone wrong twice in this
repository (see §7, "Incidents that happened here"). Read the whole thing
before you write or run a migration, not just the command list.

---

## 1. The one fact that changes everything about this database

Large parts of this database's schema were **built directly on Supabase**
— by hand, or by another developer running SQL — **before** this repo's
Alembic history described them. That means:

- Alembic's model of "what the database looks like" (its migration
  history) and the **actual live schema** can disagree.
- Your own component's models.py might be 100% correct about what's live,
  while Alembic's `alembic_version` bookmark still thinks the database is
  several revisions behind.
- Running the wrong Alembic command in this situation can destroy data
  that was never Alembic's to manage in the first place.

Because of this, **the normal "just run autogenerate" workflow is not
safe here.** Treat every migration as something you hand-build and
personally verify, not something a tool generates for you unattended.

---

## 2. Never run `alembic revision --autogenerate` against this database

`--autogenerate` works by comparing **every model imported in
`alembic/env.py`** (i.e. every component's models, not just yours) against
the **entire live database**. In this repo, that comparison will find:

- Tables other components built directly on Supabase that aren't modeled
  in anyone's `models.py` yet.
- Columns on shared tables (like `game_results` / `quiz_results`) that
  exist live but aren't in your component's model.

Autogenerate's answer to "this exists live but isn't in any model" is
always **"drop it."** It has no way to know that it's looking at another
team's table instead of leftover cruft. If you run `alembic upgrade` with
that generated file, you will drop someone else's data.

**This already happened once in this repo** (§7.1). The generated file was
caught and deleted before `upgrade` ever ran. Don't rely on catching it —
don't generate it in the first place.

### What to do instead: hand-author the migration

1. Decide exactly which table(s)/column(s) *you* are adding or changing —
   only things inside your own component's ownership.
2. Write the migration file by hand (copy the structure of an existing one
   — see `backend/alembic/versions/20261008_0004_*.py` or
   `20261009_0005_*.py` for the pattern this repo uses).
3. The file should only ever call `op.create_table` / `op.add_column` /
   `op.create_check_constraint` / `op.create_index` / etc. for the exact
   objects you intend to change. Never let it touch anything you didn't
   explicitly write.
4. Read the file back once you're done, line by line, and confirm there is
   nothing in it you didn't intend. Treat an unexpected `drop_*` call in a
   migration you hand-wrote as a sign you made a typo, not something to
   wave through.

---

## 3. Before you write any migration: find out what's actually live

Don't trust `alembic history` or `alembic current` alone — they only know
what Alembic has been told, not what's actually in the database (see §1).
Check the live schema directly:

```python
# Run from backend/, inside the venv — read-only, completely safe.
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    print(conn.execute(text("SELECT version_num FROM alembic_version")).scalar())

    cols = conn.execute(text(
        "SELECT column_name, data_type, character_maximum_length, is_nullable "
        "FROM information_schema.columns WHERE table_name = 'your_table' "
        "ORDER BY column_name"
    )).fetchall()
    for c in cols:
        print(c)

    constraints = conn.execute(text(
        "SELECT conname FROM pg_constraint WHERE conrelid = 'your_table'::regclass"
    )).fetchall()
    print([c[0] for c in constraints])
```

Do this for every table your migration will touch, **every time**, even
if you're sure you remember what's there. The whole point of this
database is that it can drift from what any one person remembers.

---

## 4. Deciding between `alembic stamp` and `alembic upgrade`

These are **not interchangeable**, and picking the wrong one is exactly
how the history drift in §7.2 happened.

| | What it does | When to use it here |
| --- | --- | --- |
| `alembic upgrade head` | **Actually runs the SQL** in `upgrade()` — creates tables, adds columns, adds constraints, for real, against the live database. | The objects in your migration **do not yet exist live**. This is the normal case for new work. |
| `alembic stamp <revision>` | Only rewrites the one bookmark row in the `alembic_version` table. Runs **no SQL** against your schema at all. | The objects in your migration **already exist live** — e.g. someone built them by hand on Supabase, or ran a raw SQL `ALTER TABLE` themselves, and you just need Alembic's history to catch up to reality. |

**If you're not sure which applies: go back to §3 and check the live
schema before deciding.** If the columns/tables are already there,
`upgrade` would error out (duplicate table/column) — which is actually a
useful safety check: if `upgrade` fails with "already exists," that's
your sign you should have used `stamp` instead, not a sign to force it
through.

---

## 5. Step-by-step workflow for a new migration

1. **Pull `main` first.** Another developer may have added a migration
   since you last checked — if you don't have it locally, Alembic won't
   know your new migration's `down_revision` should chain onto theirs.
2. **Check `alembic heads`** (not just `alembic current`). If this prints
   more than one revision, someone's migration diverged from yours and
   needs `alembic merge` before anyone runs `upgrade` — stop and sort that
   out first; don't just add a third branch on top.
3. **Check the live schema directly** (§3) for every table you're about
   to touch.
4. **Hand-author the migration file** (§2), scoped to only your own
   component's tables/columns:
   - Filename: `YYYYMMDD_NNNN_short_description.py`, where `NNNN` is one
     higher than the current head's number.
   - `revision = "YYYYMMDD_NNNN"`, `down_revision = "<the current head>"`,
     `branch_labels = None`, `depends_on = None`.
   - Write both `upgrade()` **and** a correct, working `downgrade()` —
     don't leave it as `pass`. If you never intend to roll this back,
     write the downgrade anyway; someone else may need to.
5. **If your models.py already matches the live schema** (the objects
   already exist, built outside Alembic): run
   `alembic stamp <your revision>`. Then verify directly against
   `information_schema` (§3) that nothing changed — it shouldn't have.
6. **If the objects genuinely don't exist yet:** run
   `alembic upgrade head`. This is a real, if additive, change to a
   database shared by the whole team — **say so out loud to the team
   before you run it**, the same way you'd flag any other change to
   shared infrastructure. Additive, nullable columns are low-risk; dropping
   or renaming anything is not and needs explicit agreement from whoever
   owns the table you're touching.
7. **Verify immediately after**, whichever command you ran:
   - Re-query `information_schema`/`pg_constraint`/`pg_indexes` directly
     and confirm the live schema matches your migration exactly.
   - Confirm `alembic_version` now shows your new revision.
8. **Run the full test suite** (`pytest -q` from `backend/`) — it runs
   against an in-memory SQLite built from `models.py` via
   `Base.metadata.create_all`, completely independent of Supabase, and
   confirms your models still work for every other developer's tests too.
9. **Commit and push the migration file promptly.** Every other developer
   now has a local `alembic_version` that's one revision behind reality
   the moment you run `stamp`/`upgrade` against the shared database. If
   they pull late and then try to run their own migration, Alembic will
   complain it can't find your revision, or create a second diverging
   head. Don't sit on a migration file locally after you've actually run
   it against Supabase.

---

## 6. Rules, restated plainly

1. Never run `alembic revision --autogenerate` against this database.
   Hand-author every migration.
2. Never write `op.*` calls for tables/columns outside your own
   component's ownership.
3. Never guess whether something is already live — check
   `information_schema` directly, every time (§3).
4. `stamp` = bookmark only, no SQL. `upgrade` = real SQL, really runs.
   Don't use one where the other belongs.
5. Always write a real `downgrade()`, not `pass`.
6. Say it out loud before running `alembic upgrade` against the shared
   Supabase database — it affects everyone, not just your branch.
7. Never run a destructive migration (drop/rename/remove-not-null) on a
   table you don't own without agreement from the developer who does.
8. Commit and push a migration the moment you've actually run it live —
   don't let local and remote `alembic_version` drift.
9. If `alembic heads` ever shows more than one head, stop and resolve it
   before anyone runs `upgrade`.
10. If the live schema and `alembic_version` ever disagree (see §7.2 for
    how to notice), fix the history — don't just work around it by
    hand-editing `alembic_version` directly in SQL.

---

## 7. Incidents that happened here (read these — they're not hypothetical)

### 7.1 — The autogenerate near-disaster

Running `alembic revision --autogenerate` in this repo produced a
migration that would have **dropped the entire Quiz and AI-Tutor schema**
and several columns on `game_results`/`quiz_results`, because the
migration history didn't know those objects had been built directly on
Supabase, outside Alembic. The generated file was deleted immediately,
**before `alembic upgrade` was ever run against it.** Nothing was lost —
but only because it was caught before being applied. This is exactly the
failure mode §2 exists to prevent.

### 7.2 — The migration file that went missing

A hand-authored, correctly-scoped migration (`20261008_0004`, describing
`game_sessions`/`gameplay_events`/`game_task_attempts` plus additive
`game_results` columns) was created and — according to earlier notes —
stamped onto Supabase successfully. Later, the `.py` file itself was found
to be **missing from `alembic/versions/`** (only a stale compiled
`.pyc` remained), and the live `alembic_version` table was still sitting
on the **previous** revision, one behind what had been assumed. The
actual tables were fine — they matched `models.py` exactly, verified
directly against `information_schema` — only Alembic's own bookkeeping
had drifted from reality.

**How it was fixed:** the migration file was rewritten from scratch to
exactly match the already-verified live schema, then re-applied with
`alembic stamp` (not `upgrade` — the objects already existed), and the
fix was confirmed by reading `alembic_version` directly afterward.

**The lesson:** don't trust that a migration "took" just because a
command returned success in a past session, a chat log, or a teammate's
say-so. **Verify directly against the live database** (§3) before
building anything else on top of an assumed-correct history.

---

## 8. If you inherit a broken-looking history

If `alembic current`/`alembic history` ever look inconsistent with what
you expect (a revision file referenced that doesn't exist, or
`alembic_version` pointing somewhere unexpected):

1. **Don't guess, and don't run `upgrade` to "force it forward."**
2. Query the live schema directly (§3) for the tables involved. This is
   the only source of truth that can't have drifted from itself.
3. Compare that against every component's `models.py`. Whichever model
   matches the live schema is correct; Alembic's version table is just a
   bookmark and can be wrong.
4. If a migration file is missing or wrong, rewrite it to match the
   **verified live schema** exactly (not what you assume it should be),
   then `stamp` (if the objects already exist) or `upgrade` (if they
   genuinely don't) accordingly.
5. Re-verify directly against `information_schema` afterward. Don't move
   on until the live schema, the migration file, and `alembic_version`
   all agree with each other.
