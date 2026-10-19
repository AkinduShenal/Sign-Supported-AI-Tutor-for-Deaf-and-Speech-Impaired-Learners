# Milestone 5 — Gate Runner (third Game mode)

Status: **design spec, not yet built** (drafted 17 October 2026). Owner: Game component (RehanOP007).

## 1. Summary

A stickman runs along a track toward three gates. The current equation step is shown at the top of the screen; each gate is labelled with one inverse operation (for example `−3`, `+3`, `÷3`). Running through the correct gate earns a power-gear upgrade; running through a wrong gate costs a downgrade. The learner wins by finishing all six tasks before the runner runs out of energy. If the runner does run out, the run ends visually and the remaining questions continue as a practice lap, so the assessment is always completed.

It plays the same six assessment variants as Drag & Drop and Hangman (2 Easy, 2 Medium, 2 Hard, from `data/equationVariants.ts`), through the same `GameSession`, tracker and backend sync.

## 2. Agreed design decisions

| # | Decision | Reason |
|---|---|---|
| 1 | **Three gates**: the correct operation plus two wrong ones taken from the step's existing choices. | Two gates allow 50% success by guessing, which weakens the assessment evidence. |
| 2 | **Power gear and energy**, not body shape. | Linking wrong answers to a "thin and weak" body sends a body-image message to adolescent learners. |
| 3 | **Running out of energy ends the run visually; the remaining questions continue** as a practice lap. | Every session must still complete all six tasks so the backend can calculate a result. |
| 4 | **No time pressure.** The runner jogs on the spot in front of the gates until the learner chooses. | Slower response must not be treated as lower ability (project research rule). |
| 5 | **One gate set per equation step** (step 1 `−3`, step 2 `÷2`). | This teaches the method and matches Drag & Drop's per-step evidence. |

## 3. Gates (choice selection)

Each step in `equationVariants.ts` has four choices: the correct inverse operation and three wrong ones. Gate Runner shows three of them:

1. the correct operation;
2. **always** the operation that was *not* inverted (for `−3` that is `+3`; for `÷3` it is `×3`). This is the "did not use the inverse" misconception, the most diagnostic wrong answer. Every step in the current bank includes this choice (checked 17 October 2026);
3. one of the two remaining operations, chosen with the existing seeded `orderedChoices()` (stable within a session and across a resize, varied between sessions).

Gate positions (left, centre, right) are shuffled with the same seed, so the correct gate is not always in the same place.

Each wrong gate records a `distractor_kind` of either `not_inverted` or `other_operation`.

## 4. Gameplay flow (per step)

1. The equation for this step appears in the top HUD panel and stays visible throughout.
2. The runner runs toward the three gates, then slows and **jogs on the spot** in front of them. Nothing moves closer while the learner thinks; there is no timer.
3. The learner taps a gate (the whole gate is the target, at least 44 CSS px). Keyboard: Left, Down/Space and Right choose the left, centre and right gate; Enter confirms.
4. **Correct gate:** the runner runs through it and the gate bursts into sparkles. Upgrade +1 (section 5). The step text and result appear, as in Drag & Drop (`stepText` and then `resultText`). Then the next step or the next task.
5. **Wrong gate:** the runner runs into it and gets a soft "zap" (a puff of stars). Downgrade −1 (section 5). The runner jogs back. That gate turns grey with a ✕ and is locked, and the learner chooses again from the two remaining gates. A step therefore always ends on the correct operation (two wrong attempts at most), which keeps per-step evidence identical in shape to Drag & Drop.
6. **Hint:** available at every gate set. It shows the step's existing hint text and is recorded as `HINT_REQUESTED`. Hints never change the gear level.

Between tasks the runner sprints along the track (scenery scrolls) while a level banner shows ("Level 3 · Medium"). The running happens between questions, never as a countdown.

## 5. Power gear and energy levels

A single integer **power level** from −3 to +4. It starts at 0.

| Level | Look | Pace |
|---|---|---|
| +4 | helmet, speed shoes, cape and a glowing aura | sprint |
| +3 | helmet, speed shoes and cape | sprint |
| +2 | helmet and speed shoes | run |
| +1 | speed shoes | run |
| 0 | plain runner (the starting look) | run |
| −1 | plain runner, tired face, energy bar about two-thirds | jog |
| −2 | plain runner, sweat drops, energy bar about one-third | slow jog |
| −3 | **out of energy**: the runner sits down on a bench by the track, breathing hard (cartoon) | run over |

* Correct gate: +1 (no change above +4; a burst of stars at the cap).
* Wrong gate: −1. While the level is above 0, the top gear piece pops off and bounces away. At or below 0, the energy bar drains.
* An **energy bar** on the HUD always shows the level as a shape and a number, never colour alone.
* Gear is visual feedback only. It never affects scoring, stars or the backend evidence (section 8).
* No injury, no collapsing, no distress. "Out of energy" is a sit-down rest, consistent with the Hangman milestone's rule against injury or dramatic death animations.

## 6. Winning, the end of the run, and the practice lap

* **Win:** all six tasks are completed and the level never reached −3. The summary shows "Run complete!" with the runner's final gear on a podium.
* **Run over:** the level reaches −3. The runner sits on the bench and an "Out of energy" banner shows. After a short pause, the remaining questions continue as a **practice lap**: the runner jogs in a plain training outfit with a "Practice lap" badge, and gear and energy changes stop. Every answer is still recorded exactly as before.
* The summary always shows the stars per task, plus either "Run complete!" or "Ran out of energy on question N, finished the practice lap".

## 7. Stars

The same as Drag & Drop: `starsForTask(wrongAttempts)` from `stars.ts`, per task across its steps. Hints and time never reduce stars.

## 8. Evidence and backend

* `GameType`: `'gate_runner'`. It replaces the "Mystery Reveal" placeholder card in `gameModes.ts`, which was "coming next" and has no scene (see open question 1).
* Events: the same vocabulary and payload fields as Drag & Drop (`answer_type: 'equation_operation'`, `step_index`, `step_count`, `question_prompt`, `expected_response`, `selected_choice`, `attempt_number`, `hints_before_attempt`), plus:
  * `choices_offered`: the three gate labels in left-to-right order;
  * `gate_position`: `left`, `centre` or `right`;
  * `distractor_kind` on a wrong answer;
  * `power_level_before` and `power_level_after`, and `run_state` (`running` or `practice_lap`). These are presentation context, recorded for transparency and not used to score.
* Task attempts: one `saveTaskAttempt` per variant on its final step, with the whole variant's counts (exactly like Drag & Drop). `is_successful` is always true, because every step ends on the correct operation.
* Backend changes (Game-owned files only):
  * `service.py`: add `"gate_runner"` to the audited `game_type` whitelist in the completeness check.
  * `ml/collection_research.py`: add `"gate_runner"` to the `game_type` Literal and treat its steps like `drag_drop`.
  * Tests for both changes.
* **No database migration**: `game_type` is stored in event payloads, not in a column.

## 9. Visual design

* A pseudo-3D track seen from behind the runner, in the same flat-vector style as the other modes (Phaser Graphics, no image assets). The road narrows toward the horizon, stripes scroll while running, and gates scale up as they approach.
* The top HUD panel holds the current equation (large, semi-bold), the step indicator ("Step 1 of 2"), the progress stepper and the energy bar.
* Gates are tall arches with a large operation label on a white plate, in the operation colours already used by Drag & Drop's operation cards (`operationFill`).
* The bundled game fonts and title style from the typography pass, and the shared effects in `theme/gameEffects.ts`.
* Wide layout: the track fills the stage under the HUD. Compact (phone): the same, with a taller track and gates spaced for touch.
* **Reduced motion:** no scrolling track, no sprint and no bouncing gear. The runner switches poses instantly and the gates are static; all outcomes are still shown as text and badges.

## 10. Accessibility and research rules

* Text and equations stay visible at all times; effects never cover the equation.
* No audio. All feedback is visual, using shape and text as well as colour.
* No timers and no time-based scoring; the runner waits indefinitely at the gates.
* Bilingual labels (Sinhala and English) through `gameText.ts`. New Sinhala strings are drafts until reviewed, like the rest of the file.
* The gear and energy mechanic is described as game feedback, never as a measure of ability or mastery.

## 11. Testing

* Unit tests (`node --test`): gate selection (always includes the correct gate and the not-inverted distractor; stable for a seed), the power-level rules (cap, floor, the run-over transition, the practice lap freezing the level), and star calculation.
* Browser regression (extend `tests/gameUi.e2e.mjs`): launch from the hub, a wrong gate (level −1, gate locked, retry), a correct gate (level +1), multi-step tasks, a forced run-over (three net wrong) followed by a practice lap that still records every answer, reduced motion, 390 px and 320 px touch, and 44 px targets.
* Backend: a `gate_runner` session passes the completeness check, and the research export handles it.

## 12. Open questions (decide before building)

1. **Replace Mystery Reveal?** This spec puts Gate Runner in the third card's slot and removes the "Mystery Reveal, coming next" placeholder. Should Mystery Reveal stay as a fourth, "coming next" card instead?
2. **The name "practice lap."** Calling the remaining questions a "practice lap" may suggest they don't count, so learners could try less hard, which would weaken the evidence from those tasks. Something like "Recovery lap" or "Finish lap" avoids that. Please confirm the wording.
3. **Mode name.** "Gate Runner" in English; the Sinhala name needs your team's usual language review.
4. **Run-over threshold.** −3 means three more wrong gates than correct ones from the start. A session has 9 to 11 gate sets (Easy tasks have one step; Medium tasks two or three; Hard tasks one or two). Should it be harder or more forgiving?
