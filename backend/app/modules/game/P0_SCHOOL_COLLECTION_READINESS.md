# Final P0 — Game collection readiness, October 13, 2026

School visit: October 14, 2026. This record reports engineering verification, not
real learner observations, ML accuracy, or approval of the school deployment.

## Status

| Requested area | Status | Evidence and limits |
| --- | --- | --- |
| Student identity | PASS | Explicit researcher-assigned `STU_` + 3–6 digits; visible active code; no UUID fallback in Game; explicit end/switch; no registry/account claim. |
| Drag & Drop browser | PASS | Real desktop Chrome → actual local API → PostgreSQL, full sessions for STU_001 and STU_002, wrong/correct/hint/progression, interruption/refresh recovery and learner isolation. |
| Hangman browser | PASS | Same desktop workflow, including tab closure/reopening and pending-evidence recovery. |
| Database recording | PASS | Isolated PostgreSQL 17, existing Game-only ORM tables; persisted browser actions reconciled with exact payloads and session ownership; no duplicates. |
| Refresh/tab recovery | PASS | Original stored IDs/payloads replayed in the same profile/origin; unsaved switching blocked. Full gameplay state and OS/power-failure durability are not promised. |
| CSV export | PASS | Existing read-only exporter used; source IDs, counts, difficulty vocabularies and incomplete-session flags checked against PostgreSQL. |
| Real school deployment | NOT VERIFIED | Actual school API/database URL, schema compatibility, connectivity, device/browser configuration and backup procedure have not been exercised. |
| Remaining critical blockers | NOT VERIFIED | Actual deployment preflight, approved assigned-code roster and research protocol, and operational backup/capacity checks remain. Phone orientation has a separate failed regression; use verified desktop collection. |

The local Game-to-database-to-export workflow is verified. Do not describe the
actual school deployment as ready until its configuration/preflight is verified.

## Changes made in this P0

Created:

- `frontend/src/game/collectionIdentity.ts`: strict assigned-code validation and
  explicit in-memory active learner; no browser UUID fallback.
- `frontend/src/game/CollectionGate.tsx` and `CollectionGate.css`: researcher code
  entry, visible code/session/status, explicit end/switch, recovery panel,
  single-tab Web Lock, unload warning and module-navigation protection.
- `frontend/src/game/api/pendingGameWrites.ts`: synchronous localStorage write-ahead
  queue with stable request identities, serial replay, confirmed-ack removal,
  completion intent, conservative storage failure handling, bounds and preserved
  session metadata. No pending evidence is evicted on learner switching.
- `frontend/src/game/api/collectionStore.ts`: Game API adapter and API-destination
  binding; reloads stored state on acquiring the tab lock.
- `frontend/tests/gameCollection.test.ts`: 13 additional identity/recovery unit
  tests, including response loss, attempt keys, storage failures, bounds,
  incompatible storage/destination and unconfirmed completion.
- `frontend/tests/gameCollection.e2e.mjs`: real-browser synthetic collection
  against an explicitly selected isolated local API, without successful API mocks.
- `backend/scripts/verify_game_collection_smoke.py`: read-only loopback PostgreSQL
  and existing-exporter reconciliation against recorded browser actions; refuses
  to overwrite an existing export directory.
- `backend/app/modules/game/SCHOOL_COLLECTION_RUNBOOK.md`: school procedure,
  recovery limits, export/check/backup instructions and manual fallback checks.
- This completion/readiness record.

Extended existing files:

- `frontend/src/game/api/gameBackendSync.ts`: retained scene-facing recording API,
  now backed by persistent requests rather than in-memory retry closures.
- `frontend/src/game/api/game.ts`: 15-second default HTTP timeout.
- `frontend/src/game/phaser/PhaserGame.tsx`: Game-only collection gate and explicit
  renderer shutdown on end/storage failure.
- `EquationGameScene.ts` and `HangmanGameScene.ts`: new sessions use the explicit
  collection student code. Existing session IDs and carried session objects remain.
- `GameSelectionScene.ts`: unfinished collections cannot silently start another
  mode; acknowledged completed collections can close before another mode begins.
- `frontend/tests/gameUi.e2e.mjs`: adapted the existing mocked visual regression to
  explicit code entry, UUID session acknowledgments and explicit partial-session
  closure; screenshots now go to fresh timestamped directories.
- `frontend/src/game/README.md` and `backend/app/modules/game/GAME_COLLECTION.md`:
  links and accurate recovery/identity boundaries.

The pre-existing uncommitted backend evidence/idempotency validation, exporter,
PostgreSQL integration test and frontend visual changes were preserved. No
Quiz/Tutor/Avatar/Remedial changes, ML Milestone 1/1.1 edits, shared migrations,
production Supabase access, commits, merges, pushes or branch switches occurred.
The legacy `identity.ts` remains unchanged for its other consumers.

## Verification results

From `frontend/`:

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run lint
$env:GAME_COLLECTION_API = 'http://127.0.0.1:8139/api/v1'
node tests/gameCollection.e2e.mjs
node tests/gameUi.e2e.mjs
```

- Unit tests: **53 passed** (40 existing plus 13 new).
- TypeScript/production build: **passed**; existing large-bundle warning remains.
- Lint: passed with existing warnings in unrelated components.
- Functional browser collection: **PASS**, with evidence in
  `frontend/artifacts/game-collection-1791841072231/browser-evidence.json`.
  Six sessions were checked: four complete and two recovered partial sessions,
  across both modes and two assigned learner codes. **38 actual answer actions**
  were subsequently matched to database outcomes.
- Existing visual/input regression: **FAIL** at the Hangman phone landscape
  transition assertion `isCompactLayout === false`. Both full desktop flows
  passed before this failure, including Drag & Drop drag/tap and Hangman keypad,
  hints, ten-slip failure, stars and summaries. No runtime exceptions were reported.
  The baseline Hangman resize handler fits the camera using its existing compact
  flag rather than rebuilding/recomputing compact layout. This P0 does not change
  that handler or claim phone orientation support is verified. The functional
  desktop collection test is a separate successful test against actual PostgreSQL.

From `backend/`, with explicit local-only settings:

```powershell
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
.venv/Scripts/python.exe -m pytest tests/test_game_sessions_api.py tests/test_game_ml.py tests/test_game_research_ml.py -q -p no:cacheprovider --basetemp=../tmp/game-p0-tests
# Separate empty loopback PostgreSQL DB, not the browser DB:
$env:GAME_COLLECTION_TEST_DATABASE_URL = '<isolated loopback PostgreSQL URL>'
.venv/Scripts/python.exe -m pytest tests/test_game_postgres_collection.py -q -p no:cacheprovider --basetemp=../tmp/game-p0-postgres
```

- Game/API/ML regression: **154 passed in 21.48s**, existing Starlette/httpx warning.
- Isolated PostgreSQL integration: **1 passed in 1.73s**; it did not skip.
- New reconciliation script: Ruff lint/format passed; `git diff --check` passed.

Actual PostgreSQL/CSV reconciliation command:

```powershell
.venv/Scripts/python.exe -m scripts.verify_game_collection_smoke `
  --database-url '<isolated loopback PostgreSQL URL on port 55439>' `
  --browser-evidence '../frontend/artifacts/game-collection-1791841072231/browser-evidence.json' `
  --output-dir '../tmp/game-p0-reconciled-20261013-02'
```

Result: **PASS**. Snapshot counts: 9 Game sessions, 58 answer outcomes, 250 source
events, 34 task summaries, 4 Game results and 5 incomplete sessions. These totals
include preserved records from three earlier aborted browser runs, as well as the
successful six-session run (four complete, two partial). They are not a learner
cohort or research findings. Independent labels supplied: **0**. Exact source
IDs/counts, selected browser answer values/correctness, student/session mapping,
event uniqueness and difficulty vocabularies were checked. Hangman's single
final-value step uses the existing backend's implicit step zero; missing explicit
step indices remain blank in the original CSV exporter.

The first reconciliation attempt assumed an explicit Hangman step index and
failed. The verifier was corrected to follow the existing single-step contract;
the earlier snapshot was preserved and the successful rerun used a fresh path.

## Environment and recovery limits

PostgreSQL ran in a new loopback-only container `game-p0-isolated-20261013`, using
the already cached `postgres:17` image. The initial `postgres:16` download failed
because Docker's registry CDN DNS was unavailable. No existing application
containers or production database were changed. Local tables were created with
Game-only ORM metadata in new engineering databases, without Alembic migrations.

Initial restricted Chrome startup failed because its GPU subprocess was denied
access. Browser checks succeeded with authorized local process access, leaving
Chrome's own sandbox enabled. A React StrictMode tab-lock race found during the
browser check was fixed using an abortable queued Web Lock. Another aborted run
showed final-save waits were too short for this local environment: network traces
showed successful writes taking several seconds each. The successful harness
waits for actual acknowledgments and uses the visible retry action, with a bounded
five-minute final-save deadline. Actual school performance is not established.

The queue is capped at 4 MiB, 20,000 pending writes and 100 session metadata rows
per profile/origin. It stops on storage failure/full capacity without evicting old
evidence. Refresh/tab-close recovery requires the same profile/origin and code;
gameplay state does not resume. Unfinished or delayed-summary-missing sessions
remain incomplete. Power loss, storage eviction/deletion/corruption and crashes
before synchronous persistence are unsupported guarantees. API-destination/version
mismatches block replay. Codes are pseudonymous but not authenticated identities.

Smallest remaining operational milestone: verify the approved desktop school
deployment, learner-code roster, exact API/database configuration, interruption
recovery, export reconciliation and secure backup procedure on the actual school
setup. Address phone orientation separately before collecting on phones.
