# Game-Based Learning Analytics

This component collects linear-equation gameplay and turns it into the Game
result used by the AI Tutor. Open **Equation Game** in the shared application.

Updated: 27 October 2026. [Project README](README.md)

## Games and session flow

**Drag & Drop** lets the learner apply operations to an equation, with tap
controls available as an alternative to dragging. **Hangman** asks for the
value of `x` through an on-screen numeric keypad. Both provide hints,
wrong-answer feedback, progress and a completion summary.

Each assessment has **six tasks: 2 Easy, 2 Medium and 2 Hard**. The two modes
share session handling, variant-usage checks and backend synchronization.
The selection screen also shows **Mystery Reveal** as coming next; that mode's
gameplay is not implemented.

Sinhala is the default language. The language control changes the current
scene's text without restarting it or clearing the answer buffer. Layouts
support desktop and phone widths, touch controls and celebrations.

To use the component:

1. Select the assigned learner code used for the Quiz.
2. Start either playable mode and complete its six tasks.
3. Recover pending writes if the connection was interrupted.
4. Review the saved result and continue to AI Tutor once collection is saved.

Game and Quiz can be completed in either order, but both must belong to the
same learner and learning cycle for automatic tutoring.

## Recording and analytics

The frontend queues session creation, gameplay events, task summaries and
completion. It checks backend acknowledgements and supports recovery after an
interruption. Finishing locally and confirming backend completion are separate
states in the UI.

The backend calculates success/completion rates, attempts, wrong answers,
retries, hints, skipped steps and elapsed time. Game owns this evidence and
the resulting diagnostics; Tutor reads the saved result rather than creating
or changing gameplay records.

The collection panel can download saved Game CSVs and their manifest as a ZIP.
Recover pending writes before exporting or switching learners. Download access
uses `GAME_COLLECTION_EXPORT_KEY`, separate from researcher model credentials.

Phaser currently uses the local equation variant bank. The shared curriculum
database has a separate Game content bank, but it is not yet the automatic
source for the playable scenes.

## Experimental model estimate

The result panel can show an estimate of **Beginner, Intermediate or Advanced**
and the model's class probabilities. It also provides saved ML input details.
Ordinary Game results remain available if an estimate cannot be produced.

After a newly saved completion, the backend can issue a session-bound receipt.
The browser uses it to request that session's prediction automatically. A
receipt is single-use, expires after five minutes and is held in memory. This
flow currently assumes a single backend process; a restart loses receipts.

The frozen model uses these nine inputs:

- `first_attempt_accuracy`
- `game_success_rate`
- `wrong_attempt_count`
- `retry_count`
- `total_hint_count`
- `skipped_step_count`
- `game_active_time_sec`
- `game_hint_rate`
- `game_avg_attempts_per_task`

The service validates saved evidence before projecting it into the model's
legacy feature contract. It does not overwrite the stored analytics. A separate
worker checks the trusted archive's checksums, feature/class order, dependency
versions and frozen predictions before serving a request.

Required worker runtime: **Python 3.13.12**, scikit-learn **1.6.1**, NumPy
**2.1.3**, pandas **2.2.3**, SciPy **1.16.3** and joblib **1.6.0**. The archive is
`local_ml_artifacts/game_ml_model_export_with_fixtures.zip`.
The integration version is `game-ml-experimental-v1`, with status
`EXPERIMENTAL_NOT_PRODUCTION_APPROVED`.

There is also a separate bearer/manifest-protected researcher endpoint. Its
credentials and reviewed session bindings are not required by the browser's
completion-receipt path. Predictions are experimental estimates, not teacher
verification or a replacement for the Game's saved scores.

## Running and configuration

Follow the [project setup](README.md#running-the-project) for dependencies and
a prepared database. Start the shared backend from `backend/`, with its
virtual environment activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Start Vite from `frontend/`:

```bash
npm run dev
```

Open `http://localhost:5173` and choose **Equation Game**.

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | Prepared PostgreSQL database. |
| `VITE_API_BASE_URL` | Frontend API address, normally `http://localhost:8000/api/v1`. |
| `GAME_COLLECTION_EXPORT_KEY` | Backend CSV key, at least 16 characters. |
| `GAME_ML_EXPERIMENTAL_ENABLED` | Model inference flag; backend default false, Compose default true. |
| `GAME_ML_MODEL_ARCHIVE` | Absolute path to the trusted archive. |
| `GAME_ML_PYTHON` | Absolute path to the compatible isolated worker interpreter. |
| `GAME_ML_TIMEOUT_SEC` | Worker timeout; default 30 seconds, maximum 60. |
| `FRONTEND_URL` | Browser origin used by the backend. |
| `GAME_ML_CONTAINER_NETWORK` | Compose's flag for its private bridge-network handling. |

Docker Compose builds the worker at `/opt/game-ml` and mounts artifacts
read-only. A native installation needs its own compatible worker environment;
the regular backend Python does not satisfy the frozen runtime contract.
The [inference guide](backend/app/modules/game/research_inference/README.md)
lists the separate researcher bearer/manifest settings.

## API and database

These paths use the prefix `/api/v1/game`.

| Method | Path | Use |
| --- | --- | --- |
| POST | `/sessions` | Create/recover a Game session. |
| POST | `/events` | Record a gameplay event. |
| POST | `/task-attempts` | Save a task summary. |
| POST | `/sessions/{game_session_id}/complete` | Calculate results and acknowledge completion. |
| GET | `/variant-usage` | Read learner variant history. |
| GET | `/results/{game_session_id}` | Read the saved result. |
| GET | `/results/{game_session_id}/ml-inputs` | Read ML input details. |
| POST | `/sessions/{game_session_id}/research-verification` | Request inference with a completion receipt. |
| POST | `/sessions/{game_session_id}/research-verification/cancel` | Cancel receipt access. |
| GET | `/sessions/{game_session_id}/ml-prediction` | Researcher bearer/manifest inference. |
| GET | `/exports/collection` | Protected CSV ZIP download. |

Gameplay tables are `game_sessions`, `gameplay_events`, `game_task_attempts`
and `game_results`. Session context includes learner, concept, learning cycle
and assessment phase. Learner codes provide record linkage, not login.
Schema changes follow [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md).

## Code, research and checks

| Location | Responsibility |
| --- | --- |
| [frontend/src/game/](frontend/src/game/) | Phaser scenes, collection queues and result UI. |
| [backend/app/modules/game/](backend/app/modules/game/) | Persistence, feature calculations and exports. |
| [research_inference/](backend/app/modules/game/research_inference/) | Evidence adapter, access checks and isolated worker. |
| [ml/](backend/app/modules/game/ml/) | Offline data preparation, verification and comparative experiments. |

Offline tools cover chronology/session validation, independent teacher
assessments, retrospective/prospective cohorts and synthetic development data.
Their experiments are separate from the frozen model served by the app.
The development-demo app is also separate from normal learner collection.

From `backend/`:

```bash
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q tests/test_game_*.py
```

Optional local PostgreSQL/private-artifact/runtime tests skip when their
requirements are absent. From `frontend/`:

```bash
npm test
node tests/gameUi.e2e.mjs
node tests/gameLanguage.e2e.mjs
```

The UI/language browser scripts use mocked API replies and require Chrome.
Set `GAME_TEST_CHROME` if the default executable path differs. These commands
are instructions, not new test results from this documentation edit; recorded
checks are in the [merge report](docs/merge-reviews/resolv-main-20261025.md).

Remaining work includes Mystery Reveal, Game-specific sign support, using the
curriculum bank in Phaser, and further model/device evaluation.

More detail: [architecture](GAME_MODAL_FILE_STRUCTURE.md),
[collection runbook](backend/app/modules/game/SCHOOL_COLLECTION_RUNBOOK.md),
[offline research](backend/app/modules/game/ml/RESEARCH_README.md)
and [isolated demo](backend/app/modules/game/DEVELOPMENT_DEMO.md).
