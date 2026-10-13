# Game collection: current contract and limits

Drag & Drop and Hangman continue to write `game_sessions`, `gameplay_events`,
`game_task_attempts`, and `game_results`. No shared `activity_answers` table is
assumed. For a new frontend session, `GAME_STARTED.event_payload.recording_protocol`
is `game-evidence-v1`. Each HTTP event has a stable `client_event_id` inside its
payload, and retries reuse the same timestamp and payload. The backend locks the
parent session and returns the existing event for an identical retry. A task
summary is likewise idempotent by `(game_session_id, task_id, attempt_number)`.
Changing the evidence under an existing key returns HTTP 409.

The scenes emit `ANSWER_SUBMITTED` followed by `ANSWER_CORRECT` or
`ANSWER_INCORRECT`. **Only the outcome event is one answer row in an export.**
Drag & Drop records the selected inverse-operation card for each equation step;
Hangman records the entered final value of `x`. Outcome payloads include the
prompt, expected response, answer type, difficulty, attempt order, and hints
before that attempt. `HINT_REQUESTED` and `RETRY_STARTED` remain separate source
events. Hangman emits a retry event after each earlier accepted submission.
`QUESTION_SHOWN` captures offered card order in Drag & Drop. The content version
is left blank in the CSV when the playable frontend bank has no verified version.

For sessions marked `game-evidence-v1`, completing an assessment requires six
saved task summaries, exactly two per difficulty, and matching saved answer,
wrong-answer, hint, retry, and success evidence. A partial or mismatched session
remains `in_progress`; its result is not created. The frontend now persists a
bounded write-ahead queue in browser storage before HTTP, scopes requests to the
assigned student and real Game session, and retries with the same identifiers.
Refresh/tab-close recovery requires the same browser profile/origin and explicit
re-entry of the original assigned code. Unfinished gameplay state is not restored;
recover evidence and explicitly end the partial collection before starting a new
session. See [the school runbook](SCHOOL_COLLECTION_RUNBOOK.md) for status meanings,
storage limits and unsupported crash scenarios. A recovered partial session is
not a complete research observation.

## Read-only CSV export

### Browser download

The Game researcher panel has **Download Game CSV files**. It downloads the same
five CSV files and `manifest.json` together as a ZIP through
`GET /api/v1/game/exports/collection`. The endpoint uses the backend's configured
database and a consistent read-only PostgreSQL snapshot. It does not accept a
database URL from the browser, create results or supply independent labels.

Configure a private `GAME_COLLECTION_EXPORT_KEY` (at least 16 characters) in the
repository-root `.env` or backend process environment and restart the backend.
Enter that key in the researcher panel; it is sent as a Bearer header, never in
the URL, and is not persisted in browser storage. Do not use a `VITE_` variable
for this secret. Missing/short server configuration disables the endpoint; missing
or incorrect credentials cannot access the database through it. Responses use
`Cache-Control: no-store`.

The button is disabled while this browser has unsaved evidence. A download
contains all saved Game records, including incomplete sessions; it cannot include
unacknowledged browser-only writes. Files go to the browser's download location,
and the ZIP can be extracted locally. The CLI below remains available.

### Command-line export

From `backend/`, use the configured `DATABASE_URL` (shell environment takes
precedence over the repository-root `.env`):

```powershell
.venv/Scripts/python.exe -m scripts.export_game_collection
```

Each invocation creates a new timestamped folder under the repository's ignored
`exports/` directory and prints its absolute path and row counts. No credentials
are printed. Remote databases still require explicit `--allow-remote-read`.
Existing output folders are rejected, preserving prior exports.

Optional explicit overrides, with a **local PostgreSQL URL**:

```powershell
.venv/Scripts/python.exe -m scripts.export_game_collection --database-url 'postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/DB' --output-dir ../game-export
```

The script writes `game_sessions.csv`, `student_answers.csv`, `game_events.csv`,
`game_analytics.csv`, `independent_assessment_labels.csv`, and `manifest.json`.
The answer CSV has `source_event_id`, so each row can be matched to
`gameplay_events.id`. `game_events.csv` includes hint and retry source IDs;
analytics have `source_result_id`. The manifest records
source row counts and incomplete-session count. Independent-label cells stay
empty until a researcher supplies teacher, Quiz, or test evidence with its
rubric. The exporter does not place names or credentials in the output. Remote
reads require the explicit `--allow-remote-read` flag and appropriate team
authorization; this script has not been verified against live Supabase here.

Game now requires an explicit researcher-assigned `STU_` code (3–6 digits) before
launch. It does not fall back to the legacy browser UUID, and switching learners
is explicit and blocked while evidence is unsaved. `student_id` remains a
caller-supplied Game string. A value shaped like `STU_001` is **not** proof that a shared student row exists, so the manifest
marks student codes unverified. `learning_cycle_id` is the assessment cycle,
and `game_session_id` is the Game module session. Shared `SES_...` session
links are not implemented yet. Exclude unverified identities and incomplete
sessions from an audited ML cohort. Milestone 1/1.1 datasets and trained-model
code remain unchanged; never use `game_results.game_difficulty_level` or its
other heuristic outputs as independent labels.

For an isolated local PostgreSQL test database, set
`GAME_COLLECTION_TEST_DATABASE_URL` to its loopback URL and run
`python -m pytest tests/test_game_postgres_collection.py -q` from `backend/`.
The integration test skips without that variable and rejects non-loopback hosts.

## Integration reads

The existing `GET /api/v1/game/results/{game_session_id}` returns a genuine
Game result **by Game session ID**. A filtered read by verified student code,
concept, and learning cycle is still missing for Tutor/Avatar. It should query
Game-owned results and validate identity/cycle alignment; Tutor should not
insert Game rows. The existing API also lacks a paginated, ordered individual
answer-history endpoint for Remedial. A future adapter should project outcome
events, join Game session and task metadata, include the original prompt and
source IDs, and report unknown historical fields as null. The CSV export is a
researcher-facing stopgap, not that endpoint.

## Before a school visit

- Reconcile the live Alembic/schema state before applying any migration.
- Establish and check the researcher-assigned code roster across devices;
  the Game-only code gate is not a shared registry or authenticated account.
- Validate this write/retry/export flow against local PostgreSQL and run a
  complete two-mode browser assessment under interrupted-network conditions.
- Confirm the six-task bank and content versions presented to learners.
- Confirm that any actual learner export matches source database row counts
  and has no unverified identity or incomplete session in the study cohort.
