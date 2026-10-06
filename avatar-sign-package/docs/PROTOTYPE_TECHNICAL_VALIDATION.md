# Avatar posture repair — 2026-10-03

The **actual master GLB has been changed**, not just its player. This is a
mechanical/visual repair of the supplied 22 core prototype actions, **not validation
or creation of Sri Lankan Sign Language**. Learner-facing playback remains
validated-only by default; prototypes require the explicit reviewer checkbox.

## What changed

- Corrective FK key poses lower the flared upper arms and bring the forearms
  into the space in front of the chest. No IK targets/solver or old procedural
  sign generator is used.
- The bind-frame orientation is used to remove the imported neutral arm roll.
  Simply moving wrist twist to the forearm pinched the elbow skin; that candidate
  was rejected during visual review.
- Wrist axial roll is assigned to the forearm, wrist swing is limited to 45°.
  A shared ready pose keeps hands in front of the waist on returns to rest.
- Corrected **key poses** are interpolated, rather than recomputing a bend frame
  on every sample. This avoids hemisphere flips near a straight elbow.
- Smoothstep transitions are baked at 60 Hz with float32-deduplicated key times.
  Transitions are retimed to keep local rotation speed at or below 160°/s at 1×.
  Actions now take approximately 3.6–4.6 seconds, except the 1.5-second idle.
- Body material uses a matte finish instead of the imported 2× specular multiplier.
- The player has a closer upper-body view and shows the current equation beside
  the avatar, synchronized with the lesson step/hint.

Mesh, skin weights, inverse bind matrices, skeleton hierarchy, original colour
and normal textures, action names and finger **key shapes** are unchanged.
Finger transitions are eased/retimed with the arms. Arm trajectories and palm
orientations DID change; all lexical motions still require linguistic review.

## Reproducible checks

| Rig-space measurement | Supplied asset | Repaired asset |
| --- | ---: | ---: |
| Maximum wrist swing | 159.49° | 45.00° |
| Maximum upper-arm elevation from down | 60.37° | 33.75° |
| Maximum local arm/wrist rotation speed | 519.69°/s | 159.99°/s |
| Maximum elbow flexion | 112.27° | 134.42° |

These are measured asset regression bounds, **not medical/anatomical or language
certification**. Elbow flexion increased because hands are now raised in front of
the chest, not folded back at the wrists. Automated checks include neutral
endpoints, segment lengths, finite/unit quaternions, unique key times, all-clip
wrist/arm bounds and sampled wrist clearance from a conservative torso plane.
They do not constitute full mesh-collision, finger-contact or facial-grammar tests.

The repaired file retains the original binary payload and appends new animation
accessors. An original-versus-repaired comparison confirmed identical nodes,
skins, meshes, images and textures, and a maximum non-arm key-pose difference of
less than 0.000003 degrees (floating-point normalization only).

Browser QA captures the action midpoints, plus front/65° side transition
contact sheets for EQUATION, SUBTRACTION, SUBSTITUTION and NUMBER_5. These were
visually inspected, including the idle and return poses. Full lesson playback,
pause/resume, missing-asset fallback and reduced-motion behavior are also tested.

```bash
backend/.venv/bin/python avatar-sign-package/tools/audit_master_motion.py
backend/.venv/bin/python avatar-sign-package/tools/validate_sign_package.py
backend/.venv/bin/python -m pytest backend/tests/test_avatar_motion.py -q
cd frontend
npm run test:e2e
```

Screenshots are saved under ignored `frontend/artifacts/tutor-qa/`:
`all-action-midpoints.png`, `arm-transitions-0.png`, `arm-transitions-65.png`.

## Provenance and safe reproduction

- Original SHA-256: `31fd3bbd41cf1cac8c808becd9fd285ba605e3981c721c5a4f1c822b4861b24e`
- Repaired SHA-256: `a4c837f03a64484bd75fe05c71a04d9bba36198811308d609c0b8fc4ad0cd5b0`
- Expanded 56-action SHA-256: `dbecc512846c3a0bd1d3198c020f313eef017272a2e9df7a2f850d3000729fa9`
- Canonical path: `frontend/public/models/louise_signs_master.glb`
- Original asset is retained in Git at commit `e70c31f`.
- Offline repair tool: `tools/repair_master_arm_roll.py ORIGINAL.glb REVIEW.glb`.
  It rejects other source hashes, the repaired asset as input, and same-path
  input/output. It is not part of application startup or the build pipeline.
- For a candidate saved as `frontend/public/models/louise_arm_review.glb`, use
  `npm run test:e2e -- --review-avatar` in `frontend` before promoting it.

Do not run `avatar/create_sign_animations.py` or the historical
`build_linear_equation_glb_reference.py` to overwrite this asset. The old
`prototype_pose_report.json` describes the supplied pre-repair asset only.

The later 34-action composite expansion preserves these 22 repaired tracks and
appends review-only combinations of their neutral-to-neutral motion. See
`COMPOSITE_PROTOTYPE_ACTIONS.md`. The same mechanical audit applies, but the
expansion adds no linguistic validation.

## What this does NOT solve

- No lexical action has been human-validated as SLSL. Finger articulation,
  meaning, orientation and non-manual features need a qualified review.
- `BALANCE` and `BOTH_SIDES` still share the supplied motion; separate names do
  not establish separate signs. Number shapes are retained, not newly certified.
- This is a key-term gesture library, not complete sentence translation or a
  guarantee that the entire lesson is understandable through signing alone.
- Existing strict fallback stays in place. Quiz, Game, diagnostic model, Supabase
  schema and routes were not changed in this avatar repair.
