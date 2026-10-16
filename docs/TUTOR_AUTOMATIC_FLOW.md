# Automatic Tutor flow — 2026-10-16

The student workspace no longer offers a teaching-strategy dropdown, manual level
previews or diagnostic JSON upload. It opens the lesson selected by the bundled
`strategy-ml-v1` model from saved Quiz and Game results. The recommendation card
shows the selected teaching approach in English and Sinhala.

## Student journey

1. Use the same researcher-assigned code, such as `STU_001`, in Quiz and Game.
   The active code is remembered between modules; learner names are not used.
2. Complete the Quiz and one Game assessment. Either assessment may come first.
3. Choose **Continue to AI Tutor**, or open the AI Tutor tab. The completed Game
   continuation closes its saved collection before leaving, preserving queued
   evidence/export behavior. Pending or failed writes must be recovered first.
4. The Tutor checks saved results and automatically loads its strategy and lesson.
   Missing assessments display **Complete Quiz** / **Complete Game** actions.

The browser stores identifiers under `learning.context.v1`: the active student
and a separate learning-cycle ID for each code. It does not store mastery scores
or trust browser-supplied diagnostics for automatic selection. A fresh Quiz
after a previously started Quiz gets a new cycle so an earlier Game cannot be
silently reused. Game sessions use the current learner's cycle. Historical
unlinked or differently linked results are not relabelled or migrated.

The model author confirmed that training feature `prior_mastery_score` means
mastery from the Quiz **before tutoring**. The automatic backend therefore uses
the saved pre-tutor Quiz's `quiz_mastery_score` for this feature. There is no
constant prior, manual score input or browser override in this flow. Presentation
defaults to visual support with avatar availability; avatar visibility/playback
controls remain separate from strategy selection.

## Backend

`GET /api/v1/tutor/learning-status` accepts `student_id`, `learning_cycle_id` and
`concept_id=linear_equations` as query parameters. It returns `quiz_complete`,
`game_complete` and `ready`. It only reads results.

`POST /api/v1/tutor/adaptive-lesson/from-results` accepts:

```json
{
  "student_id": "STU_001",
  "learning_cycle_id": "00000000-0000-4000-8000-000000000001",
  "concept_id": "linear_equations"
}
```

The backend chooses the latest completed pre-tutor Quiz and Game for exactly
that student, concept and cycle, derives prior mastery, runs the trained pipeline
and saves only the Tutor prediction. Repeated requests reuse the same
pair/profile/model-version prediction. The adaptive lesson includes
`plan.primary_strategy`, `model_version`, `confidence`, `prediction_id`, and
`prior_mastery_source=pre_tutor_quiz`. Extra fields, including manually supplied
strategy or prior mastery, are rejected. Missing evidence returns 404.

There is no silent fallback to a manual or rule-based lesson after an error.
The frontend cancels obsolete requests when the learner/cycle changes. Returning
focus to an existing lesson does not reset practice evidence. The retained
preview endpoints are available for developer checks, but the student workspace
does not call them. Existing lesson-content heuristics, avatar review controls
and practice evidence export remain separate from model strategy prediction.

No schema migrations or shared-database seed writes are needed for this change.
The browser code is a local learner selector, not an authenticated account system.

## Verification

The isolated backend runs passed **420 tests**, with 3 optional PostgreSQL tests
skipped. Frontend unit tests passed **16 tests**. The production build passed;
lint completed with 6 React warnings and the build retained its bundle-size
warning. The real-backend Tutor browser check and the Quiz browser flow passed.
The broader Game browser smoke passed its desktop Drag & Drop/Hangman sessions
and phone touch checks, but timed out waiting for the Game to switch out of its
compact layout after a landscape resize. That separate viewport check remains
unresolved; the full Game browser suite is not reported as passed.

- Backend tests cover saved prior mastery, model/persistence agreement,
  idempotency, missing results, wrong students/cycles, post-tutor/unlinked results,
  and rejection of student strategy/score overrides.
- Frontend tests cover Quiz-first/Game-first cycle sharing, reload persistence,
  learner switching, fresh Quiz cycles, stale responses and unavailable storage.
- The Quiz browser test verifies the assigned student and shared cycle are sent
  with session creation.
- The Tutor browser test uses the real backend, supplied model and a new
  disposable SQLite fixture, including recommendation display, saved prediction,
  missing-assessment/error states and responsive layouts.

Run backend tests using the isolated commands in [model integration](TUTOR_STRATEGY_MODEL.md).
From `frontend`, run `npm test`, `npm run build` and `npm run lint`. On macOS with
Chrome installed, `node tests/tutor.e2e.mjs --ui-only` runs the Tutor browser check;
the script never seeds the shared database. `scripts.seed_tutor_ui_check` refuses
existing databases and requires a new SQLite file.
