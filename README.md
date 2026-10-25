# Sign-Supported AI Tutor — Sign & Learn

An accessible Grade 10 Mathematics research prototype for Deaf and
speech-impaired learners, currently focused on **linear equations**. The
application combines bilingual assessment, equation games, adaptive teaching,
avatar-supported explanations, and targeted remedial practice.

**Implementation snapshot: 2026-10-25**, following the `resolv_main` merge into
`main` (`7f8e23f`). This README describes the current code; linked milestone
reports also contain historical results and earlier implementation states.

## Contents

- [Components and current status](#the-four-components)
- [Learning flow and integration](#learning-flow-and-integration)
- [Diagnostic Quiz](#1-diagnostic-quiz)
- [Game-Based Learning Analytics](#2-game-based-learning-analytics)
- [Adaptive AI Tutor and avatar](#3-adaptive-ai-tutor-and-sign-supported-avatar)
- [Non-Improvement / Remedial Support](#4-non-improvement--remedial-support)
- [Technology and repository layout](#technology-and-repository-layout)
- [Setup and configuration](#setup-and-running)
- [APIs and data ownership](#api-map-and-data-ownership)
- [Verification and tests](#verification-and-tests)
- [Remaining work](#remaining-implementation-and-research-work)

## The four components

| Component | Navigation tab | Current implementation |
| --- | --- | --- |
| 1. Diagnostic Quiz | Quiz Assessment | Bilingual ten-question assessments, durable first-answer collection, diagnostic results, optional rotating banks and experimental misconception predictions. |
| 2. Game-Based Learning Analytics | Equation Game | Playable Drag & Drop and Hangman, six-task assessments, saved gameplay evidence, backend analytics and experimental proficiency estimates. |
| 3. Adaptive AI Tutor | AI Tutor | Automatic strategy selection from saved Quiz/Game results, bilingual worked examples and practice, local lesson retrieval, and Louise avatar playback. |
| 4. Non-Improvement / Remedial Support | Remedial Support | Answer evaluation, category-level weakness tracking, generated/fallback tutorial slides and targeted follow-up quizzes. The current entry uses a demonstration submission. |

All four tabs are present in the shared React application. **AI Tutor is the
default tab.** Quiz, Game and Tutor share a learner/cycle flow; Remedial Support
currently has its own user/history flow and is not automatically connected to
their assessment results.

## Learning flow and integration

1. Select an assigned learner code, for example `STU_001`, in Quiz or Game.
2. Complete the ten-question Quiz and one six-task Game assessment using the
   same code and learning cycle. Either assessment may come first.
3. Recover pending evidence before leaving a collection. Completed Quiz results
   offer both **Continue to Game** and **Continue to AI Tutor**; Game also
   offers continuation to the Tutor after collection is saved.
4. The Tutor checks saved pre-tutor results, selects a teaching strategy,
   and opens its lesson automatically. Missing evidence produces
   **Complete Quiz** / **Complete Game** actions.
5. Use worked examples, equation visuals, optional avatar playback, progressive
   hints and graded practice. Browser practice evidence can be exported.
6. Open **Remedial Support** separately to explore its evaluation → tutorial →
   targeted practice loop. Automatic post-tutor comparison and handoff into
   that loop remain integration work.

```mermaid
flowchart LR
    Q[Diagnostic Quiz] --> QR[Saved Quiz result]
    G[Drag & Drop or Hangman] --> GR[Saved Game result]
    QR --> S[Teaching strategy model]
    GR --> S
    S --> T[Bilingual lesson and avatar support]
    T --> P[Hints and graded practice]
    R[Separate Remedial tab: demo entry] --> E[Evaluate answers and track weaknesses]
    E --> L[Tutorial slides]
    L --> F[Targeted follow-up quiz]
    F --> E
```

Quiz/Game/Tutor share `student_id`, `concept_id=linear_equations`,
`learning_cycle_id` and assessment phase. Browser context is stored under
`learning.context.v1`; a new Quiz cycle cannot silently reuse an earlier Game's
results. The Tutor reads completed results for that exact learner/concept/cycle
and writes only Tutor-owned strategy predictions. Learner codes and browser
context are identifiers, not authenticated accounts.

See [the automatic Tutor flow](docs/TUTOR_AUTOMATIC_FLOW.md) for the result
selection and cycle contract.

## 1. Diagnostic Quiz

### Assessment and collection

- English, Sinhala and bilingual presentation, with ten questions progressing
  through **4 Easy, 4 Medium and 2 Hard** items.
- Multiple-choice answers with low/medium/high confidence, question-level
  response time, progress indicators and difficulty transitions.
- BODMAS reference support, visual feedback, up to three local practice tries,
  and result summaries with correct/incorrect counts and activity details.
- The backend stores **one official first answer per question**. Later practice
  tries remain browser evidence and do not replace the original answer or score.
- Assigned-code collection, a browser collection lock, durable pending writes,
  refresh recovery, retry handling and protection against changing learners
  while evidence is unsaved.
- Backend diagnostic analysis records mastery/support signals, provisional
  misconception evidence and confidence insights for Tutor consumption.
- Protected **Download Quiz CSV files** exports include saved session/response
  evidence and incomplete sessions. Export access uses a backend-configured key.

### Fixed and dynamic banks

**The fixed ten-question bank remains the default on `main`.** Dynamic banks
are implemented and can be selected explicitly:

| Mode | Configuration | Behaviour |
| --- | --- | --- |
| Fixed | Default, or `VITE_QUIZ_BANK_MODE=fixed` | Existing ten-question pre-assessment bank. |
| Released dynamic | `VITE_QUIZ_BANK_MODE=dynamic` | Requires installed `pp1_dynamic_v1` rows; selects one of six variants for each of ten logical slots. |
| Development dynamic | `VITE_QUIZ_DYNAMIC_DEV=true` and backend `QUIZ_DYNAMIC_DEV_ENABLED=true` | Uses `pp1_dynamic_v1_DRAFT` on an isolated local database. |

The rotating bank contains **60 items**: 24 Easy, 24 Medium and 12 Hard variants.
Each session still receives ten questions in the 4/4/2 pattern. Selections are
persisted in `quiz_session_questions`, so recovery uses the original plan.
The released path selects teacher-validated rows; the draft path is separate.
Bank installation and review must precede activation.

Frontend flags belong in `frontend/.env.local` for native Vite development, or
the frontend container environment. Restart Vite after changing them.

### Quiz ML and research tooling

- Fixed-bank results support export of **45 model inputs** for the separate
  Colab workflow; this does not itself run a prediction in the app.
- Dynamic sessions have a backend **62-feature** extractor and optional M1–M4
  misconception prediction, using saved first answers and the bundled model
  under `local_ml_artifacts/quiz_dynamic_62_demo/`.
- `QUIZ_ML_ENABLED=true` enables the released-bank prediction endpoint. The
  separate SQLite demo also requires its development gates.
- The bundled dynamic model is **synthetic engineering demo only**, with
  `research_validated=false`. It does not establish learner diagnostic accuracy.
  Unavailable/incompatible artifacts leave ordinary results visible.
- `research/quiz_m3/` provides independent teacher-assessment/consensus templates
  and an offline dataset pipeline. Option tags and rule-derived diagnoses do
  not substitute for independent teacher labels.

Implementation: [frontend Quiz](frontend/src/quiz/),
[backend Quiz](backend/app/modules/quiz/).
Guides: [collection/export](backend/app/modules/quiz/QUIZ_COLLECTION.md),
[dynamic bank](backend/app/modules/quiz/DYNAMIC_DEMO.md),
[dynamic features](backend/app/modules/quiz/DYNAMIC_ML_FEATURES.md),
[synthetic ML demo](backend/app/modules/quiz/DYNAMIC_SYNTHETIC_DEMO.md), and
[teacher-label pipeline](research/quiz_m3/README.md).

## 2. Game-Based Learning Analytics

### Playable modes and evidence

- **Drag & Drop:** solve equations using operation choices, drag interactions
  and tap alternatives, with step-by-step balance/equation feedback.
- **Hangman:** solve for `x` using an on-screen numeric keypad, with hints,
  wrong-attempt feedback, progress and a completion summary.
- Both modes select **six tasks: 2 Easy, 2 Medium and 2 Hard**. Variant-usage
  checks reduce repetition; they share the session and persistence layer.
- The three-card selection screen also displays **Mystery Reveal**, marked as
  coming next; its gameplay is not implemented.
- Sinhala is the primary Game language by default. Switching to English updates
  the current scene without restarting or losing the answer buffer.
- Responsive Phaser scenes support desktop/phone layouts, touch controls,
  hints, celebrations and progress/score summaries.
- Game APIs persist sessions, events and task attempts, then calculate results
  on the backend. Metrics include accuracy/success, completion, attempts/retries,
  hints, skipped steps and elapsed time.
- Durable queues, acknowledgement checks and interruption recovery protect
  evidence. Local/unverified results remain distinguishable from saved completion.
- Protected **Download Game CSV files** exports are available; pending writes
  must be recovered before exporting or ending collection.

### Game ML and research tooling

- Result panels show saved ML input details and, when eligible, a model estimate
  of **Beginner / Intermediate / Advanced**, with class probabilities.
- A newly acknowledged completion can issue a short-lived, one-use receipt
  bound to that exact session. The browser automatically requests an estimate
  when the session is saved; missing/expired receipts leave it unavailable.
- Inference validates saved evidence and runs the frozen **nine-feature** model
  in an isolated worker. It checks **Python 3.13.12** and pinned numerical
  dependencies before loading the trusted archive.
- The separate bearer/manifest researcher endpoint retains its own access
  checks, distinct from the browser completion-receipt flow.
- Predictions are experimental, are not teacher verification, and do not
  overwrite gameplay evidence or ordinary heuristic analytics. Receipts live
  in memory and currently assume a single backend process.
- Offline tooling covers session/chronology verification, independent teacher
  assessments, retrospective/prospective cohort preparation, comparative ML,
  and synthetic development datasets. These experiments are separate from the
  deployed frozen prediction path.
- A separate development-demo app/page supports isolated synthetic sessions;
  it is not the normal learner collection backend.

Phaser currently uses its **local equation variants**. The seeded curriculum/Game
content bank is not yet the automatic question source. Mystery Reveal and
Game-specific sign support remain future work.

Guides: [frontend Game](frontend/src/game/README.md),
[architecture](GAME_MODAL_FILE_STRUCTURE.md),
[collection runbook](backend/app/modules/game/SCHOOL_COLLECTION_RUNBOOK.md),
[offline research](backend/app/modules/game/ml/RESEARCH_README.md),
[frozen inference](backend/app/modules/game/research_inference/README.md),
[current receipt implementation](backend/app/modules/game/research_inference/browser_gate.py),
and [isolated demo](backend/app/modules/game/DEVELOPMENT_DEMO.md).

## 3. Adaptive AI Tutor and sign-supported avatar

### Automatic teaching and practice

- Uses the supplied **`strategy-ml-v1`** preprocessing/Logistic Regression
  pipeline to select `step_by_step`, `worked_example_based`,
  `conceptual_explanation`, `progressive_hints` or `advanced_challenge`.
- Derives prior mastery from the saved **pre-tutor Quiz**, rather than a browser
  score override. Matching Quiz/Game results and the model decision are linked
  through the saved Tutor prediction.
- Presents four lesson paths: **Foundation, One Step, Two Step and Extended**,
  with **10 worked examples and 8 practice questions** in the current bank.
- Covers balance/equality, inverse operations, two-step equations, variables
  on both sides, brackets, denominators, negative coefficients and fractional
  solutions. Worked examples check solutions by substitution.
- Shows English/Sinhala instructions, equation diagrams, example navigation,
  progressive hints, feedback and contextual avatar support. Text and equations
  remain available when playback is unavailable.
- Grades known practice questions using exact fractions, accepting equivalent
  decimal/fraction answers without executing a submitted expression.
- Records attempts, hint/solution use and avatar interactions in browser
  practice evidence. JSON export is available; this telemetry is not
  automatically persisted to Supabase.
- Missing assessments or model/request failures produce explicit states; the
  automatic flow does not silently choose a default strategy.

### Retrieval and optional generation

**Ask about this step** retrieves relevant bilingual notes from the local
linear-equation corpus using BM25, with source excerpts and lesson context.
This works without an API key. Optional generation uses
`RAG_GENERATION_ENABLED` and a backend-only `OPENAI_API_KEY`; provider failure
falls back to retrieved notes. This corpus is separate from the shared
curriculum database.

### Louise avatar and animation package

- Runtime model: `frontend/public/models/louise_signs_master.glb`.
- **153 prototype actions**, including **70 connected explanation flows** for
  introductions, worked steps, hints and contextual explanations.
- Baked phrase timings drive captions, equation highlights, phrase seeking and
  replay. Ordered equation reading preserves repeated symbols and positions.
- Controls include preview opt-in, pause/resume, replay, speed and view options;
  reduced-motion preferences and missing-model fallback are supported.
- Default playback is **validated-only**. Reviewers can explicitly preview
  unvalidated gestures; lexical clips still require qualified sign review.
- Source-referenced number revisions and mathematical choreography improve the
  prototype without claiming full Sri Lankan Sign Language translation.
  No lexical motion is generated at runtime.
- Canonical manifests live in `avatar-sign-package/manifest/`; the backend's
  `sign_package/` is a deployment snapshot checked for consistency.

Guides: [lesson implementation](docs/GRADE10_TUTOR.md),
[automatic integration](docs/TUTOR_AUTOMATIC_FLOW.md),
[strategy model](docs/TUTOR_STRATEGY_MODEL.md),
[retrieval/generation](docs/TUTOR_RAG.md),
[avatar package](avatar-sign-package/README.md),
[connected flows](avatar-sign-package/docs/EXPLANATION_FLOWS.md), and
[number/sign references](avatar-sign-package/docs/SLSL_REFERENCE_REVISION.md).

## 4. Non-Improvement / Remedial Support

This component implements a separate evaluation and practice loop inside the
shared application; it is no longer only a gateway placeholder.

- Evaluates submitted linear-equation answers, returning per-answer correctness,
  error descriptions, overall accuracy and an encouraging summary.
- Supports six categories: **single variable, two step, negative numbers, basic
  fractions, variables on both sides and distributive equations**.
- Aggregates mistakes by category, ranks weakness severity, tracks historical
  attempts and flags active issues in PostgreSQL.
- Generates a tutorial for the highest-priority weakness using optional
  **DeepSeek** integration. Category-specific fallback tutorials work without
  an API key or when generation fails.
- Displays short tutorial slides, worked steps, tips and encouragement, then
  presents **five fresh questions** across the categories with errors.
- Re-evaluates follow-up answers and repeats targeted support when needed.
  A perfect submission resolves submitted categories and records the user as
  finished; subsequent evaluations use that completion record.
- Provides visual question cards, progress, celebrations, mute/settings controls
  and a Google Translate widget for English/Sinhala support.
- Stores category history in `ai_tutor_ml_insights` and completion in
  `ai_tutor_finishers`, using its own PostgreSQL driver/service.

**Current integration limits:** Start Evaluation posts three fixed demonstration
answers under `student_001`. It does not load the active shared Quiz/Game learner
or a genuine post-tutor reassessment. Despite the filename `ml_analyzer.py`,
weakness severity and issue flags currently use deterministic rules/history,
not a separately trained classifier. The completion flag and 100% UI represent
application behaviour, not a validated mastery measurement. This module requires
PostgreSQL; the isolated SQLite regression below does not exercise its
database-dependent evaluation path.

Implementation: [Remedial UI](frontend/src/components/NonImprovementSection.tsx),
[demo entry](frontend/src/components/NonImprovementSectionStartScreen.tsx),
[API](backend/app/modules/non_improvement_section_tutor/main.py),
[weakness analysis](backend/app/modules/non_improvement_section_tutor/services/ml_analyzer.py),
and [tutorial generation](backend/app/modules/non_improvement_section_tutor/services/tutorial_generator.py).

## Technology and repository layout

| Layer | Implementation |
| --- | --- |
| Web application | React 19, TypeScript, Vite, CSS and Framer Motion |
| Games | Phaser, shared session/queue layer and local equation variants |
| Avatar | Google `<model-viewer>`, GLB action library and JSON manifests |
| API | FastAPI, Pydantic, SQLAlchemy and Alembic |
| Database | PostgreSQL / Supabase; isolated SQLite for supported tests/demos |
| Models/research | scikit-learn, joblib, pandas, NumPy and SciPy |
| Optional providers | OpenAI for Tutor generation; DeepSeek for Remedial tutorials |
| Development | Native Python/Node or Docker Compose |

```text
backend/
  app/modules/quiz/                          Quiz sessions, diagnostics and ML
  app/modules/game/                          Gameplay persistence and analytics
    ml/                                     Offline research/data tooling
    research_inference/                     Frozen worker and access gates
  app/modules/tutor/                         Strategy, lessons, retrieval, signs
  app/modules/non_improvement_section_tutor/ Remedial evaluation and tutorials
  app/modules/curriculum/                    Shared curriculum ORM models
  alembic/versions/                          Scoped schema revisions
  scripts/                                  Seeds, exports and dataset utilities
  tests/                                    Backend regression tests
frontend/
  src/quiz/                                 Quiz UI and durable collection
  src/game/                                 Phaser scenes, collection and ML UI
  src/components/                            Tutor, avatar and Remedial UI
  src/learningContext.ts                    Shared Quiz/Game/Tutor cycle context
  public/models/                            Runtime Louise GLB
  tests/                                    Unit and local browser checks
avatar-sign-package/                        Canonical manifests/tools/reviews
local_ml_artifacts/                         Bundled trusted prediction artifacts
research/quiz_m3/                           Teacher-label templates and protocol
docs/                                      Integration/verification reports
avatar/                                    Historical procedural research only
compose.yaml                               Development backend/frontend services
```

The old scripts in `avatar/` are not the runtime pipeline. Private research
datasets and credentials do not belong in committed artifact folders.

## Setup and running

### Prerequisites and database

- Local version files specify **Python 3.13.14** and **Node 24.18.0**.
- Use PostgreSQL for the complete four-component application. Use a prepared
  schema/question bank, or prepare a disposable development database with the
  component owners using [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md).
- Current Alembic head: **`20261021_0008`**, adding Quiz bank metadata and saved
  dynamic selections. Its parent Quiz tables must already exist; the chain
  does not recreate the entire application from an empty database.
- This revision is required even for the fixed Quiz because current ORM queries
  use its columns. Bank seeds/releases are separate from schema migration.

Create a root `.env` using [`.env.example`](.env.example) as a guide. Preserve
an existing configured file. The template currently repeats `DATABASE_URL`;
keep **one populated entry**, removing its duplicate empty assignment.

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
FRONTEND_PORT=5173
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

The URL is a placeholder. Backend settings load the root `.env`; explicit
environment variables take precedence. Optional configuration is described below.
No LLM key is needed for local retrieval or Remedial fallback tutorials.

### Native development

From the repository root, prepare and start the backend:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

On Windows, create the environment with `py -3.13 -m venv .venv`, activate
`.venv\Scripts\Activate.ps1`, and use `npm.cmd` if PowerShell blocks `npm.ps1`.
Skip environment creation/dependency installation when already prepared.

Open the app at `http://localhost:5173`, Swagger at
`http://localhost:8000/docs`, and health at
`http://localhost:8000/api/v1/health`. Database connectivity has a separate
`/api/v1/db-health` endpoint. For a custom API address set
`VITE_API_BASE_URL=http://localhost:8000/api/v1` in `frontend/.env.local`.

The main app also initializes Remedial tables on startup; this does not replace
preparing the Quiz/Game/Tutor schema.

### Docker Compose

After preparing `.env` and the database:

```bash
docker compose up --build
```

Compose starts frontend/backend; it **does not provision PostgreSQL**. The
backend image builds a separate `/opt/game-ml` worker environment using
Python **3.13.12**, independently of the native version file. Bundled models are
mounted read-only from `local_ml_artifacts/`. Quiz/Game ML flags are enabled by
default in Compose, but eligibility, artifact/runtime checks and unavailable
states still apply.

Compose forwards only entries listed in `compose.yaml`. Optional RAG settings
need corresponding backend container environment entries; a variable in the
host root `.env` is not automatically forwarded into a container.

### Important configuration

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection for the application and Remedial history. |
| `FRONTEND_URL` | Expected browser origin; Compose derives it from the frontend port. |
| `VITE_API_BASE_URL` | Frontend API base including `/api/v1`; Remedial derives its `/api` base from it. |
| `GAME_COLLECTION_EXPORT_KEY`, `QUIZ_COLLECTION_EXPORT_KEY` | Separate backend CSV-download keys, at least 16 characters each. |
| `VITE_QUIZ_BANK_MODE` | Explicit `dynamic` opt-in or the default `fixed` bank. |
| `VITE_QUIZ_DYNAMIC_DEV`, `QUIZ_DYNAMIC_DEV_ENABLED` | Frontend/backend gates for the isolated draft bank. |
| `QUIZ_ML_ENABLED` | Optional dynamic Quiz inference; code default false, Compose default true. |
| `QUIZ_DYNAMIC_ML_DEMO_ENABLED` | Additional gate for the designated isolated SQLite demo. |
| `GAME_ML_EXPERIMENTAL_ENABLED` | Experimental Game inference; code default false, Compose default true. |
| `GAME_ML_MODEL_ARCHIVE`, `GAME_ML_PYTHON` | Absolute trusted archive/compatible interpreter paths; Compose sets both. |
| `RAG_ENABLED`, `RAG_TOP_K` | Tutor local retrieval, enabled by default; default retrieval count 3. |
| `RAG_GENERATION_ENABLED`, `OPENAI_API_KEY`, `RAG_MODEL`, `RAG_TIMEOUT_SEC` | Optional Tutor generation; generation defaults off. |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` | Optional Remedial generation; configure provider URL as `https://api.deepseek.com/v1`. |

Keep database/provider secrets in backend configuration, outside `VITE_*` values.
Export keys are entered into researcher download controls and must not be bundled
as frontend environment values. Native Game inference needs its separate
compatible runtime; the ordinary backend interpreter is not sufficient. The
inference guide covers separate researcher bearer/manifest settings.

## API map and data ownership

| Component | Principal routes |
| --- | --- |
| System | `GET /api/v1/health`, `GET /api/v1/db-health` |
| Quiz | `/api/v1/quiz/questions`, `/sessions`, `/sessions/{id}/questions`, `/sessions/{id}/responses`, `/sessions/{id}/complete`, `/sessions/{id}/analyze`, `/sessions/{id}/result`, `/sessions/{id}/experimental-prediction`, `/exports/collection` |
| Game | `/api/v1/game/sessions`, `/events`, `/task-attempts`, `/sessions/{id}/complete`, `/results/{id}`, `/results/{id}/ml-inputs`, `/variant-usage`, `/exports/collection` |
| Game inference | `POST /api/v1/game/sessions/{id}/research-verification`; separate protected `GET /api/v1/game/sessions/{id}/ml-prediction` |
| Tutor | `/api/v1/tutor/learning-status`, `/adaptive-lesson/from-results`, `/strategy/from-results`, `/grade10/{level}`, `/practice/check`, `/rag/answer`, `/rag/status`, `/sign-plan` |
| Remedial | `POST /api/evaluate`; `GET /api/categories`, `/api/quiz/{category}`, `/api/quiz/adaptive/{user_id}`, `/api/focus-area/{user_id}`, `/api/health` |

Abbreviated paths in a cell use that component's prefix. Swagger documents
request methods and schemas in full.

Quiz owns questions/options, sessions, official responses, selections and Quiz
results. Game owns sessions, events, task attempts and Game results. Tutor reads
those results and owns `tutor_strategy_predictions`. Remedial owns its separate
insight/completion tables. Old unlinked results must not be relabelled to
manufacture a shared learning cycle.

The curriculum module has six shared tables for versions, units, concepts,
mappings, document registrations and content. Historical seed verification
records **10 concepts, 2 document registrations and 11 draft content pieces**,
plus **8 Game activities and 18 draft variants**. These are historical seed
counts, not a fresh live inventory. Automatic consumption by the current
Tutor/Phaser content paths remains pending.

Read the [migration guide](MIGRATION_GUIDE.md) before schema changes. Revision
`20261021_0008` was confirmed present by read-only schema inspection during the
2026-10-25 merge review; no migration or reseed was performed in that review.
See [curriculum implementation](backend/app/modules/curriculum/README.md),
[curriculum seed](backend/scripts/EQUATIONS_CURRICULUM.md), and
[Game bank seed](backend/scripts/EQUATIONS_GAME_ACTIVITIES.md).

## Verification and tests

Latest recorded merge verification on **2026-10-25**:

| Check | Recorded result |
| --- | --- |
| Backend isolated regression | **840 passed, 34 skipped, 1 deselected** |
| Frontend unit tests | **34 passed** |
| TypeScript / Vite production build | Passed, with a bundle-size warning |
| Frontend lint | Completed with React hook/ref warnings |
| Tutor browser regression | Passed: 153 clips, playback, grading, mobile and fallbacks |
| Quiz browser regression | Passed: refresh recovery, first answers and Tutor/Game handoffs |
| Game browser regression | Passed: Drag & Drop/Hangman and desktop/phone input/layout |
| Docker Compose configuration | Passed; a full image build was not verified |

These are recorded merge checks, not a claim that every optional integration
or live model deployment passed. See [the merge verification report](docs/merge-reviews/resolv-main-20261025.md).

Run the isolated backend regression from `backend/`:

```bash
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q \
  --ignore=tests/test_database_queries.py -k 'not test_linear_tutor_evaluation'
```

The unfiltered suite has an existing collection failure because
`test_database_queries.py` imports missing `app.db.queries`.
`test_linear_tutor_evaluation` requires the separate PostgreSQL Remedial path
and cannot run against this SQLite configuration. Skipped checks need optional
local PostgreSQL databases, private fixtures or the pinned ML runtime. Use
disposable test databases, not the shared learner database.

From `frontend/`:

```bash
npm test
npm run build
npm run lint
npm run test:e2e -- --ui-only
node tests/quiz.e2e.mjs
node tests/gameUi.e2e.mjs
```

Browser scripts require Chrome and installed dependencies. Set
`TUTOR_TEST_CHROME`, `QUIZ_TEST_CHROME` or `GAME_TEST_CHROME` to its executable
where the default path does not match your platform. Tutor browser checks use
a disposable local database; Quiz/Game UI checks mock API replies. Screenshots
are under ignored `frontend/artifacts/`. To include full avatar motion sampling,
use `npm run test:e2e` without `--ui-only`.

## Remaining implementation and research work

- Replace the Remedial demo entry with genuine reassessment input, shared
  learner/cycle linkage and a defined post-tutor improvement comparison.
- Implement Mystery Reveal and pending Game sign-support interactions.
- Connect curriculum/content banks to runtime question/lesson consumers and
  complete empty-database schema reproducibility.
- Review bilingual mathematics and lexical avatar clips with qualified
  teachers/sign reviewers. The prototype does not provide validated full SLSL
  translation.
- Validate predictions and teaching effectiveness with independently labelled
  learner evidence. Synthetic outputs, practice completion and training metrics
  do not establish research effectiveness.
- Complete authenticated learner/researcher access, centralized Tutor practice
  persistence and broader device/deployment evaluation. Browser learner codes
  and Google Translate output do not substitute for these checks.
