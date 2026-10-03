# Avatar Sign Package

This package replaces the fragile procedural-IK approach with a clip-library architecture.

## Important

This package **does not claim to contain linguistically validated Sri Lankan Sign Language motion clips**.
The research scope is sign-supported mathematics key terms / avatar actions, not full automatic sign-language translation.

This canonical package contains:
- one authoritative sign inventory;
- stable clip names;
- backend phrase/action mapping data;
- a validation script;
- an animator/interpreter brief;
- the prototype animation catalog and pose report;
- the reproducible direct-FK prototype build tool.

## Current prototype asset

The runtime file `frontend/public/models/louise_signs_master.glb` contains 22 named educational
gesture actions supplied by `linear-equation-avatar-package/`. The manifest
marks them with `prototype_ready: true`, while their lexical
`validation_status` remains `needs_validation`. The application may play these
actions for research-prototype demonstrations, but must not describe them as
validated Sri Lankan Sign Language.

The current master includes the 2026-10-03 **arm-posture repair**: corrected FK
arm/wrist poses, a shared ready pose, eased transitions and matte material.
See [technical checks and limitations](docs/PROTOTYPE_TECHNICAL_VALIDATION.md).
The historical builder is not the current build path; do not use it to overwrite
the repaired master. No new lexical signs were validated by this repair.

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
- `clips/` — validated per-sign source clips
- `docs/` — validation, animation catalog, and pose-review evidence
- `tools/validate_sign_package.py` — manifest/master-GLB validator
- `tools/build_linear_equation_glb_reference.py` — prototype master-GLB build reference

Runtime integration lives in:

- `backend/app/modules/tutor/sign_planner.py`
- `frontend/src/components/AvatarSignPlayer.tsx`
