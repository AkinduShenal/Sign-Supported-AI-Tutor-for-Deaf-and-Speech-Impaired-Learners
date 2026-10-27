# Diagnostic Quiz

The Quiz collects a learner's initial linear-equation answers and produces the
diagnostic result used by the AI Tutor. It opens through **Quiz Assessment**
in the shared Sign & Learn application.

Updated: 27 October 2026. [Project README](README.md)

## Assessment flow

1. Enter an assigned learner code, such as `STU_001`.
2. Complete ten questions: **4 Easy, 4 Medium and 2 Hard**.
3. Select an answer and a low/medium/high confidence level for each question.
4. Review the result after all official answers and completion are saved.
5. Continue to Game or AI Tutor using the same learner and learning cycle.

English, Sinhala and bilingual views are available. The interface includes a
BODMAS reference, progress indicators, difficulty transitions and visual answer
feedback. A question allows up to three practice tries, but only the **first
answer** is the official response. Later tries stay in browser storage and do
not replace its score or recorded response time.

The collection queue survives a refresh. Identical retries reuse saved
responses, while conflicting answers are rejected. A browser lock prevents
two collection tabs from recording at once. Recover unsaved answers before
switching learners or leaving the collection.

## Question banks

| Mode | Selection | Bank |
| --- | --- | --- |
| Fixed | Default, or `VITE_QUIZ_BANK_MODE=fixed` | Existing ten-question pre-assessment. |
| Dynamic | `VITE_QUIZ_BANK_MODE=dynamic` | Released `pp1_dynamic_v1` bank. |
| Dynamic development | `VITE_QUIZ_DYNAMIC_DEV=true` and backend `QUIZ_DYNAMIC_DEV_ENABLED=true` | Local draft `pp1_dynamic_v1_DRAFT` bank. |

The rotating bank has **60 questions**, with six variants for each of ten
logical slots. There are 24 Easy, 24 Medium and 12 Hard items in total. Each
session chooses ten in the 4/4/2 pattern and saves that selection in
`quiz_session_questions`. Reloading uses the original plan.

The released mode selects teacher-validated rows. Install the appropriate bank
before enabling it; the development bank is restricted to a local database.
See [dynamic bank setup](backend/app/modules/quiz/DYNAMIC_DEMO.md) for the
seed/release procedure.

## Results and ML

The backend records correctness, response time and confidence, then derives
mastery/support signals, provisional misconception evidence and confidence
insights. The result page shows the score, correct/incorrect counts and activity
details. These saved results are also read by the Tutor.

There are two separate ML paths:

- The fixed bank can export **45 inputs** for the Colab workflow. This does not
  run a prediction in the app.
- Dynamic sessions use a **62-feature** backend extractor and an optional
  M1–M4 misconception prediction endpoint. The bundled model and manifest are
  in `local_ml_artifacts/quiz_dynamic_62_demo/`.

The dynamic model is trained on synthetic data and marked
`research_validated=false`. Its output is an engineering demonstration. Missing
or incompatible artifacts leave the ordinary Quiz result available.
Independent teacher-assessment and consensus templates live in
`research/quiz_m3/`; provisional option tags are not independent teacher labels.

## Running and configuration

Install dependencies and prepare the database using the
[project setup](README.md#running-the-project). Quiz runs inside the shared
backend/frontend, not as a separate service.

From `backend/`, with its virtual environment activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

From `frontend/`, in another terminal:

```bash
npm run dev
```

Open `http://localhost:5173` and choose **Quiz Assessment**.

| Setting | Where | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Root `.env` | Prepared PostgreSQL database. |
| `QUIZ_COLLECTION_EXPORT_KEY` | Backend | CSV download key, at least 16 characters. |
| `QUIZ_ML_ENABLED` | Backend | Enables dynamic-bank inference; code default false, Compose default true. |
| `QUIZ_DYNAMIC_DEV_ENABLED` | Backend | Allows the local draft bank. |
| `QUIZ_DYNAMIC_ML_DEMO_ENABLED` | Backend | Additional inference gate for the designated SQLite demo file. |
| `VITE_API_BASE_URL` | `frontend/.env.local` | API address, normally `http://localhost:8000/api/v1`. |
| `VITE_QUIZ_BANK_MODE`, `VITE_QUIZ_DYNAMIC_DEV` | Frontend | Select the bank as described above. |

Restart Vite after changing frontend flags. Docker only receives variables
listed in `compose.yaml`; add the relevant container environment entries when
changing options there.

Quiz requires migration **`20261021_0008`**, including when using the fixed bank.
The migration expects existing Quiz tables; question seeding is separate.
Read [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) before changing a shared database.

## API and saved data

All paths below use the prefix `/api/v1/quiz`.

| Method | Path | Use |
| --- | --- | --- |
| GET | `/questions` | Fetch questions for a concept/assessment phase. |
| POST | `/sessions` | Create or recover a session. |
| GET | `/sessions/{quiz_session_id}` | Read session status and saved responses. |
| GET | `/sessions/{quiz_session_id}/questions` | Recover the session's question plan. |
| POST | `/sessions/{quiz_session_id}/responses` | Save an official first answer. |
| POST | `/sessions/{quiz_session_id}/complete` | Confirm a fully answered assessment. |
| POST | `/sessions/{quiz_session_id}/analyze` | Produce/read its diagnostic result. |
| GET | `/sessions/{quiz_session_id}/result` | Read the saved result. |
| GET | `/sessions/{quiz_session_id}/experimental-prediction` | Optional dynamic Quiz prediction. |
| GET | `/exports/collection` | Protected collection ZIP download. |

Core tables are `quiz_questions`, `quiz_question_options`,
`misconception_mappings`, `quiz_sessions`, `quiz_session_questions`,
`quiz_responses` and `quiz_results`. A `quiz_comparisons` model also exists;
automatic post-tutor comparison and Remedial handoff are not wired into the
current UI.

Sessions carry `student_id`, `concept_id`, `learning_cycle_id` and assessment
phase. A new Quiz cycle cannot reuse a previous Game result for Tutor selection.
Learner codes identify records; they do not authenticate a learner.

The researcher panel exports saved sessions/responses, including incomplete
sessions. Recover pending writes first. Export keys belong in backend settings
and the researcher download control, not in a frontend build variable.

## Files and checks

| Location | Responsibility |
| --- | --- |
| [frontend/src/quiz/](frontend/src/quiz/) | Assessment UI, API calls and pending writes. |
| [backend/app/modules/quiz/](backend/app/modules/quiz/) | Models, persistence, diagnostics and inference. |
| [bankMode.ts](frontend/src/quiz/bankMode.ts) | Default/optional bank selection. |
| [research/quiz_m3/](research/quiz_m3/) | Teacher-label templates and dataset procedure. |

From `backend/`, run the component's isolated tests:

```bash
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q tests/test_quiz_*.py
```

From `frontend/`:

```bash
npm test
node tests/quiz.e2e.mjs
```

`npm test` includes shared frontend tests. The browser script uses mocked API
replies and needs Chrome; set `QUIZ_TEST_CHROME` to its executable if necessary.
No new application test run was performed for this documentation update.
The last combined run is recorded in the
[25 October merge report](docs/merge-reviews/resolv-main-20261025.md).

More detail: [collection/export](backend/app/modules/quiz/QUIZ_COLLECTION.md),
[dynamic features](backend/app/modules/quiz/DYNAMIC_ML_FEATURES.md),
[synthetic inference](backend/app/modules/quiz/DYNAMIC_SYNTHETIC_DEMO.md)
and [independent labels](research/quiz_m3/README.md).
