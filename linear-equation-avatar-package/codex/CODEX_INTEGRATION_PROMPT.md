You are working inside my existing project `sign-supported-ai-tutor`.

I have added a package folder named `linear-equation-avatar-package/`. It contains a REAL animated master GLB, not just a manifest.

IMPORTANT FILE:
`linear-equation-avatar-package/frontend/public/models/louise_signs_master.glb`

It contains these named animations:
IDLE, EQUATION, BALANCE, BOTH_SIDES, VARIABLE, ADDITION, SUBTRACTION, MULTIPLICATION, DIVISION, SUBSTITUTION, SOLVE, ANSWER, NUMBER_0, NUMBER_1, NUMBER_2, NUMBER_3, NUMBER_4, NUMBER_5, NUMBER_6, NUMBER_7, NUMBER_8, NUMBER_9.

TASK
1. Inspect the current repository before editing. Find current `TutorAvatar.tsx`, current sign planner, tutor lesson response structure, and every place that reads `sign_actions`.
2. BACK UP the current avatar component and old procedural animation generator. Do not delete them.
3. Copy the package master GLB to:
   `frontend/public/models/louise_signs_master.glb`
4. Replace/adapt the current avatar playback code using:
   `linear-equation-avatar-package/frontend/src/components/LinearEquationAvatar.tsx`
   Keep the existing UI styling and component API where possible.
5. Adapt:
   `linear-equation-avatar-package/backend/sign_planner_linear_equation.py`
   into the existing backend tutor sign planner. Keep the existing `sign_actions` response field.
6. Do NOT run or use the old Blender procedural IK generator for these clips. The new master GLB already contains the animations.
7. Make the Linear Equation lesson use meaningful short sequences. Required examples:
   - Key idea / equation balance: `EQUATION -> BOTH_SIDES`
   - Identify x: `VARIABLE`
   - Add 4 to both sides: `ADDITION -> NUMBER_4 -> BOTH_SIDES`
   - Subtract 3 from both sides: `SUBTRACTION -> NUMBER_3 -> BOTH_SIDES`
   - Substitute 5 for x: `SUBSTITUTION -> NUMBER_5 -> VARIABLE`
   - Solve: `SOLVE`
   - Show result: `ANSWER`
8. Max 4 animations per teaching step. Deduplicate while preserving order. Do not sign every raw expression token.
9. Each animation already starts/ends at the neutral pose. Play each requested clip once and return to looping IDLE after the sequence.
10. Add a development console warning for a requested animation that is not present in `availableAnimations`, but never crash the lesson.
11. Run frontend typecheck/build and backend tests. Add planner tests for the example sentences above.
12. Show me: files changed, test/build output, and the final lesson-to-animation mapping.

RESEARCH WORDING CONSTRAINT
These clips are generated prototype educational avatar gestures. Do NOT describe them as validated Sri Lankan Sign Language unless a qualified human reviewer validates them later.

Start by inspecting the repository. Then perform the integration completely; do not stop after giving instructions.
