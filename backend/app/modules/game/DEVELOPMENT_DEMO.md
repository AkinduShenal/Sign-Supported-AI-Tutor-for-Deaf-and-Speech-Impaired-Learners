# Private PP1 Game ML development demo

**Development Demo — Not Student Assessment**

This is a separate localhost ASGI application, disabled by default. It reuses
the existing six-task games, save queue protocol, strict saved-evidence adapter,
frozen nine-feature Logistic Regression worker and results card. It does not
mount Quiz, Tutor, research inference, collection exports or database migrations.
No model is trained. A prediction is an experimental estimate for a team tester.

## Run locally (PowerShell, from the repository root)

These commands use separate ports so the ordinary app can keep running. Open
two terminals. Do not use `app.main:app`, `--reload`, multiple workers, a public
host, tunnels or a deployment platform for the demo.

Terminal 1:

```powershell
$env:GAME_ML_DEV_DEMO_ENABLED = 'true'
$env:FRONTEND_URL = 'http://localhost:5175'
& backend/.venv/Scripts/python.exe -B -m uvicorn app.modules.game.development_demo:app --app-dir backend --host 127.0.0.1 --port 18081 --workers 1 --no-access-log
```

Terminal 2:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:18081/api/v1'
npm.cmd --prefix frontend run dev -- --host localhost --port 5175 --strictPort
```

Open **http://localhost:5175/development-demo**. The scheme, hostname and port
must match `FRONTEND_URL` exactly; `127.0.0.1:5175` is a different browser origin.
If a port is occupied, select a free port and update the corresponding value in
both commands. Do not stop another person's server.

The backend loads these existing private settings from the **root `.env`**:

- `GAME_RESEARCHER_VERIFY_KEY`: existing private 32–256 character URL-safe key,
  distinct from export/bearer credentials. Never add it to any `VITE_` setting.
- `GAME_ML_MODEL_ARCHIVE`: absolute path to the existing trusted
  `local_ml_artifacts/game_ml_model_export_with_fixtures.zip`.
- `GAME_ML_PYTHON`: absolute path to the compatible interpreter, currently
  `local_ml_artifacts/compatibility_audit/env/Scripts/python.exe`.
- `GAME_ML_TIMEOUT_SEC`: existing worker bound (default 60 seconds).

No genuine research manifest, manual SHA-256 generation or consent reference is
needed for this pathway. The **worker's existing frozen model checksums and
runtime checks still apply**. The ordinary app's manifest policy is unchanged.
No `.env` edit is needed when those three private settings already exist.

## Show a prediction

1. Click **Start Game**. The server issues `DEMO_TEAM`, a fresh
   learning cycle, recording capability and a pool of new session IDs.
2. Choose Drag & Drop or Hangman. Finish all six tasks. The original difficulty,
   question selection, hints, analytics and scoring rules apply.
3. Wait for the **Researcher Verification** dialog. It opens only after the
   backend acknowledges completed, saved evidence. Confirm the exact session
   is your development test, enter the existing private researcher key, and
   click **Verify & Show ML Result**.
4. The backend checks the key, designation, receipt, source chronology and all
   nine features, then runs the original worker. The **ML Model Estimate** card
   displays the returned level and all three probabilities.
5. Choose another game for a fresh session, or **Start a fresh session** to reload.

The visible demo banners were removed at the researcher's request. The existing
experimental prediction notice remains; internal demo classification, isolated
storage and research-team confirmation are unchanged. An estimate must not guide a real
student's tutoring, difficulty, assessment or remedial decisions.

## Isolation and lifetime

- Every backend startup creates a fresh
  `local_ml_artifacts/development_demo/development-only-<uuid>.sqlite3` file.
  It never uses `DATABASE_URL` for storage, connects to the genuine database, reopens old
  sessions or changes historical research records. One worker holds a file lock.
- Only server-issued session IDs bound to that browser capability and cycle
  can be recorded. `STU_037`, arbitrary UUIDs and known excluded sessions cannot
  enter this pathway. Demo designation and approval audit live only in SQLite.
- No researcher key or prediction is written to browser storage. The recording
  capability, queue and completion receipts are memory-only. The shared learner
  context and genuine pending-write queue are not read or flushed by this page.
- Reloading loses pending writes and receipts. Backend restart creates another
  namespace. Complete a new demo if either happens; do not use it for genuine
  collection or recover an old research session through this pathway.
- A completion receipt expires in **five minutes**, is bound to the exact
  session/context and key configuration, and is consumed after one successful
  prediction. Cancelled or expired receipts require a newly completed demo;
  completion retries do not mint replacements.
- The app exposes no research export routes. Demo identity also fails the real
  research student-code contract. Never manually import these SQLite files or
  test artifacts into genuine training, evaluation or collection datasets.
- Loopback client/Host and exact local Origin checks apply, without trusting
  forwarding headers. Existing failed-key rate limits, cancellation, expiry and
  replay protection are reused through a separate in-memory receipt store.

Stop both demo terminals with Ctrl+C when finished. Process environment flags
are temporary; the source default remains disabled. Return to your ordinary
frontend/backend for genuine collection. Do not set demo flags publicly.

## Verification

Backend engineering tests use isolated synthetic sessions in both modes. The
positive tests call the actual frozen worker, while negative checks must never
reach it. Genuine inference/preview/export regression tests remain separate.

```powershell
& backend/.venv/Scripts/python.exe -B -m pytest backend/tests/test_game_development_demo.py -q -p no:cacheprovider --basetemp tmp/demo-tests-manual-001
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Use a fresh, nonexistent `--basetemp` path for each run; pytest can remove an
existing base temporary directory. Backend imports require `PYTHONPATH=backend`
when invoking pytest from the repository root:

```powershell
$env:PYTHONPATH = "$PWD/backend"
```

For the actual local browser test (Chrome installed, free ports 5196, 9246,
18986), run from `frontend`:

```powershell
node tests/gameDevelopmentDemo.e2e.mjs
```

It launches its own loopback backend, SQLite namespace, Vite and headless Chrome
with a temporary synthetic verification key. It plays both games using actual
pointer controls, saves six tasks each and checks real worker predictions in
the card. The Phaser inspection hook exists only in the intercepted test page;
production source has no test hook. Outputs are development evidence under
`frontend/artifacts/development-demo-<time>/`, never genuine learner results.

The model archive and compatible worker interpreter must be installed locally;
no network model download or training occurs.

## Source changes for this extension

New backend files:

- `backend/app/modules/game/development_demo.py`
- `backend/app/modules/game/DEVELOPMENT_DEMO.md`
- `backend/tests/test_game_development_demo.py`

New frontend files:

- `frontend/src/game/DevelopmentDemoPage.tsx`
- `frontend/src/game/developmentDemoState.ts`
- `frontend/tests/developmentDemo.test.ts`
- `frontend/tests/gameDevelopmentDemo.e2e.mjs`

Existing frontend files extended:

- `frontend/src/App.tsx` — route `/development-demo` separately.
- `frontend/src/game/collectionIdentity.ts` — memory-only demo identity override.
- `frontend/src/game/session/GameSession.ts` — use the issued demo learning cycle.
- `frontend/src/game/api/gameBackendSync.ts` — use server-issued demo session IDs.
- `frontend/src/game/api/game.ts` — demo-only URL namespace and capability header.
- `frontend/src/game/api/collectionStore.ts` — separate volatile demo queue.
- `frontend/src/game/gameMLVerification.ts` — bind demo acknowledgements and endpoint.
- `frontend/src/game/ResearcherMLResult.tsx` — explicit demo confirmation text.
- `frontend/src/game/MLProficiencyCard.tsx` — existing prediction card, experimental notice retained.
- `frontend/src/game/phaser/PhaserGame.tsx` — reuse GameCanvas.

No original research backend authorization, model worker/adapter, model archive,
scene mechanics, scoring, root `.env`, genuine data or shared database contract
was edited. Generated test SQLite databases and browser outputs are development
artifacts only. No public deployment or genuine-student test was performed.
