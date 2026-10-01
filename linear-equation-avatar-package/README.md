# Linear Equation Avatar Package

This package contains an actual animated Louise master GLB for the Linear Equation lesson.

## Main file
`frontend/public/models/louise_signs_master.glb`

SHA-256: `31fd3bbd41cf1cac8c808becd9fd285ba605e3981c721c5a4f1c822b4861b24e`

## Animations
IDLE, EQUATION, BALANCE, BOTH_SIDES, VARIABLE, ADDITION, SUBTRACTION, MULTIPLICATION, DIVISION, SUBSTITUTION, SOLVE, ANSWER, NUMBER_0, NUMBER_1, NUMBER_2, NUMBER_3, NUMBER_4, NUMBER_5, NUMBER_6, NUMBER_7, NUMBER_8, NUMBER_9

## Install
1. Copy `frontend/public/models/louise_signs_master.glb` to the same path in your project.
2. Integrate `frontend/src/components/LinearEquationAvatar.tsx` or adapt your existing `TutorAvatar.tsx`.
3. Adapt `backend/sign_planner_linear_equation.py` into your current tutor sign planner.
4. Run the frontend and verify the animation list in the browser.

## Important
This version no longer relies on the old procedural Blender IK/pole-target generator. The embedded animation channels use direct FK rotations on the existing Louise skeleton.

The motions are prototype educational gestures for the research UI. They are not validated Sri Lankan Sign Language.

See `codex/CODEX_INTEGRATION_PROMPT.md` for the exact Codex task.
