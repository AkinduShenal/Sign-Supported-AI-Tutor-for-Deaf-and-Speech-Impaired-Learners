# Avatar Sign Package

This package replaces the fragile procedural-IK approach with a clip-library architecture.

## Important

This package **does not claim to contain linguistically validated Sri Lankan Sign Language motion clips**.
The research scope is sign-supported mathematics key terms / avatar actions, not full automatic sign-language translation.

The package gives you:
- one authoritative sign inventory;
- stable clip names;
- backend phrase/action mapping;
- a frontend player for a master GLB containing named animation clips;
- a validation script;
- an animator/interpreter brief;
- a Codex integration prompt.

## Current prototype asset

`frontend/public/models/louise_signs_master.glb` contains 22 named educational
gesture actions supplied by `linear-equation-avatar-package/`. The manifest
marks them with `prototype_ready: true`, while their lexical
`validation_status` remains `needs_validation`. The application may play these
actions for research-prototype demonstrations, but must not describe them as
validated Sri Lankan Sign Language.

## Recommended validation workflow

1. Keep the existing Louise avatar mesh/skeleton as the base.
2. Create or record each sign clip against a validated Sri Lankan Sign Language reference.
3. Retarget every clip to the same Louise armature.
4. Ensure every clip starts and ends in the same neutral pose.
5. Name the Blender action exactly as the manifest ID.
6. Merge approved actions into one `louise_signs_master.glb`.
7. Use the frontend player to play animation names from the backend sign plan.
8. Do not generate lexical sign motion from heuristic procedural IK.

## Priority

Start with:
- IDLE
- NUMBER_0 ... NUMBER_9
- ADDITION / SUBTRACTION / MULTIPLICATION / DIVISION
- EQUATION
- ALGEBRA / VARIABLE / EXPRESSION / TERM / COEFFICIENT
- SUBSTITUTION
- BALANCE / BOTH_SIDES
- SOLVE / ANSWER

Then add tutor/remedial support signs.

## Folder layout

- `manifest/signs.json` — canonical sign catalog
- `manifest/phrase_map.json` — text/expression to sign IDs
- `backend/sign_planner.py` — manifest-driven planner
- `frontend/AvatarSignPlayer.tsx` — master-GLB animation player
- `clips/` — validated per-sign source clips
- `docs/` — validation and animator guidance
- `codex/CODEX_INTEGRATION_PROMPT.md` — integration prompt
