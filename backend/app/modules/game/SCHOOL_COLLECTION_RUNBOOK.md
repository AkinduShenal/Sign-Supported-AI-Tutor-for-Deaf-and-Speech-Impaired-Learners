# School Game collection runbook — October 14, 2026

This guide covers researcher-operated Drag & Drop and Hangman collection only.
Assigned codes are not authenticated accounts or backend student registry rows.
Do not enter learner names. Keep the school's code-to-learner roster separately
under the approved research protocol. Do not use engineering test records as
learner observations, or Game heuristic labels as independent assessment labels.

## Before the visit

Use current desktop Chrome or Edge, normal browsing, one Game tab, and the same
browser profile/origin for recovery. Web Locks require localhost or HTTPS; plain
HTTP on another laptop's LAN address is not a verified deployment configuration.
Use desktop/laptop collection for the verified workflow. The additional phone
visual regression failed its Hangman compact-to-landscape transition assertion;
phone orientation support is not verified by this milestone.
Confirm the approved code roster, collection permission, six-task content bank,
independent assessment rubric, and handling of interrupted sessions.

Verify the actual school backend/database and frontend API URL separately. The
local synthetic test database is not the school database. No production schema
or connectivity is established by local tests. Do not run migrations for this
milestone. Never change the API destination while pending evidence exists.

## Start the application

From `backend/`, in a dedicated PowerShell terminal:

```powershell
# Obtain the approved collection URL through the team's secure configuration.
# Set DATABASE_URL explicitly; do not accidentally inherit backend/.env.
$env:DATABASE_URL = '<approved collection database URL>'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, in another terminal, for same-laptop collection:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`. Keep this exact origin throughout collection;
`localhost`, a different port, and a different profile have different storage.
These development commands require already-installed dependencies. Confirm the
actual school launch configuration in advance rather than installing at school.

## Collect one learner

1. At the Game collection form, enter the roster's code, such as `STU_001`.
   Allowed syntax: uppercase `STU_` plus 3–6 digits. Click **Set student**.
2. Check the visible active code against the roster before handing over the game.
3. Choose **Drag & Drop** or **Hangman**. A new UUID Game session and local
   learning-cycle UUID are created. Record the real Game session ID if keeping a
   paper log. No `SES_...` identifier or cross-module linkage is manufactured.
4. Let the learner work. The collection panel shows the code, real session ID,
   queued writes and **Saved / Pending / Failed**.
5. **Saved** means the queued evidence was acknowledged. It does not mean the
   assessment is complete. For a complete observation, require both **Saved** and
   **Assessment complete**, plus the backend result summary.
6. For the other mode, end the collection and explicitly set the same learner
   code again before choosing the mode. Each mode has its own Game session.
7. Before a different learner, check the end-collection confirmation and click
   **End collection / switch learner**. Pending/failed evidence blocks this.
   Then enter `STU_002` and verify the displayed code. Switching modules while a
   collection is open is blocked. No previous browser UUID is reused by Game.

## Disconnection, refresh or tab closure

- During a disconnection, accepted events are written synchronously to the
  bounded browser queue before HTTP is attempted. Restore connectivity and use
  **Retry / recover saved evidence**. Online reconnection also retries the active
  learner's collection. A stalled HTTP request times out after 15 seconds.
- Do not clear storage, use private browsing, change browser/profile/origin or
  reinstall the application. Do not switch learners while unsaved writes remain.
- After refresh or reopening the tab at the same origin, re-enter the original
  learner code shown in the recovery panel. Click **Retry / recover saved evidence**.
  Pending IDs and original payloads are reused, including writes whose responses
  were lost after the database committed.
- An interrupted unfinished game does **not** resume its gameplay state. Recover
  its evidence and explicitly end that collection locally. The backend session
  remains `in_progress` and is incomplete in CSV. Start a fresh session for that
  learner; do not merge the two sessions or count the partial one as complete.
- If all tasks were finished and a completion request was stored before closure,
  recovery can retry completion after all evidence has been acknowledged.
- Storage failure/full capacity stops collection. Preserve the browser profile
  and contact the researcher. A failed storage write means the latest interaction
  cannot be promised durable; do not continue or mark that assessment complete.
- Storage has a 4 MiB serialized-document cap, 20,000 pending-write cap and
  100-session cap per origin/profile. Acknowledged payloads leave the queue;
  session metadata remains. No evidence is evicted to make room. Plan capacity
  in advance; do not clear a full profile containing unresolved evidence.
- Normal refresh and tab-close recovery are tested scenarios. OS/power failure,
  disk corruption, browser eviction, deliberate storage deletion, and a crash
  between a user action and its synchronous storage write are not guaranteed.
  Closing before a scene emits its delayed task summary can leave a session
  incomplete even when its answer events were recovered.

## Export and check

### Download from the Game panel

Before collection, configure this backend-only setting in the repository-root
`.env` (use your own private random value with at least 16 characters):

```dotenv
GAME_COLLECTION_EXPORT_KEY=replace-with-your-own-long-random-key
```

Restart the backend after changing its environment. In the Game researcher
panel, open **Download Game CSV files**, enter the researcher export key and click
**Download Game CSVs (.zip)**. Extract the archive to inspect the five CSV files
and manifest. The browser controls where it saves downloads; this does not create
a snapshot in the repository's `exports/` directory.

The key protects the collection-wide endpoint because the application has no
researcher login. Keep it separate from learner access codes, do not publish it
in frontend environment variables, and use HTTPS for remote browser access.
It is not saved in browser storage. Pending/failed writes must be recovered before
the button becomes available. Incomplete persisted sessions still appear and
remain marked incomplete in the downloaded snapshot.

### Command-line alternative

Stop new collection writes while taking the final snapshot. From `backend/`,
run the read-only exporter using `DATABASE_URL` from the environment or the
repository-root `.env`:

```powershell
.venv/Scripts/python.exe -m scripts.export_game_collection
```

It creates a fresh timestamped directory under the repository's ignored
`exports/` folder and prints the absolute destination and source counts. For an
authorized remote source, append `--allow-remote-read`. To choose a destination:

```powershell
.venv/Scripts/python.exe -m scripts.export_game_collection `
  --output-dir '../exports/school-2026-10-14-snapshot-001'
```

Remote reads additionally require the exporter's `--allow-remote-read` and the
team's authorization. This runbook does not grant production access. The
CLI rejects existing destination folders. Preserve earlier snapshots and the
source database. Explicit `--database-url` overrides are still supported.

`game_sessions.csv` maps assigned `student_code` to the actual `game_session_id`,
`learning_cycle_id`, concept and phase. This is the session mapping; it does not
assert a shared Quiz/Tutor session. `student_answers.csv` records actual answer
outcomes and source event IDs. `game_events.csv` contains all exported source
events. `game_analytics.csv` contains Game results. The independent-label template
remains empty until genuine assessment evidence is supplied.

Inspect counts in PowerShell (set the path to the fresh snapshot):

```powershell
$snapshot = '../exports/school-2026-10-14-snapshot-001'
$sessions = Import-Csv "$snapshot/game_sessions.csv"
($sessions | Select-Object -ExpandProperty student_id_recorded -Unique).Count
$sessions.Count
$sessions | Group-Object student_id_recorded | Select-Object Name,Count
$sessions | Where-Object { $_.saved_assessment_complete -ne 'True' }
Get-Content "$snapshot/manifest.json"
```

Match manifest counts against read-only source database counts for all four Game
tables. Outcome counts include only `ANSWER_CORRECT` and `ANSWER_INCORRECT`, not
`ANSWER_SUBMITTED` again. Match answer `source_event_id` to `gameplay_events.id`;
check `(game_session_id, client_event_id)` is unique. Verify incomplete sessions
are retained and excluded from a complete research cohort. Game task difficulty
is `easy/medium/hard`; the existing result difficulty vocabulary is
`beginner/intermediate/advanced`. Do not relabel either as independent mastery.

## Secure backup

Keep exports outside Git and public/shared folders. Back up the source database
and complete export snapshot (including manifest) using the team's approved
encrypted storage. Restrict access and keep the learner-name roster separately.
Verify the backup can be read and retain the original snapshot. Browser pending
storage is a recovery aid, not a database backup. Preserve unresolved profiles.

## Local engineering verification

The browser smoke script requires an explicitly selected isolated loopback
backend, not the ordinary configured application backend:

```powershell
# frontend/
$env:GAME_COLLECTION_API = 'http://127.0.0.1:8137/api/v1'
node tests/gameCollection.e2e.mjs
```

Use a fresh isolated local PostgreSQL database with Game-only ORM tables for that
backend. The script generates synthetic engineering actions for `STU_001` and
`STU_002` and writes `frontend/artifacts/game-collection-*/browser-evidence.json`.
It does not train ML. On Windows, restricted process environments can prevent
Chrome's GPU process from starting; run with normal authorized local process
access, keeping Chrome's own sandbox enabled.

Reconcile a successful run with the existing CSV exporter using:

```powershell
# backend/ — use the same isolated database that served the browser test
.venv/Scripts/python.exe -m scripts.verify_game_collection_smoke `
  --database-url '<isolated loopback PostgreSQL URL>' `
  --browser-evidence '../frontend/artifacts/<successful-run>/browser-evidence.json' `
  --output-dir '../tmp/<fresh-reconciliation-directory>'
```

If browser automation does not finish, do not mark it passed. Manually perform
the collection steps for both modes on an isolated test deployment: wrong answer,
correct answer, hint, all six tasks, network failure, refresh, recovery, and
explicit switch to `STU_002`. Repeat interruption with tab closure; compare IDs,
answers and counts in PostgreSQL and CSV. Record each outcome and failure.
