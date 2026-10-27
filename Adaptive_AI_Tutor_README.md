# Adaptive AI Tutor

The Tutor turns saved Quiz and Game results into a teaching plan for linear
equations. It combines bilingual worked examples, practice, retrieved lesson
notes and Louise avatar explanations. **AI Tutor** is the app's default tab.

Updated: 27 October 2026. [Project README](README.md)

## Loading a lesson

Complete Quiz and Game with the same assigned learner code and learning cycle,
then choose **Continue to AI Tutor**. Either assessment can come first. Pending
collection writes must be saved before leaving their module.

The Tutor checks completed pre-tutor evidence for that learner, concept and
cycle. It derives prior mastery from the saved Quiz score, runs the teaching
strategy model and returns a lesson. Missing assessments produce completion
actions; errors do not silently switch to a default strategy.

Quiz/Game/Tutor share browser context through `learning.context.v1`. Starting
a new Quiz cycle prevents an older Game result from being reused. Historical
unlinked results are not relabelled. Learner codes are identifiers, not accounts.

## Teaching strategy and content

The supplied **`strategy-ml-v1`** pipeline includes its preprocessing and
Logistic Regression estimator. Its five teaching strategies are:

| Strategy | Approach |
| --- | --- |
| `step_by_step` | Work through the equation one operation at a time. |
| `worked_example_based` | Follow a solved example before similar practice. |
| `conceptual_explanation` | Emphasize equality, balance and why operations work. |
| `progressive_hints` | Reveal help gradually while the learner attempts a solution. |
| `advanced_challenge` | Offer more demanding content when the lesson plan permits it. |

The lesson bank has **10 worked examples and 8 practice questions** across
Foundation, One Step, Two Step and Extended paths. Topics include inverse
operations, variables on both sides, brackets, denominators, negative
coefficients and fractional solutions. Worked examples check the answer by
substitution.

The workspace shows English/Sinhala instructions, equation diagrams, example
navigation, hints and answer feedback. Known practice questions are graded
using exact fractions, including equivalent decimal/fraction answers.
Mathematics stays visible when an avatar cannot play.

Attempts, hint/solution views, avatar interactions and timing can be exported
as practice JSON. That evidence is stored in the browser session, not
automatically persisted to Supabase. It is separate from the official Quiz
and Game assessment records.

Model artifacts are in `backend/app/modules/tutor/artifacts/`. The integration
loads the supplied preprocessing/model rather than retraining it on startup.
Missing or incompatible artifacts cause an explicit failure. Model training
metrics do not establish the effectiveness of the teaching intervention.

## Asking about a step

**Ask about this step** searches the local bilingual linear-equation corpus
using BM25. Responses include relevant lesson notes and source excerpts.
This works without an API key and does not require a vector database.

Optional generated responses use backend settings `RAG_GENERATION_ENABLED`,
`OPENAI_API_KEY`, `RAG_MODEL` and `RAG_TIMEOUT_SEC`. Provider failures fall back
to the retrieved notes. The corpus in `knowledge/linear_equations.json` is
separate from the shared curriculum database.

## Avatar and signs

The runtime Louise model is
`frontend/public/models/louise_signs_master.glb`. It has **153 prototype actions**,
including **70 connected explanation flows** for introductions, worked steps,
hints and contextual explanations.

Phrase timings synchronize captions and equation highlights. Learners can
pause/resume, replay, seek phrases and change playback speed/view. Ordered
equation reading retains repeated symbols and their original positions.
Reduced-motion preferences and missing-model fallbacks are supported.

Playback defaults to validated-only. Reviewers can explicitly preview
unvalidated gestures. Lexical clips still require qualified sign review;
these educational motions do not provide validated full SLSL translation.
The app does not generate new signing motion at runtime.

Canonical manifests are in `avatar-sign-package/manifest/`. The backend keeps
a deployment copy under `app/modules/tutor/sign_package/`, with tests checking
that the copies agree. Historical procedural scripts under `avatar/` are not
part of runtime playback.

## Running and settings

Use [project setup](README.md#running-the-project) for dependencies, environment
and database preparation. Run the shared backend from `backend/`, with its
virtual environment activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Run the frontend from `frontend/`:

```bash
npm run dev
```

Open `http://localhost:5173`. Complete the prerequisite assessments or use the
retained developer preview endpoints when checking lesson content.

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | Prepared database containing Quiz/Game results and Tutor predictions. |
| `VITE_API_BASE_URL` | Frontend API address, normally `http://localhost:8000/api/v1`. |
| `FRONTEND_URL` | Expected browser origin. |
| `RAG_ENABLED` | Local retrieval, default true. |
| `RAG_TOP_K` | Retrieved note count, default 3. |
| `RAG_GENERATION_ENABLED` | Optional answer generation, default false. |
| `OPENAI_API_KEY` | Backend-only generation key. |
| `RAG_MODEL` | Configured generation model; default `gpt-4.1-mini` in code. |
| `RAG_TIMEOUT_SEC` | Generation timeout, default 15 seconds. |

Backend settings read the root `.env`; frontend variables go in
`frontend/.env.local`. For Docker, optional RAG settings need explicit backend
environment entries in `compose.yaml`.

## API and ownership

All paths below use `/api/v1/tutor`.

| Method | Path | Use |
| --- | --- | --- |
| GET | `/learning-status` | Check whether matching Quiz/Game evidence is ready. |
| POST | `/adaptive-lesson/from-results` | Select and return the automatic lesson. |
| POST | `/strategy/from-results` | Predict a strategy from saved results. |
| POST | `/strategy` | Check supplied diagnostic references against saved results and predict. |
| GET | `/grade10/{level}` | Developer lesson preview. |
| POST | `/adaptive-lesson` | Build a lesson from a diagnostic payload. |
| POST | `/practice/check` | Grade a known practice question. |
| POST | `/rag/answer` | Ask about lesson content. |
| GET | `/rag/status` | Check retrieval/generation availability. |
| GET | `/lessons/{concept_id}` | Read the retained static lesson. |
| POST | `/sign-plan` | Produce a mathematics sign/action plan. |

For example, the automatic lesson endpoint accepts this context:

```json
{
  "student_id": "STU_001",
  "learning_cycle_id": "00000000-0000-4000-8000-000000000001",
  "concept_id": "linear_equations"
}
```

Use the learner's actual cycle ID. The backend reads matching completed
pre-tutor Quiz/Game results and owns only `tutor_strategy_predictions`.
Repeated requests reuse the same result-pair/profile/model-version prediction.
It does not create missing assessment evidence or accept browser overrides of
the automatic strategy/prior mastery.

## Main files and checks

| File or directory | Responsibility |
| --- | --- |
| [AdaptiveTutor.tsx](frontend/src/components/AdaptiveTutor.tsx) | Student workspace and practice evidence. |
| [AvatarSignPlayer.tsx](frontend/src/components/AvatarSignPlayer.tsx) | Playback, timing and preview policy. |
| [backend Tutor](backend/app/modules/tutor/) | Model, lesson content, retrieval and action plans. |
| [learning_flow.py](backend/app/modules/tutor/learning_flow.py) | Matching assessment evidence for automatic teaching. |
| [teaching_explanations.py](backend/app/modules/tutor/teaching_explanations.py) | Teaching explanations. |
| [avatar-sign-package/](avatar-sign-package/) | Manifests, animation tools and review material. |

From `backend/`, run representative Tutor regression tests:

```bash
DATABASE_URL=sqlite+pysqlite:///:memory: ./.venv/bin/python -m pytest -q \
  tests/test_automatic_tutor.py tests/test_tutor_strategy.py \
  tests/test_trained_strategy_model.py tests/test_adaptive_lesson.py \
  tests/test_tutor_lesson_content.py tests/test_tutor_rag.py \
  tests/test_math_sign_planner.py tests/test_explanation_choreography.py
```

From `frontend/`:

```bash
npm test
npm run test:e2e -- --ui-only
```

The browser check uses a disposable database and local Chrome. Set
`TUTOR_TEST_CHROME` if needed. Remove `--ui-only` for the full avatar motion
sampling. Recorded results are in the
[25 October merge report](docs/merge-reviews/resolv-main-20261025.md);
this documentation edit does not claim a new application test run.

Remaining work includes teacher/sign review, centralized practice persistence,
authenticated learner access, curriculum-bank consumption and measured learner
outcomes. Remedial Support is currently a separate flow.

Further reading: [automatic integration](docs/TUTOR_AUTOMATIC_FLOW.md),
[lesson implementation](docs/GRADE10_TUTOR.md),
[model integration](docs/TUTOR_STRATEGY_MODEL.md),
[retrieval setup](docs/TUTOR_RAG.md),
[explanation flows](avatar-sign-package/docs/EXPLANATION_FLOWS.md)
and [sign references](avatar-sign-package/docs/SLSL_REFERENCE_REVISION.md).
