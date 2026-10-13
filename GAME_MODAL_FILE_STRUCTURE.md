# Game component — current continuation guide

Updated **2026-10-12** against the current working tree. Owner: RehanOP007.
For whole-project status see [STATUS_CHECKLIST.md](STATUS_CHECKLIST.md); for the
database evidence and migration gaps see [DATABASE_CHECKLIST.md](DATABASE_CHECKLIST.md).

## What works now

The Game tab opens a Phaser selection hub with three interaction modes:
**Drag & Drop** and **Hangman** are both playable; **Mystery Reveal** remains an
unavailable "Coming next" entry. All three are intended to share the assessment
content and analytics architecture. Their presence in the registry does not by
itself implement them — see each mode's own scene for what actually exists.

Both playable modes present the same six-task pre-tutor assessment: 2 Easy,
2 Medium, 2 Hard, selected from 18 local equation variants. Questions shuffle
within each tier. The selector normally excludes variants used at least twice;
when too few are eligible, it samples a small least-used pool. This fallback
may exceed the usual two-use threshold and is not a strict global usage cap.

**Drag & Drop** has the learner choose the correct inverse operation at each
step of balancing the equation (drag or tap a card).

**Hangman** instead asks for only the equation's final numeric value, typed on
an on-screen keypad. The figure hangs from a bar by both hands (5 fingers each,
drawn as a filled cartoon person, not a stick figure); each wrong submission
slips one finger, alternating hands, and the grip visibly sags. At
`MAX_WRONG_SUBMISSIONS` (10, see `phaser/hangmanLogic.ts`) both hands release
and a Phaser tween animates a safe fall to a seated landing — no impact effects.
A correct answer never moves the grip (per design), it only swaps in a happy
face and a brief confetti burst. The figure's face also swaps between a mild
"strained" look while hanging, surprised mid-fall and gently sad once settled
after a fall — four expressions total, picked by state in
`phaser/HangmanFigure.ts`, not blended. The session summary shows a
"🎉 You didn't let him fall!" banner once, only when zero of the six questions
ended in a fall that session. A "☰ Menu" button on the gameplay screen returns
to Game Selection at any point, including mid-question.

One backend session contains raw events, task summaries and an optional result.
The summary displays backend-calculated analytics when available, with local
tallies as a network/error fallback. Stars depend on wrong attempts only, not
hints or speed — Drag & Drop and Hangman each have their own thresholds
(`stars.ts`'s `starsForTask()` vs. `hangmanLogic.ts`'s `starsForHangman()`,
the latter rescaled for the 10-wrong ceiling: 0→3, 1-3→2, 4-9→1, 10→0; these
bands are a judgment call, not confirmed against a specific rubric). Labels/
hints include draft Sinhala; review is still needed.

## Active architecture

```text
App.tsx → PhaserGame.tsx → GameConfig.ts
                           → GameSelectionScene
                           → EquationGameScene (Drag & Drop)
                               → GameSession (shared assessment state)
                                   → GameSessionTracker (local tallies)
                                   → GameBackendSync → gameApi → gameRequest
                                       → /api/v1/game → service → ORM → Supabase
                           → HangmanGameScene (Hangman)
                               → GameSession (same class, same tracker/backend sync)
                               → HangmanFigure (bar/grip/fall drawing)
                               → hangmanLogic.ts (answer buffer, submit outcome, stars)
```

Both playable scenes construct their own `GameSession` and never share one
instance — starting either mode from Game Selection always begins a fresh
session, tracker and figure state. `GameSession` survives scene restarts/
resizes through scene data; a new game gets new session state. This is not
refresh persistence or cross-device resume. Quiz also reuses `game/identity.ts`
for the browser's pseudonymous student ID; a shared authentication or
coordinated learning-cycle handoff is not implemented.

## File map

Paths below are relative to `frontend/src/game/` unless stated otherwise.

| File | Responsibility |
| --- | --- |
| `phaser/PhaserGame.tsx` | React mounting and teardown of Phaser. |
| `phaser/GameConfig.ts` | Registers the hub first, then both playable scenes (`EquationGameScene`, `HangmanGameScene`). |
| `phaser/scenes/GameSelectionScene.ts` | Bilingual mode cards; only available modes can start. |
| `phaser/scenes/EquationGameScene.ts` | Drag & Drop: rendering, input, task progression, event evidence, rewards and summary. |
| `phaser/scenes/HangmanGameScene.ts` | Hangman: keypad input, submit/hint flow, drives the figure and the fall tween, event evidence, rewards and summary (including the "didn't let him fall" banner). |
| `phaser/HangmanFigure.ts` | Draws the bar/hands/illustrated person purely from Phaser Graphics (filled capsules/circles/rounded rects, no images); exposes `setGrip()`, `celebrate()`, `setFallProgress()`. No game logic — the scene decides what state to show. |
| `phaser/hangmanLogic.ts` | Phaser-free: answer buffer handling, `submitAnswer()`'s correct/wrong/failed outcome, `MAX_WRONG_SUBMISSIONS` (10), `starsForHangman()`. Unit-tested directly. |
| `gameModes.ts`, `types.ts` | Mode registry and `GameType`: `drag_drop/hangman/mystery_reveal`. Mode is separate from concept/activity/variant/difficulty. |
| `session/GameSession.ts` | Shared mode, identity/cycle, selected tasks, tracker, backend sync, task index and stars. Current concept defaults to `linear_equations`. |
| `phaser/viewport.ts` | Shared camera/design-space layout helpers. |
| `phaser/BalanceScale.ts`, `equationSides.ts` | Visual balance and equation-side helpers. |
| `phaser/stars.ts`, `gameText.ts` | `stars.ts`: Drag & Drop's reward rule and `formatStars()`/`MAX_STARS_PER_TASK` (shared for display by both modes). `gameText.ts`: draft bilingual labels/hint templates for both modes, the session-summary banner text and the menu button label. |
| `data/equationVariants.ts` | Existing 18 typed local variants, with final answers. This is not the future database Activity/Variant Bank. |
| `data/variantAccess.ts` | Shared variant accessors for future modes. |
| `data/variantSelection.ts` | Tier selection, shuffling, usage filtering and fallback. |
| `analytics/GameSessionTracker.ts` | In-memory step/task tallies; aggregate counts for one completed variant. |
| `api/gameBackendSync.ts` | Tracks pending event/attempt requests, waits before completion, and fetches results. |
| `api/gameApi.ts`, `game.ts` | Typed Game endpoints and HTTP wrapper. |
| `identity.ts` | Pseudonymous localStorage student ID, not login. |

Legacy reference files remain: `GameActivity.tsx`, `GameSummary.tsx`,
`activities/`, `useGameEvents.ts`, `i18n/`, and the original
`data/equationLevels.ts` level array. Some shared types remain imported; do not
delete these directories on the assumption that every file is unused.

Backend: `backend/app/modules/game/models.py` defines `GameSession`,
`GameplayEvent`, `GameTaskAttempt` and `GameResult`; `schemas.py` validates
contracts, `router.py` handles HTTP, and `service.py` owns persistence/analytics.

## API and persistence

All paths below start with `/api/v1/game`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/sessions` | Create one assessment session. |
| POST | `/events` | Save raw event and JSON evidence. |
| POST | `/task-attempts` | Save task-level totals and variant metadata. |
| POST | `/sessions/{id}/complete` | Mark the session completed and conditionally create its result. |
| GET | `/variant-usage` | Count saved variant attempts for student/concept. |
| GET | `/results/{id}` | Read the result, or 404 if absent. |

Current scene behavior saves one aggregate attempt per finished variant. Events
include variant/step/equation/choice evidence; `game_type` is stored inside event
payloads, not dedicated session/result columns. Historical rows can predate the
richer payload or task aggregation.

Hangman reuses every endpoint, event type and attempt field above unchanged —
no schema change, no migration, no new `event_type` enum value. It maps onto
the existing vocabulary as: `QUESTION_SHOWN` per question, `ANSWER_SUBMITTED`/
`ANSWER_CORRECT`/`ANSWER_INCORRECT` per keypad submission (never for typing or
backspace, which are not attempts), `HINT_REQUESTED`, `TASK_COMPLETED` with an
`outcome: 'solved' | 'failed'` field in its event payload (the enum has no
dedicated "failed" value), then `GAME_COMPLETED`/`SESSION_ENDED` as usual.
Hangman never emits `RETRY_STARTED` — that event is specific to Drag & Drop's
per-step retry concept, which Hangman's single-submission-per-attempt model
has no equivalent of. One `game_task_attempts` row is saved per question,
same as Drag & Drop: `wrong_attempts` is the finger-slip count at resolution,
`is_successful`/`score` distinguish solved from failed after the 10th wrong.

Completion waits for in-flight requests but logs/swallows network errors.
It provides no durable queue or guaranteed retry/replay. The backend marks
session status completed when completion is requested; the distinct-task
2 Easy + 2 Medium + 2 Hard check separately gates result creation. An early-ended
session can therefore be marked completed and still have no result.

## Backend analytics

Everything below is game-mode-agnostic by construction — `calculate_session_features()`
and `is_assessment_complete()` only read `difficulty_level`/`task_id`/the generic
attempt fields, never `game_type`, so Hangman required zero backend changes here.

`calculate_session_features()` derives:

- `tasks_total = 6`; attempted/completed/successful counts from attempt rows.
- Success rate = successful / attempted; completion rate = completed / 6.
- Average attempts = summed attempts / attempted tasks.
- Hint rate = number of tasks using any hint / 6; `total_hint_count` retains the
  raw count. This definition must not change silently.
- Active time = rounded sum of task times; wrong/hint/skipped totals from attempts.
- Retry count = number of persisted `RETRY_STARTED` events.

Divisions guard zero denominators; rates are clamped to the allowed range.
Completion counts distinct task IDs by tier, whereas feature aggregation reads
attempt rows. Duplicate attempt ingestion remains a robustness concern.

`create_game_result()` returns an existing result for the session instead of
recalculating it. Prototype labels use `game-heuristic-v1`, not trained ML.
Game owns its result writes. Tutor's current missing-result insertion fallback
is a separate ownership defect; it must not be described as intended architecture.

## Migration and curriculum state

0004 describes Game tracking tables/result extensions; 0005 adds nullable
activity/variant/difficulty metadata to attempts. The current repository head and
last verified Supabase revision are **0007** (2026-10-12). Revision 0006 adds
shared curriculum; 0007 adds only the Game activity/variant bank.

Do not infer exact live equivalence from the older stamped-revision notes.
0004 uses `game_results_game_session_id_fkey`; earlier live evidence used
`fk_game_results_game_session`. It also creates tables unconditionally and can
fail on historical orphaned results. Applied files must be preserved; consult
[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) before any new reconciliation work.

Milestone 4 Batch 1 and Batch 2 are complete. The Equations knowledge base now
has 10 canonical concepts and 11 source-traceable draft content rows. Game still
uses its existing `linear_equations` contract and local variants; it does not
load questions from the curriculum tables. See the
[curriculum seed report](backend/scripts/EQUATIONS_CURRICULUM.md).

## Verification and remaining work

- Fresh checks for this documentation refresh: **39 frontend tests passed**
  (12 of them `hangmanLogic.test.ts`, Phaser-free); production build passed
  (large-bundle warning); lint passed with **5 existing React warnings** in
  Tutor/avatar components, none in Game files.
- A test run during this same refresh briefly **failed** (`gameHub.test.ts`'s
  "every mode has bilingual card text"): `GAME_TYPE_TEXT.drag_drop.name.si` and
  `.hangman.name.si` had been left as empty strings mid-edit in `gameText.ts`.
  Fixed by restoring just those two values; an unrelated deliberate edit to
  `hangman`'s description (updated to "Don't let the man fall" to match the
  current design) was left as-is. Worth knowing: editing this file live while
  a dev server watches it can produce a stretch of genuinely broken/flickering
  UI mid-edit, not just stale HMR — re-run `npm run test` after hand-editing
  bilingual text here before assuming a UI glitch is something else.
- Hangman is implemented and browser-verified (see below) — no longer pending.
- Same-day Batch 2 evidence: **201 backend cases passed across isolated runs**,
  including disposable PostgreSQL tests. Do not run against configured Supabase.
- The latest hub/session/UI work remains uncommitted. A browser walkthrough of
  the latest six-task UI, responsive/reduced-motion behavior and network failures
  is not established by unit/build checks alone — see the Hangman section below
  for what has actually been walked through in a browser. Live stored rows
  alone do not prove it either.
- Mystery Reveal, durable learner resume, coordinated Tutor handoff, evaluated
  ML, teacher/Sinhala review and post-tutor reassessment remain pending.
- Hangman's star thresholds (0→3, 1-3→2, 4-9→1, 10→0 — see `hangmanLogic.ts`)
  are a judgment call, not confirmed against any specific rubric from the
  component owner. Easy to revise if that changes.
- Milestone 4 Batch 3 is complete: `game_activity_bank` has 8 draft activities
  and `game_activity_variants` has 18 draft LEQ_BANK variants, 6 per tier.
  Repeat seeding inserted zero; Phaser integration remains Batch 4. See the
  [bank report](backend/scripts/EQUATIONS_GAME_ACTIVITIES.md). **This "Batch 4"
  is unrelated to the Hangman game mode below** — it means loading Drag & Drop/
  Hangman's 18 variants from these database tables instead of the hardcoded
  `data/equationVariants.ts`, which has not happened; both modes still read the
  local file. The name collision is between two different pieces of work that
  both got called "Milestone 4" — see the next section for the Hangman one,
  tracked separately in `frontend/src/game/Milestone_4-hanging_man.md`.

The original [Milestone 3 plan](frontend/src/game/Milestone_3.md) is retained as
an acceptance checklist, not an up-to-date status report. Review the implemented
flow against its remaining live/browser checks before declaring every step done.

## Hangman (grip-and-fall design)

Scoped to `frontend/`, no backend changes. Tracked in
[Milestone_4-hanging_man.md](frontend/src/game/Milestone_4-hanging_man.md),
whose original gallows-and-6-wrong brief was superseded during implementation
by the bar-and-hands design described in "What works now" above, following
direct design review (mockups iterated live against feedback before the real
Phaser build, rather than the brief's exact wording).

Scene flow: `GameSelectionScene` → `scene.start('HangmanGameScene', { gameType: 'hangman' })`
with no session (a fresh `GameSession` is created, same as Drag & Drop) →
`loadAssessmentVariants()` picks the same 2+2+2 tasks via the same "max two
uses" logic → `displayCurrentQuestion()` shows the equation, resets
`HangmanFigure.setGrip(0)` → each keypad digit/backspace only touches a local
buffer, never an attempt → Submit calls `hangmanLogic.ts`'s `submitAnswer()`:
correct calls `HangmanFigure.celebrate()` (grip unchanged, happy face,
confetti) and proceeds; wrong-but-not-failed calls `setGrip(wrongCount)` and
stays on the question; wrong-and-failed (10th) runs a Phaser
`tweens.addCounter` from 0 to 1 driving `HangmanFigure.setFallProgress()` each
frame, and only reveals "Question Failed"/the correct answer once that
tween's `onComplete` fires. After question 6 resolves, `finishSession()`
awaits `session.finish()` (same backend completion path as Drag & Drop) and
restarts into the summary screen, which fetches the backend's calculated
result (or falls back to the local tracker) and conditionally shows the
"didn't let him fall" banner.

Browser-verified (Playwright against a live dev server, backend deliberately
pointed at an unreachable port per this repo's own run-skill guidance, so no
rows were written to shared Supabase during testing):
- A run with one question failed: finger-slip progression, the fall tween,
  the sad settled face, a later correct answer's happy face + confetti with
  the grip preserved from an earlier wrong attempt, and the summary correctly
  **omitting** the banner (`Questions Failed: 1`).
- A perfect run (0 wrong anywhere): the summary correctly **showing** the
  banner, `18 / 18` stars, `Questions Failed: 0`.
- Drag & Drop re-checked clean after each Hangman run (no cross-scene
  regression).
- One real bug was caught and fixed during this verification: `HangmanFigure`'s
  vertical anchor didn't match the scene's existing `figureBaseY` "ground
  reference" convention (every other layout constant in `HangmanGameScene.ts`
  treats it as a floor, not a top-left corner), which briefly pushed most of
  the fallen figure off-screen. Fixed inside `HangmanFigure.ts` only — no
  scene changes needed.
- Not verified live against shared Supabase (same caution Drag & Drop's own
  live verification used in Milestone 3) and not checked against a live
  backend's `GameResultResponse` path specifically — the fallback (local
  tracker) path is what the browser runs above actually exercised, since the
  backend was deliberately unreachable. The result-fetch plumbing itself is
  unchanged from, and was already verified live for, Drag & Drop.

## Local checks

From `frontend/`: `npm run test`, `npm run build`, `npm run lint`.
On PowerShell with script execution disabled, use `npm.cmd` for these commands.

From `backend/`, force local database configuration and isolate Tutor tests
until the existing shared-override fixture issue is fixed:

```powershell
$env:DATABASE_URL = 'sqlite+pysqlite:///:memory:'
python -m pytest -q -p no:cacheprovider --ignore=tests/test_tutor_strategy.py
python -m pytest -q -p no:cacheprovider tests/test_tutor_strategy.py
python -m ruff check .
```

Disposable PostgreSQL test URLs and the initial failed combined-run incident
are documented in the curriculum seed report. No migrations, database writes,
commits or pushes are performed by this documentation refresh.

## Game content files — Batch 3

`backend/app/modules/game/content_models.py` defines GameActivity and
GameActivityVariant separately from learner evidence. The static manifest is
`backend/scripts/equations_game_activities.json`; use
`python -m scripts.seed_equations_game_activities` from backend/ to validate it
without a DB connection. `--apply` requires revision 0007 and Batch 2 curriculum
prerequisites. IDs are immutable: materially changed mathematics needs a new ID.
No retrieval API, old-attempt FK or Phaser selection change was added.
