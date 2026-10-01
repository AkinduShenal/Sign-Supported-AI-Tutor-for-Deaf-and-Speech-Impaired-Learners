You are integrating a new avatar sign package into my existing project:

Project: Sign-Supported AI Tutor for Deaf and Speech-Impaired Learners
Frontend: React + TypeScript + Vite
Backend: Python + FastAPI
Current avatar: Louise, GLB/Blender-based
Research scope: selected Grade 10 Mathematics concepts, especially linear equations/equation balancing, with sign-supported key terms/avatar actions. This is NOT a full automatic sign-language translation system.

I will place this package at:
    avatar-sign-package/

IMPORTANT CONSTRAINTS
1. Do NOT continue the old procedural IK sign-generation approach.
2. Do NOT invent or procedurally guess Sri Lankan Sign Language lexical motion.
3. Use the package manifest as the single source of truth for sign IDs.
4. Lexical clips with `validation_status != "validated"` must be treated as unavailable in production mode.
5. The system must gracefully fall back to text/visual support when a validated clip is unavailable.
6. Preserve the current API contracts as much as possible.
7. Do not break quiz, game, tutor, remedial, Supabase, or routing code.
8. Keep all changes small, reviewable, and typed.
9. Do not delete the existing avatar implementation until the new one works; move legacy code to a clearly named backup/legacy location if necessary.
10. Do not regenerate or overwrite any validated animation asset.

YOUR TASK

A. Inspect the repository first.
- Find the current TutorAvatar component.
- Find the current backend sign planner.
- Find all places that create or consume `signActions`.
- Find the current Louise GLB path.
- Find existing tests for tutor/sign planning.

B. Integrate the package.
- Copy/adapt `avatar-sign-package/backend/sign_planner.py` into the backend tutor module.
- Keep the existing response field name `sign_actions` unless the repository proves otherwise.
- Replace hard-coded supported-action sets with IDs loaded from `avatar-sign-package/manifest/signs.json`.
- Apply `manifest/phrase_map.json` rules.
- Prefer teaching instruction text over raw expression token-by-token signing.
- Cap a teaching step at 4 sign actions.
- Deduplicate actions while preserving order.

C. Frontend.
- Adapt `avatar-sign-package/frontend/AvatarSignPlayer.tsx` to the project styling.
- Use ONE master avatar GLB:
      /models/louise_signs_master.glb
- Play named actions from `signActions`.
- Play each lexical action once.
- Return to looping IDLE after the sequence.
- Do not pause midway through a sign.
- Ignore unavailable actions safely.
- Keep replay support.
- Keep accessibility labels and text fallback.

D. Asset policy.
- The final master GLB must contain animation actions whose names exactly match manifest IDs.
- If the master GLB is not present yet, do NOT fabricate it.
- Instead show a clear development warning and keep the lesson usable through text/visual content.
- Add a development-only console warning listing missing requested animations.

E. Validation.
- Add a backend unit test for:
    "Subtract 3 from both sides"
  Expected high-level actions:
    SUBTRACTION, NUMBER_3, BOTH_SIDES or BALANCE
  Use the existing lesson semantics to choose between BOTH_SIDES and BALANCE; do not duplicate both unless the instruction requires both.
- Add tests for:
    "Add 4 to both sides"
    "Substitute 5 for x"
    "Solve the equation"
- Ensure unsupported signs never crash the frontend.
- Run backend tests, frontend typecheck/build, and lint if configured.

F. Legacy cleanup only after the new path works.
- Mark the procedural `create_sign_animations.py` path as legacy/deprecated.
- Do not delete it automatically.
- Add a short README explaining that lexical signs now come from validated clips.

DELIVERABLES
1. Show me the files changed.
2. Explain each change briefly.
3. Show test/build results.
4. Tell me exactly where to put `louise_signs_master.glb`.
5. Tell me which manifest sign clips are still missing/unvalidated.
6. Do not claim the signs are Sri Lankan Sign Language validated unless their manifest status is `validated`.

Start by inspecting the repo and reporting the current avatar/sign architecture before editing anything.
