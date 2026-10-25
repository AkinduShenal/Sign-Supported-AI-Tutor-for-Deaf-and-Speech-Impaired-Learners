# Milestone 3.1 — Game ML proficiency presentation

The later supervised PP1 verification controller is documented in [Milestone 3.2B](../../../backend/app/modules/game/research_inference/PP1_BROWSER_VERIFICATION.md). Normal inference defaults remain disabled; the results below record the original presentation milestone.

**PASS: frontend presentation and isolated verification. Live prediction requests remain disconnected.**

Completed Drag & Drop and Hangman results now include an `ML Model Estimate` card beneath the existing Phaser summary and above the unchanged ML Input Details panel. The normal integration supplies no prediction, so it always displays `Prediction unavailable` with no level or probability bars. Existing scoring, progression, analytics, event recording, sign support and ML input copying retain their behavior. Neither backend authorization/configuration nor the frozen model/data was changed.

## Files created

- `frontend/src/game/MLProficiencyCard.tsx`: reusable presentation with ready, loading, unavailable and error states; invalid/incomplete responses also remain unavailable.
- `frontend/src/game/MLProficiencyCard.css`: scoped Diagnostic Quiz palette, white rounded panel, purple accents and native progress-bar styling; two columns on desktop, stacked below 620 px, readable at 320 px and enlarged text.
- `frontend/src/game/config/gameMLConfig.ts`: `gameMLConfig.SHOW_EXPERIMENTAL_LABEL=true`.
- `frontend/src/game/mlPrediction.ts`: typed protected API response, class ordering, response validation and probability formatting.
- `frontend/tests/gameMLPrediction.test.ts`: formatting, response/provenance validation, missing/invalid inputs and default configuration checks.
- `frontend/tests/fixtures/gameMLPrediction.fixture.ts`: invented examples for isolated tests only, explicitly named and marked as mock data.
- `frontend/tests/fixtures/gameMLVisualHarness.tsx`: clearly labelled visual-test entry; not a normal application route or production entry.
- `frontend/tests/gameMLCard.e2e.mjs`: isolated Chrome/CDP browser tests with screenshots, blocked APIs and accessibility checks.
- This report.

## Files modified

- `frontend/src/game/phaser/PhaserGame.tsx`: imports/renders the unavailable card in the existing results lifecycle. Existing scene completion notifications and cleanup are reused; neither scene was edited.
- `frontend/tests/gameUi.e2e.mjs`: asserts the normal card is unavailable, checks no prediction request occurs, captures its responsive screenshots, and corrects a stale rotation assertion. Existing scenes intentionally retain their creation-time design during rotation; the test now verifies actual canvas resizing and preserved layout/question state.

Pre-existing uncommitted work in these files was retained. No package, lockfile, frontend environment, root environment, backend or database changes were needed.

## Component and configuration

`<MLProficiencyCard />` safely defaults to unavailable. A future trusted controller can supply a `GameMLPredictionState`: `loading`, `unavailable`, `error`, or `ready` with a complete `GameMLPrediction`. The response type matches the documented backend fields, including original provenance, runtime, checksum, feature contract and `teacher_verified=false`. Response validation checks class names, numeric probabilities, normalization and expected provenance. It rejects bad evidence rather than clamping, normalizing or fabricating values. Authentication and session binding remain server responsibilities; this frontend validation is not an authorization mechanism.

All three probabilities use fixed Beginner / Intermediate / Advanced ordering. Percentages display up to one decimal place. Native progress values retain the full numeric precision, labelled with both their class and percentage for assistive technology. The card uses semantic headings, a named section/group, status announcements, a generic error alert, and visible text alongside visual bars. No audio or animation is required. No controls were added to the existing Game/sign workflow.

Changing `SHOW_EXPERIMENTAL_LABEL` to false hides only `Experimental Prediction — Not Teacher Verified`. The `ML Model Estimate` heading, state, proficiency, bars and uncertainty explanation remain. The reusable component also accepts `showExperimentalLabel` for isolated testing.

The card has no fetch function, credential parameter, session lookup, local-storage prediction cache or example-data fallback. No researcher bearer is placed in frontend source, environment variables or requests. The verified historical learner prediction is not embedded or loaded. Test fixtures are imported only from `frontend/tests`; the normal production entry does not import them.

## Verification results

| Check | Result |
| --- | --- |
| `npm.cmd test` | 39 passed, including 16 new ML tests; no failures/skips |
| `npm.cmd run build` | TypeScript and production build passed; Vite reported the existing large application chunk warning |
| Targeted `oxlint` | Exit 0 for all new TS/TSX/browser tests and both modified frontend files |
| `node --experimental-strip-types tests/gameMLCard.e2e.mjs` | 48 passed cases: three levels, loading, unavailable, error, invalid response and default state; both label settings at 1440 / 390 / 320 px |
| Accessibility/formatting | Native progress bars present in Chrome's accessibility tree with class labels; expected numeric/percentage values; 200% text at 320 px without horizontal overflow |
| Existing Game results checks | Both completed modes passed scoring/progression/results, exact ML clipboard JSON, missing/error evidence, unavailable card and 390/320 px results layouts using mocked APIs |
| Phone regression rerun | `GAME_UI_PHONE_ONLY=1` with `node tests/gameUi.e2e.mjs` passed 390/320 px touch, 44 px targets, scroll/drag behavior, real canvas rotation/state preservation, reduced motion and offline usage fallback |
| Live prediction requests | Zero in the isolated card browser test and normal mocked Game flow |
| Production JavaScript inspection | No mock fixture/harness marker, verified learner session ID or ML researcher-token setting bundled |
| Preservation check | All 24 previously protected backend/model/data/configuration files matched prior hashes; the intended `PhaserGame.tsx` edit was excluded |

The first broad Game browser run passed both desktop completed-game/results flows, then encountered the stale landscape assertion described above. After correcting only the test, the phone-only rerun passed the remaining touch/rotation/reduced-motion checks. These are separate runs, not a claim that one uninterrupted full run passed. Existing Game APIs were mocked throughout; no shared database or protected inference endpoint was contacted. The new presentation test blocked API requests altogether. No live ML inference was performed for this milestone.

Commands above run from `frontend/`; use `npm` in shells that do not need Windows's `.cmd` executable. Browser tests use the existing Chrome installation and no added dependencies. Generated screenshots are ignored under `frontend/artifacts/`.

## Screenshots and visual review

Manually inspected the desktop ready-state mock, mobile ready-state mock, 200% text screenshot and normal unavailable card. Ready-state images clearly include `Visual test only — mock data, not a student prediction.` The normal Game card displays no mock level.

- [Desktop ready-state mock](../../artifacts/game-ml-card-1792646695601/mock-Advanced-1440.png)
- [320 px ready-state mock](../../artifacts/game-ml-card-1792646695601/mock-Intermediate-320.png)
- [320 px with 200% text](../../artifacts/game-ml-card-1792646695601/mock-Intermediate-320-text-200.png)
- [Normal Hangman unavailable card](../../artifacts/game-ui-1792646708887/ml-card-unavailable-hangman-390.png)
- [Normal Drag & Drop unavailable card](../../artifacts/game-ui-1792646708887/ml-card-unavailable-drag-drop-390.png)

The associated browser artifacts contain machine-readable check lists and screenshots for all three levels and the loading/unavailable/error states. Automated checks cover Chrome's accessibility tree and text resizing; a manual screen-reader/device review has not been performed.

## Before Milestone 3.2

Implement a separately approved backend-mediated browser authorization flow with session ownership, reviewed scope and non-disclosing failures. The researcher bearer must remain server-side. Preserve the existing manifest, quarantine, strict saved-session checks and disabled-by-default service policy. Bind any future response to the current completed session and clear it on learner/session changes. Address loading, cancellation and the private worker's observed cold-start latency when designing that connection.

The one approved genuine-session reproduction establishes backend technical compatibility for that scope. This UI work adds no evidence of real-world proficiency accuracy, calibration or teacher verification. It does not approve production activation or broader learner/session inference.
