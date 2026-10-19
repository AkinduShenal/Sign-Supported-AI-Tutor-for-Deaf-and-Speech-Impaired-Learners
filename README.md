# Sign-Supported AI Tutor

Research project for accessible Grade 10 Mathematics learning support for Deaf
and speech-impaired learners.

## Current state — 2026-10-12

- **Game:** a three-mode Phaser hub, with Drag & Drop playable and Hangman /
  Mystery Reveal pending. Six-task assessments persist events, attempts and
  backend-calculated results. The latest hub/session work is still uncommitted.
- **Quiz:** merged bilingual ten-question pre-assessment, saved responses and
  provisional diagnostic results; it is no longer a placeholder.
- **AI Tutor:** adaptive lesson/practice workspace and avatar support, using a
  trained `strategy-ml-v1` strategy pipeline (updated 2026-10-16). Quiz/Game share
  learner codes and cycles; saved results now select the lesson automatically.
  See [automatic learning flow](docs/TUTOR_AUTOMATIC_FLOW.md).
- **Remedial:** gateway/package placeholder; implementation pending.
- **Curriculum and Game content:** Milestone 4 Batches 1–3 complete. Supabase
  was verified at revision `20261011_0007` on 2026-10-12. The curriculum has
  10 concepts, 2 document registrations and 11 draft content pieces; the new
  Game bank has 8 draft activities and 18 draft variants (6 per tier). Phaser
  still uses its existing local content; database integration is Batch 4.

The newer Quiz schema is modeled but not covered by Alembic. Tutor now reads
saved Quiz/Game results and persists only its predictions (2026-10-16). The current history
does not yet build the entire live application schema from an empty database.

See [current status and next steps](STATUS_CHECKLIST.md),
[database inventory](DATABASE_CHECKLIST.md),
[Game continuation guide](GAME_MODAL_FILE_STRUCTURE.md), and
[curriculum verification](backend/scripts/EQUATIONS_CURRICULUM.md).

## Project structure

- `backend/` — FastAPI API, tutor strategy logic, lesson content, sign planner,
  database models, migrations, and tests.
- `frontend/` — React/Vite Quiz, Game and Tutor gateways, with runtime avatar playback.
- `frontend/public/models/louise_signs_master.glb` — deployed Louise avatar with
  named prototype gesture actions.
- `avatar-sign-package/` — canonical sign manifests, review documentation,
  technical pose report, and asset validation/build tools.
- `avatar/` — deprecated procedural research script retained for reference only;
  it is not used by the application.

`backend/app/modules/tutor/sign_package/` is a deployment snapshot of the two
canonical manifest files because Railway deploys the backend directory by
itself. A test prevents the snapshot and canonical files from drifting apart.

## Run locally

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` (or the configured frontend port). On Windows use
`.venv\Scripts\Activate.ps1`, or invoke `.venv\Scripts\python.exe` directly;
use `npm.cmd` if PowerShell blocks `npm.ps1`.

The application opens the **AI Tutor** tab. Complete Quiz and Game with the same
assigned student code, then return to AI Tutor.
It loads the model-selected approach and lesson automatically. See [the implementation and research guide](docs/GRADE10_TUTOR.md)
for API integration, tests, model status and remaining validation requirements.

Backend settings currently read the root `.env` when environment variables are
absent; Docker Compose reads the root `.env` and injects `DATABASE_URL`.
Explicit environment variables take precedence. Never print credentials or run
tests with the shared Supabase URL: use the isolated commands in the status guide
and read [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) before schema operations.

Latest frontend checks: **26 tests passed**, build passed with a large-bundle
warning, lint passed with **5 existing warnings**. The same-day Batch 2 backend
verification passed 201 cases across isolated executions; it is not a claim that
the current combined test invocation is safe or that learner validation is done.

Each worked-example step now has **Ask about this step** and related bilingual
lesson notes. Local retrieval works without an API key. Optional OpenAI generation
can be enabled on the backend; provider failure falls back to the retrieved
notes. See [tutor retrieval setup](docs/TUTOR_RAG.md) for configuration and limits.

## Avatar research status

The master GLB contains 83 prototype educational gesture actions: 22 repaired
core actions, 34 earlier composites, 15 teaching demos and 12 short explanation
cues. The latest expansion preserves all 71 previous actions and reuses their
unchanged poses; builder preservation checks passed, with visual/signing review
still pending. See [short explanation cues](avatar-sign-package/docs/EXPLANATION_CUES.md).
They are not
validated Sri Lankan Sign Language. Missing or unavailable actions fall back to
written and visual mathematics support rather than being fabricated at runtime.

Validated-only playback is the default. To review existing unvalidated gestures,
explicitly enable **Preview unvalidated gestures (reviewers only)**. The current
strategy engine uses the supplied Colab model; its training metrics are not a
claim of learner effectiveness. Teacher/sign
review and actual learner evaluation remain necessary before research claims.

Batch 3 schema, seed, source references and live preservation checks are recorded
in [the Game bank report](backend/scripts/EQUATIONS_GAME_ACTIVITIES.md). Existing
frontend/Phaser code and applied migrations 0001–0006 were preserved.
