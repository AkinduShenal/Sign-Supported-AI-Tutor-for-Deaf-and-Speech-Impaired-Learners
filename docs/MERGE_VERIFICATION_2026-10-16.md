# Main / Tutor integration verification — 2026-10-16

Integrated `origin/main` at `a360ffe` with `Ai_Tutor_Optimize_V2` at `df00a05`
using a normal merge. Both histories and the original commits are retained.

The conflicts were in App, QuizAssessment, the Quiz API and the Quiz browser test.
Resolution keeps main's Quiz collection gate, queued/idempotent writes, feedback,
level transitions, CSV export and timeouts. Quiz session creation now supplies
the Tutor branch's shared learner/cycle identifiers through that existing queue.
Recovery restores the queued Quiz's original cycle; completed, saved assessments
can close collection and continue to the automatic Tutor. Session acknowledgments
are checked against the requested cycle/concept.

Main's Game language controls and source files were retained. The Tutor branch's
model artifacts, avatar assets, manifests and lesson engine were retained. Outside
the explicit integration adapters and tests, 37 main-side changed files and 62
Tutor-side changed files match their original branch versions byte for byte.

Verification:

- Backend: 424 tests passed across the two isolated runs; 3 optional PostgreSQL
  tests were skipped.
- Frontend: 23 unit tests passed; production build passed; lint completed with
  6 existing React warnings. The build still reports its bundle-size warning.
- Quiz browser: feedback, transitions, response-loss/refresh recovery, shared
  learning cycle, safe collection close, Tutor handoff and timeout checks passed.
- Tutor browser: real bundled-model predictions, saved prediction IDs, layouts,
  missing-assessment/error states and avatar lesson checks passed.
- The stale Quiz seed test was updated to verify the new feedback contract
  against saved evidence. The browser test checks inherited fieldset disabling
  and waits for the new document after reload.
- The broader Game language browser check failed its summary text-spacing
  assertion. Its Game scene/text/layout source remains identical to main; this
  merge does not change that layout. The previously recorded Game landscape
  resize limitation also remains outside these integration changes.

All backend tests use isolated SQLite configuration, with optional PostgreSQL
tests skipped when disposable local databases are not configured. No shared
database migrations or seed writes are part of this merge.
