# Grade 10 linear-equation tutor: implementation and research boundaries

## What runs now

The main frontend now opens an adaptive linear-equation workspace. It uses the
existing Louise master GLB, not any procedural IK script. The old static lesson
endpoint and other component/database contracts remain intact.

1. Open **Lesson setup / team diagnostic handoff**.
2. Import a JSON payload matching `POST /api/v1/tutor/strategy`, containing
   `student_id`, `concept_id`, `quiz`, `game`, and `learner`.
3. `POST /api/v1/tutor/adaptive-lesson` validates that same input and returns a
   teaching plan. This endpoint is read-only and does not save diagnostic data.
4. The frontend presents the selected examples, misconception support,
   progressively revealed hints, practice and corresponding `sign_actions`.
5. `POST /api/v1/tutor/practice/check` grades the known question using exact
   fractions. Decimal/fraction equivalents are accepted; no expression is executed.
6. Export practice evidence before changing plans or reloading. Export includes
   numerical attempts, hints, avatar interactions, request timing and content/model
   versions, but not the diagnostic payload, real names or student identifiers.

Manual **Preview** buttons are for development/teacher review, not a diagnosis.
They exercise the same content bank without inventing student records. Quiz/Game
teammates can call the API directly or reuse `getAdaptiveLesson` from the frontend
API module. Accepted concept identifiers are `linear_equations` and
`linear_equation_balancing`; out-of-scope concepts are rejected.

## Placement and teaching

| Draft path | Content |
| --- | --- |
| Foundation | Equality/balance; undo addition and subtraction |
| One step | Inverse operations; a single addition/subtraction or coefficient |
| Two step | Undo the constant term, then divide by the coefficient |
| Extended | Variables on both sides, brackets, denominators, negative coefficients and fractional solutions |

There are 10 worked examples and 8 practice questions in the current bank. Every
worked solution preserves equality, shows the original equation, and checks the
solution by substitution. This is a bounded draft content bank, not comprehensive
coverage of every Grade 10 curriculum problem (e.g. word problems and
identity/no-solution cases are not included).

Current placement uses the mean of the three supplied mastery scores: below 0.5
starts at foundation, below 0.7 at one step, otherwise two step. An
`advanced_challenge` recommendation plus advanced quiz difficulty enables extended
content. Step-by-step/conceptual recommendations return to foundation. These are
transparent **draft heuristics**, not empirically established cut-offs. Support
and misconception inputs also affect the strategy, examples and guidance. A
reported sign error moves the relevant negative-constant example first.

Conceptual learners receive a recurring balance explanation. Progressive-hint
and advanced strategies encourage trying before viewing worked solutions. All
learners retain access to examples and hints. Slower response times are **not**
treated as lower mathematical ability. Text/equations never disappear when an
avatar or preference changes.

The current engine remains `rule-based-v2`, **not a trained ML model**. The shared
`StrategyPredictor` boundary and `TutorStrategyService.model` allow an evaluated
predictor to replace it consistently in `/strategy` and `/adaptive-lesson`.
Training a model still requires independently labelled, consented data, a
student-separated evaluation split, and comparison with this baseline. Do not
train/evaluate on rules' own labels and describe that as learner evidence.

Quiz/Game own incoming diagnosis/mastery. Tutor selects support, and records
practice evidence. Two first-attempt unaided answers permit previewing the next
topic, **not a claim of mastery gain**. Actual post-tutoring reassessment and
non-improvement analysis remain separate components.

## Avatar behavior and safeguards

- One runtime asset: `frontend/public/models/louise_signs_master.glb`.
- The 2026-10-03 posture revision changes the actual GLB arm/wrist key poses,
  transition timing and neutral pose; it is not just a player-control update.
  The mesh/skeleton and finger key shapes remain from the supplied package.
  See [avatar repair checks](../avatar-sign-package/docs/PROTOTYPE_TECHNICAL_VALIDATION.md).
- Canonical manifests: `avatar-sign-package/manifest/` (backend deployment snapshots remain synced).
- The library has 22 prototype actions; **zero lexical signs are human-validated**.
- Default playback is validated-only. Missing/unvalidated actions use text and
  equation support. A reviewer must explicitly enable **Preview unvalidated
  gestures** to inspect the supplied prototype actions.
- These clips are educational gestures, not reliable SLSL sentence translation.
  Sign grammar, finger shapes, facial expression and meaning need qualified
  review. No new lexical motion has been guessed or generated in this change.
- Fractions, negative values and multi-digit values in the adaptive instruction
  are not converted into misleading sequences of single-digit gestures. They
  remain explicit in the written equation.
- Stage captions stay beside the avatar. Users can slow, pause/resume and replay.
  Reduced-motion users start with auto-play off; they can opt in explicitly.
- The player waits for the model-viewer's animation-name update before assigning
  single-play loop options. Old pending playback is cancelled on stage/policy
  changes and unmount. Sequence completion returns to the supplied neutral clip.
  Because the installed model-viewer can omit `finished` events, completion is
  also detected from actual clip time reaching its duration, not a wall-clock
  timeout. Paused/offscreen clips are not skipped by elapsed time.
- No new skeleton rotations, IK, mesh editing or retargeting occurs at runtime.

## Proposal alignment and outstanding work

Checked against the user's **IT23393202-Proposal Report new.pdf**, physical
pages 18–22 (sections 4–5), especially the individual responsibility boundary and
FR01–FR12. This implements the visual-first, non-audio, selected-concept-support
direction; it does not redefine the research as automatic full translation.

| Requirement | Current status |
| --- | --- |
| FR01–06, FR09–10 | Diagnostic contract, adaptive content, examples, hints, practice, replay and feedback implemented; effectiveness not yet evaluated |
| FR07–08 | Safe manifest/player path implemented; validated language assets still missing |
| FR11 | Browser-session attempt/hint/interaction recording and JSON export; not complete centralized study instrumentation |
| FR12 | Existing diagnostic prediction persistence unchanged; new tutoring evidence is **not automatically persisted to Supabase** |
| Accuracy / research effectiveness | Algebra regression checks in code; teacher content review, interpreter review and student evaluation still required |

Before student evaluation:

1. Have a Grade 10 mathematics teacher review all examples, vocabulary,
   difficulty placement and practice tasks. Add curriculum-specific word problems
   and wider practice coverage if required by the approved study scope.
2. Have an SLSL reviewer evaluate actual animated clips on the intended avatar.
   Record reviewer/date/reference/decision for each lexical action. Only mark a
   manifest entry `validated` following genuine approval; keep missing signs in
   fallback. Do not infer sign validity from a technical pose report.
3. Integrate authenticated, consent-aware session/evidence persistence and
   pseudonymous reassessment linkage into the team's shared backend. The current
   export is formative browser telemetry, not tamper-proof assessment evidence.
   Export data is capped at the latest 1000 events and disappears on reload.
4. Train/evaluate the tutoring strategy model using labelled data; report model
   version, leakage controls, class imbalance and calibration. No trained artifact
   or suitable labelled dataset was supplied for this implementation.
5. Compare **text + visuals** with **the same text + visuals + validated avatar
   support**, holding mathematical content constant. Predefine outcome measures,
   matched pre/post reassessment, comprehension/usability feedback, and how hints
   affect scoring. Do not treat repeated correct attempts as independent success.

The system is a stronger, testable research prototype, not yet a validated
research result or a promise to teach every learner effectively.

## Verification and local use

Run backend/frontend as in the root README. Use the current branch locally;
deploying old `main` will not expose the new endpoints. No deployment or shared
database migration is part of this change.

```bash
backend/.venv/bin/python -m pytest backend/tests -q
backend/.venv/bin/python avatar-sign-package/tools/validate_sign_package.py
backend/.venv/bin/python avatar-sign-package/tools/audit_master_motion.py
```

From `frontend/`:

```bash
npm run test
npm run build
npm run lint
npm run test:e2e
```

`test:e2e` uses an isolated Chrome profile plus temporary local servers on ports
8126/5176/9226 and an in-memory test database. It never opens your signed-in tabs,
writes Supabase, or calls Railway. It stops the processes it starts. Screenshots
are local ignored artifacts under `frontend/artifacts/tutor-qa/`; they are not
linguistic approval. On a non-macOS host set `TUTOR_TEST_CHROME` to your Chrome
executable path. A Python backend venv and frontend dependencies must be installed.

The motion audit checks quaternion validity, neutral endpoints, arm-segment length
stability and sampled elbow bends using keyframes plus midpoint interpolation.
It does **not** establish natural signing, collision-free skinning or finger/
facial correctness. Review rendered animation, not just numeric audit results.

Verification on 2026-10-02: 55 backend tests, 4 playback-policy unit tests,
frontend build/lint, manifest checks and the isolated browser smoke suite pass.
Browser checks include complete sequence-to-idle playback, pause/resume,
reduced-motion behavior, missing-model fallback, answer grading and mobile
overflow. The production build still reports the existing large, lazily loaded
model-viewer chunk; no library rewrite was attempted here.
