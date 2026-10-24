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

The current runtime master contains **153 actions**, including 70 connected
explanation flows for the current tutor introductions, worked steps, hints and
Q&A. Baked phrase timings drive equation highlights and phrase replay. See
[explanation flows, source evidence and coverage](docs/EXPLANATION_FLOWS.md).
The 2026-10-14 number revision fixes source-referenced shapes for numbers 6–9,
adds ordered equation reading and withholds the inaccurate legacy zero motion.
See [number sources and remaining language work](docs/SLSL_REFERENCE_REVISION.md).
All lexical clips remain unvalidated; the flows demonstrate mathematical meaning
with bilingual text and diagrams rather than claiming full SLSL translation.

Before the short-cue and number revisions, `frontend/public/models/louise_signs_master.glb` contained 71 named educational
gesture actions: 22 repaired core actions, 34 review-only composites and 15 longer
teaching-demo composites. The manifest
marks them with `prototype_ready: true`, while their lexical
`validation_status` remains `needs_validation`. The application may play these
actions for research-prototype demonstrations, but must not describe them as
validated Sri Lankan Sign Language.

The current master includes the 2026-10-03 **arm-posture repair**: corrected FK
arm/wrist poses, a shared ready pose, eased transitions and matte material.
See [technical checks and limitations](docs/PROTOTYPE_TECHNICAL_VALIDATION.md).
The historical builder is not the current build path; do not use it to overwrite
the repaired master. No new lexical signs were validated by this repair.

The 34 added actions concatenate the repaired core motions and preserve their
neutral endpoints and joint limits. See
[the composite recipes and review references](docs/COMPOSITE_PROTOTYPE_ACTIONS.md).
They are placeholders for reviewer testing, not claims of lexical equivalence.

The 15 teaching demos preserve all original 56 actions and reuse their repaired
rotations at the original speed or slower. Backend explanation segments request
these longer actions by teaching topic/strategy. No new hand shapes, signs or
facial movements are authored. See [the teaching demo review catalogue](docs/TEACHING_DEMO_ACTIONS.md).

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
- `tools/append_composite_prototype_actions.py` — guarded 34-action review expansion
- `tools/append_teaching_prototype_actions.py` — guarded 15-action teaching expansion with source preservation checks and a backup before promotion
- `tools/build_explanation_flows.py` — guarded 70-action connected choreography build with baked phrase timing and source preservation

Runtime integration lives in:

- `backend/app/modules/tutor/sign_planner.py`
- `frontend/src/components/AvatarSignPlayer.tsx`
