We are continuing development of the **Accessible Game-Based Learning Module** in the Sign-Supported AI Tutor research project.

The current project already contains:

- React + Vite + TypeScript
- Phaser 4
- Game Selection scene
- shared `GameSession`
- `GameType = 'drag_drop' | 'hangman' | 'mystery_reveal'`
- 18 shared equation variants
- six selected questions per session
- easy/medium/hard selection
- local analytics
- backend synchronization
- Drag & Drop fully working
- shared question/session architecture
- local + backend Game evidence
- ML Milestone 1.1 already completed offline using synthetic engineering verification

IMPORTANT:

The ML work now depends on the Game Module producing **stable, comparable behavioural evidence**.

The new game modes must therefore preserve the existing shared analytics semantics.

Do NOT redesign shared analytics fields casually.

Do NOT rename or change the meaning of:

- `variantId`
- `activityId`
- `concept`
- `difficulty`
- `wrongAttempts`
- `hintCount`
- `attemptsCount`
- completion fields
- timing fields
- learner/session identity
- learning-cycle identity

Add new mode-specific evidence only as backward-compatible extensions.

---

# HIGH-LEVEL GOAL

Implement two additional visual game modes:

1. Hangman
2. Mystery Reveal

Both must use the SAME shared equation bank:

`frontend/src/game/data/equationVariants.ts`

Do NOT create separate question banks.

The three game modes should differ in interaction style while keeping the mathematical content comparable.

Current intended distinction:

## Drag & Drop

Tests:

- operation selection
- equation transformation
- balancing behaviour

## Hangman

Tests:

- independent solving
- final-answer submission
- persistence across incorrect full-answer submissions

## Mystery Reveal

Tests:

- recognition of valid mathematical transformation steps
- solution-sequence understanding

---

# PARALLEL DEVELOPMENT CONSTRAINT

Other developers are working on:

- ML
- AI Tutor
- Curriculum
- Quiz
- shared backend/database components

For this milestone:

- keep changes inside `frontend/src/game` wherever possible
- do not modify Tutor files
- do not modify Quiz files
- do not modify Curriculum files
- do not modify ML implementation
- do not create database migrations
- do not add new shared database columns
- do not redesign global application navigation
- do not change existing Game API/database contracts unless absolutely required
- if a cross-component schema change becomes necessary, STOP that part and report it instead of implementing it

---

# ML COMPATIBILITY REQUIREMENT

The ML pipeline will later compare behaviour using shared features.

Every game mode should continue to produce comparable fields such as:

- learner/session identity
- game type
- question/variant ID
- concept
- difficulty
- attempts count
- wrong attempts
- hint count
- time taken
- completion status
- first-attempt correctness where available

Mode-specific evidence may be added.

Do NOT replace the shared metrics.

For example:

Hangman may add:

- `wrongSubmissions`
- `submittedAnswersCount`
- `hangmanStageReached`
- `failedMaxAttempts`

Mystery Reveal may add:

- `wrongStepChoices`
- `revealStepsCompleted`
- `solutionSequenceErrors`
- `revealCompletionRatio`

These should complement, not replace:

- `wrongAttempts`
- `attemptsCount`
- `hintCount`
- `timeTaken`

---

# FIRST-ATTEMPT CORRECTNESS

This is important for ML.

For every question in every game mode, preserve enough evidence to determine whether the learner answered correctly on the first valid mathematical submission.

Examples:

Hangman:

- first submitted complete answer correct → `firstAttemptCorrect = true`
- first submitted complete answer wrong → `false`

Mystery Reveal:

- first submitted valid next-step choice correct → `true`
- first valid next-step choice wrong → `false`

Do not count accidental clicks, invalid keypad states, dragging without submission, or empty submissions as mathematical attempts.

---

# TIMING SEMANTICS

Preserve existing timing fields.

Do not redefine their meaning per mode.

At minimum:

- question/task start time
- question/task completion time
- total task duration

Mode-specific step timing may be added.

Do not introduce visible countdown pressure unless explicitly requested.

ML needs observed behaviour, not artificially induced speed.

---

# IMPLEMENTATION ORDER

Implement in this order:

1. Hangman
2. verify shared analytics compatibility
3. Mystery Reveal
4. verify all three modes against the same session/question contracts
5. regression-test Drag & Drop

Do not rewrite Drag & Drop.

---

# =========================================================
# PART A — HANGMAN
# =========================================================

Create a Phaser Hangman scene.

Suggested file:

`frontend/src/game/phaser/scenes/HangmanGameScene.ts`

Register it in `GameConfig.ts`.

Set:

`hangman.available = true`

in `gameModes.ts`.

Mystery Reveal can remain unavailable until its implementation is complete.

---

# HANGMAN MATHEMATICAL MECHANIC

Hangman should test the learner's final solution value.

Example:

`3x = 12`

Display:

`Solve for x`

`x = [  ]`

Learner enters:

`4`

through a visual numeric keypad and presses:

`Submit Answer`

Do NOT implement word/letter guessing.

Do NOT guess individual digits independently.

The learner submits the complete value of `x`.

---

# SHARED QUESTION DATA

Use:

`variant.finalAnswer`

from the existing 18 variants.

Do not parse final answers from display strings unless only as a temporary fallback.

Do not create Hangman-specific equations.

The same selected six variants should be provided through the existing shared `GameSession`.

---

# HANGMAN INPUT

Provide a Phaser visual keypad.

Support exactly the answer formats required by the current 18 variants.

Inspect all `finalAnswer` values first.

Possible controls:

- digits
- minus sign
- decimal point only if required
- backspace
- Submit

Do not add mathematical symbols that are not needed.

Mouse and touch must both work.

---

# HANGMAN ATTEMPT SEMANTICS

A mathematical attempt occurs ONLY when the learner presses:

`Submit Answer`

with a valid complete answer.

Do NOT count:

- digit taps
- backspace
- changing the answer buffer
- empty submit
- invalid formatting
- unrelated clicks

as attempts or wrong answers.

On each valid submission:

`attemptsCount += 1`

If incorrect:

`wrongAttempts += 1`

and Hangman-specific:

`wrongSubmissions += 1`

---

# HANGMAN FIRST ATTEMPT

If the first valid submitted answer is correct:

`firstAttemptCorrect = true`

Otherwise:

`firstAttemptCorrect = false`

Do not change it after later successful attempts.

---

# HANGMAN FIGURE

Implement a traditional simple line-drawn Hangman figure using Phaser Graphics.

No external asset required.

Stages:

0. gallows only
1. head
2. torso
3. left arm
4. right arm
5. left leg
6. right leg / figure complete

Do not use gore, injury animation, choking, struggling, or dramatic death animation.

The figure should simply progress visually like a traditional Hangman puzzle.

---

# HANGMAN WRONG ANSWER FLOW

For an incorrect submitted answer:

1. record one mathematical attempt
2. record one wrong attempt
3. increment `wrongSubmissions`
4. advance Hangman one stage
5. show visual `Try Again`
6. clear or allow editing of answer buffer
7. remain on the same question

---

# HANGMAN FAILURE

After 6 incorrect submitted answers:

- set `failedMaxAttempts = true`
- Hangman stage = 6
- reveal correct final answer
- do not mark the learner as having solved the question correctly
- allow Next
- do not trap the learner

IMPORTANT:

Seeing the revealed answer does NOT count as successful completion.

Analytics must distinguish:

`solvedCorrectly`

from:

`failedMaxAttempts`

---

# HANGMAN SHARED COMPLETION SEMANTICS

Do not overload shared `completed` in a misleading way.

If the existing analytics structure supports only `completed`, preserve its technical meaning but add a separate outcome field such as:

`outcome: 'solved' | 'failed_max_attempts'`

or:

- `completedCorrectly`
- `failedMaxAttempts`

Choose the smallest backward-compatible solution.

Do not modify Drag & Drop semantics.

---

# HANGMAN HINTS

Reuse existing variant hints.

Hint usage should:

- increment shared `hintCount`
- not count as an attempt
- not count as a wrong answer
- not advance Hangman
- not auto-solve the question

For multi-step equations, use the most educationally appropriate existing hint without duplicating the question bank.

---

# HANGMAN ML-RELEVANT EVIDENCE

Per question, preserve shared fields:

- variantId
- concept
- difficulty
- attemptsCount
- wrongAttempts
- hintCount
- timeTaken
- firstAttemptCorrect
- completion/outcome

Additional Hangman fields:

- wrongSubmissions
- submittedAnswersCount
- hangmanStageReached
- failedMaxAttempts

Do NOT replace shared `wrongAttempts` with `wrongSubmissions`.

They can contain the same numeric value in Hangman while remaining semantically separate fields.

---

# HANGMAN STARS

Keep stars as presentation/reward evidence only.

Suggested rule:

0 wrong → 3 stars
1–2 wrong → 2 stars
3–5 wrong → 1 star
6 wrong / failed → 0 stars

Do NOT make ML behaviour fields depend on stars.

Stars are an output/reward, not a primary behavioural feature.

---

# HANGMAN SUMMARY

After six questions display:

- Questions Solved
- Questions Failed
- Wrong Answers
- Hints Used
- Total Time
- Stars Earned

Include:

`Choose Another Game`

which returns to Game Selection.

---

# =========================================================
# PART B — MYSTERY REVEAL
# =========================================================

After Hangman is working and verified, implement Mystery Reveal.

Suggested scene:

`frontend/src/game/phaser/scenes/MysteryRevealScene.ts`

Then register it and set:

`mystery_reveal.available = true`

---

# MYSTERY REVEAL MATHEMATICAL MECHANIC

Mystery Reveal should NOT simply ask for the final answer.

It should test whether the learner recognizes the correct sequence of equation transformations.

Example:

Starting equation:

`2x + 3 = 11`

Question:

`Which is the correct next step?`

Options might include:

A. `2x = 8`
B. `2x = 14`
C. `x + 3 = 9`
D. `2x = 11`

Correct:

`2x = 8`

Then proceed to the next transformation:

`2x = 8`

Question:

`Which comes next?`

Correct:

`x = 4`

This mode should test solution-sequence understanding.

---

# SHARED QUESTION DATA

Use the same:

`equationVariants.ts`

and existing `steps`.

Do NOT create:

`mysteryQuestions.ts`

Do NOT duplicate equations.

Inspect whether the current step data contains enough semantic information for Mystery Reveal.

If current data already provides:

- starting equation
- step text
- result text
- choices

reuse it.

If Mystery Reveal needs explicit transition fields, add them only as backward-compatible semantic fields.

Do not redesign the entire variant format.

---

# MYSTERY REVEAL OPTIONS

For each solution step, present several possible next-equation states.

The correct option must represent the mathematically valid next transformation.

Distractors should come from explicit data where possible.

Do not generate misleading malformed equations at runtime unless the logic is deterministic and mathematically valid.

If the shared question bank currently lacks appropriate next-step distractors, report this before inventing a large new content-generation system.

A small backward-compatible addition to variant data is acceptable.

---

# MYSTERY VISUAL REWARD

Correct solution steps progressively reveal a mystery visual.

This may initially be implemented using:

- geometric puzzle tiles
- hidden pattern
- abstract visual
- simple built-in Phaser shapes

Do NOT require production artwork for the first implementation.

The hidden visual is a reward only.

Never hide mathematical information needed to solve the question.

---

# MYSTERY ATTEMPT SEMANTICS

A mathematical attempt occurs only when the learner deliberately selects/submits a candidate next mathematical step.

Do NOT count:

- hover
- accidental empty space clicks
- animations
- opening/closing visual panels

as attempts.

Each submitted step choice:

`attemptsCount += 1`

Incorrect:

`wrongAttempts += 1`

and mode-specific:

`wrongStepChoices += 1`

---

# MYSTERY FIRST-ATTEMPT CORRECTNESS

Track first valid mathematical choice.

If the first choice for the task/step is correct:

`firstAttemptCorrect = true`

Otherwise false.

For multi-step questions, preserve step-level correctness if existing analytics supports it.

Do not collapse all step behaviour into only the final task outcome.

---

# MYSTERY PROGRESSION

Each correct step should:

1. confirm the mathematical transformation
2. reveal part of the mystery
3. advance to the next solution step
4. eventually reveal the complete reward

Incorrect step:

1. record wrong attempt
2. show visual feedback
3. keep learner on current mathematical step
4. do NOT permanently reveal reward progress

---

# MYSTERY HINTS

Reuse shared hints where possible.

Hint:

- increments shared `hintCount`
- does not count as attempt
- does not count as wrong answer
- does not automatically select a correct step

---

# MYSTERY ML-RELEVANT EVIDENCE

Preserve:

- variantId
- concept
- difficulty
- attemptsCount
- wrongAttempts
- hintCount
- timeTaken
- firstAttemptCorrect
- completed

Add:

- wrongStepChoices
- revealStepsCompleted
- solutionSequenceErrors
- revealCompletionRatio

If step-level analytics already exists, use it rather than creating duplicate structures.

---

# =========================================================
# PART C — SHARED ANALYTICS RULES
# =========================================================

All three game modes must remain comparable.

Example shared session/question evidence:

```ts
{
  gameType: 'hangman',
  variantId: 'LEQ_M_001',
  concept: 'two_step_equation',
  difficulty: 'medium',

  attemptsCount: 3,
  wrongAttempts: 2,
  hintCount: 1,
  firstAttemptCorrect: false,
  timeTakenSec: 41,
  completed: true,

  modeEvidence: {
    wrongSubmissions: 2,
    hangmanStageReached: 2,
    failedMaxAttempts: false
  }
}
```

Mystery example:

```ts
{
  gameType: 'mystery_reveal',
  variantId: 'LEQ_M_001',
  concept: 'two_step_equation',
  difficulty: 'medium',

  attemptsCount: 3,
  wrongAttempts: 1,
  hintCount: 0,
  firstAttemptCorrect: false,
  timeTakenSec: 35,
  completed: true,

  modeEvidence: {
    wrongStepChoices: 1,
    revealStepsCompleted: 2,
    solutionSequenceErrors: 1,
    revealCompletionRatio: 1
  }
}
```

Use the project's existing structures rather than forcing these exact shapes if a cleaner backward-compatible implementation already exists.

---

# ML MILESTONE 1.1 PROTECTION

The current ML milestone is still offline/synthetic engineering verification.

Real learner data collection will validate the research pipeline later.

Therefore:

Do NOT:

- add ML inference into Phaser
- add adaptive difficulty based on model predictions
- call an ML API from Hangman or Mystery Reveal
- create model-generated labels from game score
- change game behaviour based on predicted difficulty
- introduce circular labels such as defining "difficulty" directly from the same features the model is supposed to learn from

The Game Module should collect clean evidence.

The ML module should analyze it later.

---

# DATA QUALITY RULES

For research-quality evidence:

- count only meaningful mathematical submissions
- do not inflate attempts with UI actions
- preserve question IDs
- preserve difficulty labels
- preserve concept labels
- preserve gameType
- preserve first-attempt correctness
- preserve timing consistently
- preserve failed-vs-solved distinction
- do not silently discard unsuccessful sessions
- do not convert revealed answers into successful mastery

---

# BACKEND

Use the existing backend synchronization system.

Continue carrying:

`game_type`

inside event JSON payloads.

Do NOT create a database `game_type` column in this milestone.

Do NOT run Alembic migrations.

If Hangman/Mystery evidence can fit into existing event JSON payloads, use that mechanism.

Do not modify shared database schemas.

If aggregated task-attempt persistence cannot represent failed Hangman outcomes correctly, report the limitation and make only a backward-compatible adjustment if possible.

Do not fake successful attempts to satisfy the old schema.

---

# SESSION SELECTION

For each selected mode, continue using the existing shared six-question session selection.

Do not create separate random question sets per mode outside the shared session system.

The game type should affect interaction, not the mathematical bank.

---

# SESSION SWITCHING

Flow:

Game Selection
→ choose mode
→ create fresh GameSession
→ six questions
→ summary
→ Choose Another Game
→ Game Selection

Do not reuse completed session state when switching game modes.

---

# ACCESSIBILITY

All modes must remain:

- visual-first
- no audio dependency
- large text
- large touch controls
- clear mathematical symbols
- no colour-only feedback
- responsive
- mouse compatible
- touch compatible
- minimal unnecessary text

Keep the visual style suitable for approximately 16-year-old learners.

Avoid preschool-like styling.

---

# SINHALA

Add new UI strings through the existing bilingual system.

Mark Sinhala as draft/unreviewed unless reviewed wording already exists.

Do not claim it has been language-validated.

---

# REGRESSION REQUIREMENTS

After both modes are implemented, verify Drag & Drop still supports:

- six-question selection
- easy/medium/hard balance
- drag
- tap
- hints
- multi-step questions
- stars
- analytics
- backend events
- summary
- game selection return
- responsive layout

Do not change Drag & Drop interaction behaviour.

---

# TESTING

Add focused unit tests for shared and mode-specific logic.

At minimum test:

## Hangman

- correct final answer
- wrong submitted answer
- firstAttemptCorrect
- 6-stage progression
- max-attempt failure
- hint does not count as attempt
- keypad edit does not count as attempt
- failed question not treated as solved
- gameType = hangman

## Mystery Reveal

- correct next-step selection
- incorrect next-step selection
- firstAttemptCorrect
- reveal progress
- hint does not count as attempt
- step-level analytics
- final reveal completion
- gameType = mystery_reveal

## Shared

- Drag & Drop analytics unchanged
- same variant IDs usable across all modes
- fresh session when switching modes

Run:

`npm run build`

`npm run lint`

`npm test`

Run backend Game tests only if backend Game code is modified.

Do not fix unrelated Tutor warnings.

---

# BROWSER VERIFICATION

Use backend-disabled/local-safe browser testing wherever possible.

Desktop:

- Game Selection
- Hangman full path
- Hangman failure path
- Mystery Reveal
- multi-step Mystery Reveal
- summary
- switching modes
- Drag & Drop regression

Phone:

- Hangman keypad
- Hangman figure visibility
- Mystery choices
- reveal visual
- summary layout
- touch interaction

Do not write automated browser-test sessions into the shared live database unless explicitly necessary.

---

# FINAL REPORT

After implementation report:

## 1. Files created

Exact paths.

## 2. Files modified

Exact paths.

## 3. Hangman architecture

Explain scene, input, figure progression and question flow.

## 4. Mystery Reveal architecture

Explain solution-step selection and reveal logic.

## 5. Shared question reuse

Confirm all three modes use the same 18 variants.

## 6. Shared ML-compatible fields

List the exact shared behaviour fields preserved.

## 7. Hangman-specific evidence

List exact fields.

## 8. Mystery-specific evidence

List exact fields.

## 9. First-attempt correctness

Explain how it is calculated in all new modes.

## 10. Failure semantics

Explain Hangman max-attempt failure and how it differs from solved.

## 11. Backend evidence

Show representative event payloads for both modes.

## 12. ML safety

Confirm no ML inference/adaptation was added.

## 13. Regression results

Drag & Drop, build, lint, tests and browser verification.

## 14. Known limitations

Especially anything that could affect real-data collection.

Do not proceed to ML production inference or database-schema redesign.