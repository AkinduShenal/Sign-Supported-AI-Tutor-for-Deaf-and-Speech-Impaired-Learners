# Sign & Learn — Sign-Supported AI Tutor

A Grade 10 Mathematics project for Deaf and speech-impaired learners. We are
working on linear equations, with English and Sinhala explanations, visual
practice and avatar support.

The app has four components: Diagnostic Quiz, Equation Game, AI Tutor and
Remedial Support. Quiz and Game results feed into the Tutor. Remedial Support
has its own evaluation and follow-up practice flow; connecting it to the shared
assessment cycle is still in progress.

Last updated: 27 October 2026.

## Contents

- [How the app works](#how-the-app-works)
- [Components](#components)
- [Project structure](#project-structure)
- [Running the project](#running-the-project)
- [Configuration](#configuration)
- [APIs and database](#apis-and-database)
- [Tests](#tests)
- [Work still to do](#work-still-to-do)

## How the app works

The app opens on the **AI Tutor** tab. To load a lesson:

1. Enter the same assigned learner code, such as `STU_001`, in Quiz and Game.
2. Complete the ten-question Quiz and one six-task Game assessment. Either can
   be completed first.
3. Wait for the answers and game events to save. Use the recovery controls if
   there are pending writes.
4. Choose **Continue to AI Tutor**. The Tutor reads both saved results and
   loads the lesson selected by the teaching-strategy model. Quiz also has a
   **Continue to Game** button.

Quiz, Game and Tutor share `student_id`, `learning_cycle_id`, assessment phase
and `concept_id=linear_equations`. The browser keeps the active learner/cycle
under `learning.context.v1`. Starting a new Quiz cycle prevents an old Game
result from being reused for the new assessment.

The Tutor asks for any missing assessment instead of selecting a lesson without
it. Learner codes keep records together; they are not a login system.

[Automatic Tutor integration](docs/TUTOR_AUTOMATIC_FLOW.md) explains the result
lookup and learning-cycle handling.

## Components

Each component also has its own README:

| Component | Documentation |
| --- | --- |
| Diagnostic Quiz | [Diagnostic_Quiz_README.md](Diagnostic_Quiz_README.md) |
| Game-Based Learning Analytics | [Game_Based_Learning_Analytics_README.md](Game_Based_Learning_Analytics_README.md) |
| Adaptive AI Tutor | [Adaptive_AI_Tutor_README.md](Adaptive_AI_Tutor_README.md) |
| Non-Improvement / Remedial Support | [Remedial_Support_README.md](Remedial_Support_README.md) |

### 1. Diagnostic Quiz

The Quiz has ten multiple-choice questions: **4 Easy, 4 Medium and 2 Hard**.
Learners can use English, Sinhala or both. Each answer includes a confidence
level, and the app records the time spent on the question.

The interface includes progress indicators, difficulty transitions, a BODMAS
reference, answer feedback and up to three practice tries. Only the **first
answer** is saved as the official response and used for the score. Later tries
stay in browser storage as practice evidence.

Collection supports assigned learner codes, a single-tab lock, queued writes
and refresh recovery. Unsaved answers must be recovered before switching
learners or leaving the collection. Results include correct/incorrect counts
and activity details; the backend also produces mastery, support, confidence
and provisional misconception signals for the Tutor.

The fixed question bank is the default. Rotating banks are also available:

| Bank | How to select it | Questions |
| --- | --- | --- |
| Fixed | Default, or `VITE_QUIZ_BANK_MODE=fixed` | The existing ten-question bank. |
| Released dynamic | `VITE_QUIZ_BANK_MODE=dynamic` | One variant from each of ten slots in `pp1_dynamic_v1`. |
| Development dynamic | `VITE_QUIZ_DYNAMIC_DEV=true` and backend `QUIZ_DYNAMIC_DEV_ENABLED=true` | Draft bank `pp1_dynamic_v1_DRAFT`, restricted to a local development database. |

The dynamic bank has **60 items**: six variants per slot, with 24 Easy,
24 Medium and 12 Hard items overall. Sessions still follow the 4/4/2 pattern.
Their selected question IDs are saved in `quiz_session_questions`, so a reload
keeps the same plan. Install the relevant bank before enabling it; the released
mode selects teacher-validated rows.

Quiz ML has two paths. Fixed-bank results can export **45 inputs** for the
separate Colab workflow. Dynamic-bank sessions use a **62-feature** backend
extractor and an optional M1–M4 prediction endpoint, enabled through
`QUIZ_ML_ENABLED`. The bundled model in
`local_ml_artifacts/quiz_dynamic_62_demo/` uses synthetic training data and has
`research_validated=false`. It is an engineering demo, not a validated learner
diagnosis. Missing or incompatible models leave the ordinary results available.
The isolated SQLite inference demo has additional development flags.

The researcher panel can download saved Quiz sessions and responses as CSVs,
including incomplete sessions. Independent teacher-assessment and consensus
label templates are in `research/quiz_m3/`; Quiz option tags are kept separate
from those labels.

See [Quiz collection](backend/app/modules/quiz/QUIZ_COLLECTION.md),
[dynamic bank setup](backend/app/modules/quiz/DYNAMIC_DEMO.md),
[feature extraction](backend/app/modules/quiz/DYNAMIC_ML_FEATURES.md),
[synthetic inference demo](backend/app/modules/quiz/DYNAMIC_SYNTHETIC_DEMO.md)
and [teacher-label dataset preparation](research/quiz_m3/README.md).

### 2. Game-Based Learning Analytics

Two equation games are playable:

- **Drag & Drop:** choose and apply operations to solve an equation. Tap
  controls are available as an alternative to dragging.
- **Hangman:** solve for `x` and enter the answer using the on-screen keypad.

Both use six tasks: **2 Easy, 2 Medium and 2 Hard**. They share session handling,
variant-usage checks and backend synchronization. **Mystery Reveal** appears
on the selection screen as coming next; its gameplay is not implemented.

Sinhala is the default language. Switching to English updates the current
scene without resetting the question or answer buffer. Both games have hints,
wrong-answer feedback, progress, celebrations and summaries, with desktop and
phone layouts and touch controls.

The backend saves sessions, gameplay events and task attempts, then calculates
results from that evidence. Metrics cover success, completion, attempts,
retries, hints, skipped steps and elapsed time. Queued writes can be recovered
after an interruption. The UI distinguishes locally completed play from a
confirmed saved session. Saved Game data can be downloaded as CSV files from
the collection panel after pending writes are recovered.

Game results also include ML input details and an optional proficiency estimate
(**Beginner, Intermediate or Advanced**) with class probabilities. After a
session is saved, its completion response can issue a one-use receipt for an
automatic prediction request. The receipt expires after five minutes and is
bound to that session. Receipt state is kept in memory, so this flow currently
uses a single backend process.

The frozen **nine-feature** model runs in a separate worker with Python
**3.13.12** and pinned dependencies. Evidence, model checksums and runtime
versions are checked before inference. A separate researcher endpoint uses its
own bearer/manifest checks. Predictions are experimental and do not change the
saved Game results or heuristic analytics.

Offline research tools cover session and chronology checks, teacher assessments,
retrospective/prospective datasets, comparative ML and synthetic data. A separate
development-demo app supports synthetic sessions. Phaser still gets its
questions from the local variant bank; it does not yet consume the seeded
curriculum/Game bank.

See [Game frontend](frontend/src/game/README.md),
[file structure](GAME_MODAL_FILE_STRUCTURE.md),
[collection runbook](backend/app/modules/game/SCHOOL_COLLECTION_RUNBOOK.md),
[offline research](backend/app/modules/game/ml/RESEARCH_README.md),
[model worker](backend/app/modules/game/research_inference/README.md),
[current receipt flow](backend/app/modules/game/research_inference/browser_gate.py)
and [development demo](backend/app/modules/game/DEVELOPMENT_DEMO.md).

### 3. Adaptive AI Tutor

The Tutor uses the supplied **`strategy-ml-v1`** preprocessing and Logistic
Regression pipeline. It reads matching pre-tutor Quiz/Game results, takes prior
mastery from the Quiz and saves its teaching-strategy prediction. The five
strategies are:

- `step_by_step`
- `worked_example_based`
- `conceptual_explanation`
- `progressive_hints`
- `advanced_challenge`

Lessons cover **Foundation, One Step, Two Step and Extended** paths. The current
bank has **10 worked examples and 8 practice questions**, covering balance,
inverse operations, variables on both sides, brackets, denominators, negatives
and fractional solutions. Worked solutions include substitution checks.

The workspace shows bilingual instructions, equation diagrams, example
navigation, progressive hints and answer feedback. Practice grading uses exact
fractions and accepts equivalent decimal/fraction answers. Attempts, hints,
solution views and avatar interactions can be exported as browser practice
JSON; they are not automatically saved to Supabase. Missing results or model
errors are shown explicitly rather than replaced with a default strategy.

**Ask about this step** searches the local bilingual lesson corpus using BM25
and returns relevant notes with source excerpts. Retrieval works without a key.
Optional generated answers use `RAG_GENERATION_ENABLED` and a backend
`OPENAI_API_KEY`; failures fall back to the retrieved notes. The local corpus
is separate from the shared curriculum database.

#### Avatar support

The Louise model at `frontend/public/models/louise_signs_master.glb` contains
**153 prototype actions**, including **70 connected explanation flows**.
Phrase timings synchronize captions, equation highlights and replay. Ordered
equation reading keeps repeated symbols in their original positions.

The player has preview, pause/resume, replay, speed and view controls, plus
reduced-motion handling and text/visual fallbacks. Playback defaults to
validated-only; reviewers can opt into unvalidated gesture previews. Lexical
clips still need qualified sign review. The animations support mathematical
explanations and do not provide validated full SLSL translation or generate
new signing motion at runtime.

Canonical manifests are in `avatar-sign-package/manifest/`. The backend keeps
a checked deployment copy under `app/modules/tutor/sign_package/`. The older
procedural scripts in `avatar/` are retained for reference and are not used by
the app.

See [lesson implementation](docs/GRADE10_TUTOR.md),
[strategy model](docs/TUTOR_STRATEGY_MODEL.md),
[retrieval setup](docs/TUTOR_RAG.md),
[avatar package](avatar-sign-package/README.md),
[explanation flows](avatar-sign-package/docs/EXPLANATION_FLOWS.md)
and [number/sign references](avatar-sign-package/docs/SLSL_REFERENCE_REVISION.md).

### 4. Non-Improvement / Remedial Support

Remedial Support evaluates answers, identifies the main weakness, shows a
short tutorial and gives targeted practice. It handles single-variable and
two-step equations, negative numbers, basic fractions, variables on both sides
and the distributive property.

The backend groups mistakes by category, ranks their severity and keeps a
history of attempts and active issues. It generates a tutorial for the main
weakness through DeepSeek when configured; built-in category tutorials are
used without a key or if the request fails. The UI presents these as slides
with worked steps, tips and encouragement.

Follow-up quizzes contain **five fresh questions** across the categories with
errors. Answers are evaluated again, and the tutorial/practice loop repeats
when needed. A perfect submission clears the submitted issues and records the
user as finished. The interface includes visual questions, progress,
celebrations, mute/settings controls and an English/Sinhala Google Translate
widget.

History is stored in PostgreSQL tables `ai_tutor_ml_insights` and
`ai_tutor_finishers`. Although the analysis file is named `ml_analyzer.py`, its
current severity and issue logic uses rules and history, not a trained model.

The entry screen still submits **three fixed demo answers for `student_001`**.
It is not connected to the active Quiz/Game learner or a real post-tutor
assessment. Completion currently means a perfect submitted quiz; linking this
to measured improvement is unfinished. This component needs PostgreSQL and
cannot run its evaluation path against the SQLite test database.

Code: [Remedial interface](frontend/src/components/NonImprovementSection.tsx),
[demo entry](frontend/src/components/NonImprovementSectionStartScreen.tsx),
[API](backend/app/modules/non_improvement_section_tutor/main.py),
[analysis](backend/app/modules/non_improvement_section_tutor/services/ml_analyzer.py)
and [tutorial generator](backend/app/modules/non_improvement_section_tutor/services/tutorial_generator.py).

## Project structure

The frontend uses React 19, TypeScript, Vite, Phaser, Framer Motion and Google's
`<model-viewer>`. The backend uses FastAPI, Pydantic, SQLAlchemy and Alembic with
PostgreSQL/Supabase. Model and dataset tooling uses scikit-learn, joblib,
pandas, NumPy and SciPy.

```text
backend/
  app/modules/quiz/                          Quiz, diagnostics and Quiz ML
  app/modules/game/                          Gameplay, analytics and research
    ml/                                     Offline data/model tools
    research_inference/                     Frozen model worker and access checks
  app/modules/tutor/                         Strategy, lessons, retrieval and signs
  app/modules/non_improvement_section_tutor/ Remedial evaluation and tutorials
  app/modules/curriculum/                    Shared curriculum models
  alembic/versions/                          Database revisions
  scripts/                                  Seeds, exports and dataset utilities
  tests/
frontend/
  src/quiz/                                 Quiz UI and collection
  src/game/                                 Phaser games, collection and ML UI
  src/components/                            Tutor, avatar and Remedial UI
  src/learningContext.ts                    Shared learner/cycle context
  public/models/                            Louise avatar
  tests/
avatar-sign-package/                        Manifests, animation tools and reviews
local_ml_artifacts/                         Bundled prediction models
research/quiz_m3/                           Teacher-assessment templates
avatar/                                    Historical scripts
docs/                                      Integration and verification reports
compose.yaml
```

## Running the project

Use **Python 3.13.14** and **Node 24.18.0**, as listed in the repository version
files. The complete app needs PostgreSQL with the prepared schema and question
banks. See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) when setting up a database.
The Alembic chain does not yet recreate every application table from an empty DB.

### Environment

Create a root `.env` using [`.env.example`](.env.example). Keep an existing
configured file. The example currently has two `DATABASE_URL` entries; keep
one populated value and remove the empty duplicate.

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
FRONTEND_PORT=5173
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

Replace the URL placeholders with your development connection. Backend settings
read the root `.env`, with explicit environment variables taking precedence.
Local Tutor retrieval and Remedial fallback tutorials work without LLM keys.

### Backend

From the repository root:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

On Windows, use `py -3.13 -m venv .venv` and activate
`.venv\Scripts\Activate.ps1`. Reuse an existing environment if it is already set
up. Startup initializes the Remedial tables; the other component schemas and
question banks need to be prepared separately.

### Frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Use `npm.cmd` if PowerShell blocks `npm.ps1`. Open `http://localhost:5173`.
Swagger is at `http://localhost:8000/docs`; health checks are
`/api/v1/health` and `/api/v1/db-health`.

For a different API address, set
`VITE_API_BASE_URL=http://localhost:8000/api/v1` in `frontend/.env.local`.
Frontend Quiz flags also go there. Restart Vite after changing them.

### Docker

With `.env` and the database ready:

```bash
docker compose up --build
```

Compose starts the two app services, not PostgreSQL. It mounts the model folder
read-only and builds a separate Game ML environment at `/opt/game-ml`, using
**Python 3.13.12**. Native Game inference also needs this compatible isolated
runtime; the ordinary backend interpreter will not pass its version checks.

Compose enables Quiz/Game ML flags by default. A valid session, model and
runtime are still needed for a prediction. Only variables listed in
`compose.yaml` are forwarded; optional Tutor RAG settings need matching backend
container environment entries.

## Configuration

| Variable | Use |
| --- | --- |
| `DATABASE_URL` | Application and Remedial PostgreSQL connection. |
| `FRONTEND_URL` | Expected browser origin. Compose uses the frontend port. |
| `VITE_API_BASE_URL` | Frontend API address including `/api/v1`; Remedial derives its `/api` address from it. |
| `GAME_COLLECTION_EXPORT_KEY`, `QUIZ_COLLECTION_EXPORT_KEY` | CSV download keys; at least 16 characters each. |
| `VITE_QUIZ_BANK_MODE` | `fixed` by default; `dynamic` selects the released bank. |
| `VITE_QUIZ_DYNAMIC_DEV`, `QUIZ_DYNAMIC_DEV_ENABLED` | Frontend/backend flags for the local draft bank. |
| `QUIZ_ML_ENABLED` | Dynamic Quiz predictions. Backend default false; Compose default true. |
| `QUIZ_DYNAMIC_ML_DEMO_ENABLED` | Additional flag for the designated SQLite inference demo. |
| `GAME_ML_EXPERIMENTAL_ENABLED` | Game predictions. Backend default false; Compose default true. |
| `GAME_ML_MODEL_ARCHIVE`, `GAME_ML_PYTHON` | Absolute Game model/interpreter paths; Compose sets both. |
| `RAG_ENABLED`, `RAG_TOP_K` | Local Tutor retrieval; defaults true and 3. |
| `RAG_GENERATION_ENABLED`, `OPENAI_API_KEY`, `RAG_MODEL`, `RAG_TIMEOUT_SEC` | Optional Tutor answer generation; off by default. |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` | Optional Remedial generation; use `https://api.deepseek.com/v1` as the provider URL. |

Keep database/provider credentials in backend configuration. Export keys are
configured on the backend and entered into researcher download controls;
do not put them in frontend `VITE_*` values. Separate Game researcher
bearer/manifest settings are described in the inference guide.

## APIs and database

The main route groups are below. Paths after the first entry in a row use the
same component prefix. Swagger has the full methods and request schemas.

| Component | Routes |
| --- | --- |
| Quiz | `/api/v1/quiz/questions`, `/sessions`, `/sessions/{id}/questions`, `/sessions/{id}/responses`, `/sessions/{id}/complete`, `/sessions/{id}/analyze`, `/sessions/{id}/result`, `/sessions/{id}/experimental-prediction`, `/exports/collection` |
| Game | `/api/v1/game/sessions`, `/events`, `/task-attempts`, `/sessions/{id}/complete`, `/results/{id}`, `/results/{id}/ml-inputs`, `/variant-usage`, `/exports/collection` |
| Game ML | `POST /api/v1/game/sessions/{id}/research-verification`, `GET /api/v1/game/sessions/{id}/ml-prediction` |
| Tutor | `/api/v1/tutor/learning-status`, `/adaptive-lesson/from-results`, `/strategy/from-results`, `/grade10/{level}`, `/practice/check`, `/rag/answer`, `/rag/status`, `/sign-plan` |
| Remedial | `POST /api/evaluate`; `GET /api/categories`, `/api/quiz/{category}`, `/api/quiz/adaptive/{user_id}`, `/api/focus-area/{user_id}`, `/api/health` |

Quiz owns its question, session, response, selection and result tables. Game
owns gameplay sessions, events, attempts and results. Tutor reads those results
and writes `tutor_strategy_predictions`. Remedial uses its separate insight
and completion tables. Existing unlinked results are not reassigned to new
learning cycles.

Current Alembic head is **`20261021_0008`**. It adds Quiz bank metadata and saved
question selections and requires the existing Quiz tables. It is needed even
for fixed-bank sessions. Seeds and dynamic-bank releases are separate operations.
The 25 October merge review confirmed this revision on the configured database
through a read-only check; it did not apply migrations or reseed data.

The curriculum module has six shared tables for versions, units, concepts,
mappings, documents and content. Earlier seed checks recorded 10 concepts,
2 document registrations, 11 draft content pieces, 8 Game activities and
18 draft variants. Those are historical counts; Tutor and Phaser still use
their own content sources.

See [curriculum models](backend/app/modules/curriculum/README.md),
[curriculum seed](backend/scripts/EQUATIONS_CURRICULUM.md) and
[Game bank seed](backend/scripts/EQUATIONS_GAME_ACTIVITIES.md).

## Tests

The last full merge check was on **25 October 2026**:

| Check | Result |
| --- | --- |
| Backend isolated tests | 840 passed, 34 skipped, 1 deselected |
| Frontend unit tests | 34 passed |
| TypeScript / Vite build | Passed; bundle-size warning remains |
| Frontend lint | Completed with React hook/ref warnings |
| Tutor, Quiz and Game browser checks | Passed, including playback, recovery, handoffs and mobile layouts |
| Docker Compose config | Passed; a full image build was not checked |

[The merge report](docs/merge-reviews/resolv-main-20261025.md) records the checks
and their limits. These results are from that run, not a new test run for this
README edit.

From `backend/`, run the isolated suite:

```bash
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q \
  --ignore=tests/test_database_queries.py -k 'not test_linear_tutor_evaluation'
```

The exclusions cover two existing issues: `test_database_queries.py` imports
the missing `app.db.queries` module, and `test_linear_tutor_evaluation` needs
PostgreSQL rather than SQLite. Optional PostgreSQL, private-fixture and pinned
ML-runtime checks account for the skips. Use disposable databases for tests.

From `frontend/`:

```bash
npm test
npm run build
npm run lint
npm run test:e2e -- --ui-only
node tests/quiz.e2e.mjs
node tests/gameUi.e2e.mjs
```

Browser checks need Chrome and installed dependencies. Set `TUTOR_TEST_CHROME`,
`QUIZ_TEST_CHROME` or `GAME_TEST_CHROME` if the script's default path differs
from your installation. Tutor uses a disposable local database; the Quiz/Game
UI scripts mock API replies. Screenshots go to ignored `frontend/artifacts/`.
Run `npm run test:e2e` without `--ui-only` to include full avatar motion sampling.

## Work still to do

- Connect Remedial Support to real reassessment results and shared learner cycles.
- Implement Mystery Reveal and Game-specific sign support.
- Use the curriculum banks in runtime lessons/games and complete database setup
  from an empty instance.
- Review bilingual content and avatar signs with mathematics teachers and
  qualified sign reviewers.
- Evaluate models and teaching outcomes with independently labelled learner
  data. Synthetic predictions and practice completion are not validation results.
- Add authenticated access, centralized Tutor practice storage and further
  device/deployment testing.
