# Teaching demonstration actions — 2026-10-12

This expansion produced **71 actions**. These 15 new actions combine existing
Louise movements into longer demonstrations. They are **review-only teaching
topic cues**, not independently authored lexical signs or SLSL sentence
translations. The user will review signing correctness and the final rendering.

All previous 56 action definitions/accessors and their original binary payload
are preserved. Nodes, skeleton hierarchy, meshes, skins/inverse bind matrices,
materials, images and textures are unchanged. New clips reuse the exact existing
rotation values, with shared neutral endpoints and no faster source movements.
No root motion, limb length change, new finger pose or facial expression is added.

| New action | Existing movement recipe | Duration at 1× |
| --- | --- | ---: |
| EXPLAIN_EQUALITY | EQUATION → BALANCE → BOTH_SIDES | 12.097 s |
| EXPLAIN_UNKNOWN_VARIABLE | EQUATION → VARIABLE → SOLVE | 12.516 s |
| EXPLAIN_UNDO_ADDITION | ADDITION → SUBTRACTION → BOTH_SIDES | 12.417 s |
| EXPLAIN_UNDO_SUBTRACTION | SUBTRACTION → ADDITION → BOTH_SIDES | 12.417 s |
| EXPLAIN_DIVIDE_COEFFICIENT | MULTIPLICATION → DIVISION → BOTH_SIDES → VARIABLE | 17.859 s |
| EXPLAIN_EXPAND_BRACKETS | MULTIPLICATION → BOTH_SIDES → EQUATION | 12.426 s |
| EXPLAIN_CLEAR_DENOMINATOR | DIVISION → MULTIPLICATION → BOTH_SIDES | 13.261 s |
| EXPLAIN_COLLECT_VARIABLES | VARIABLE → BOTH_SIDES → EQUATION | 12.503 s |
| EXPLAIN_CHECK_SOLUTION | ANSWER → SUBSTITUTION → EQUATION | 11.877 s |
| EXPLAIN_SOLUTION_FOUND | VARIABLE → SOLVE → ANSWER | 12.734 s |
| TEACH_STEP_BY_STEP | EQUATION → VARIABLE → BOTH_SIDES → SOLVE (1.15× duration) | 19.168 s |
| TEACH_CONCEPTUAL | EQUATION → BALANCE → BOTH_SIDES (1.1× duration) | 13.286 s |
| TEACH_WORKED_EXAMPLE | EQUATION → SOLVE → ANSWER → SUBSTITUTION | 16.081 s |
| TEACH_PROGRESSIVE_HINTS | VARIABLE → BOTH_SIDES → SOLVE (1.1× duration) | 14.162 s |
| TEACH_INDEPENDENT_CHALLENGE | EQUATION → VARIABLE → SOLVE → SUBSTITUTION | 16.646 s |

## Runtime use

The original expansion used EXPLAIN/TEACH actions for longer reasoning and
strategy segments. The later [short explanation cue expansion](EXPLANATION_CUES.md)
preserves these actions for review and replaces runtime captions with smaller
bilingual teaching ideas. Exact operation/amount cues remain in the checked
instruction segments. The current master has 83 actions; both manifests match.

Select **Teaching approach**, then explicitly enable **Preview gestures** for
review. The player advances through explanation parts after actual clip
completion. Individual new actions are also selectable under **Playback settings
& sign details → New animation examples**. Playback remains validated-only by
default; selecting/reviewing an action does not validate it.

## Preservation evidence and reproducibility

Tool: `tools/append_teaching_prototype_actions.py`.

- Source SHA-256 (56 actions): `dbecc512846c3a0bd1d3198c020f313eef017272a2e9df7a2f850d3000729fa9`.
- Expanded SHA-256 (71 actions): `27ca27d9a207128740d54cebe3ec76fda8d6f4af1ac3f31092bfbd63337f379d`.
- Original backup: `tmp/avatar-animation-expansion/louise_signs_master_56_actions.glb`.
- Candidate and builder report: `tmp/avatar-animation-expansion/` (ignored).

The builder rejects unknown/already-expanded sources and creates a separate
candidate. Before promotion, it compares original action/accessor definitions,
binary prefix and rig/visual metadata, verifies exact source quaternion reuse,
finite/strictly increasing float32 times, unit quaternions and shared neutral
joins, then backs up the existing master.

To reproduce a candidate after promotion, use `--source` with the saved 56-action
GLB and `--source-manifest` with `tmp/avatar-animation-expansion/signs_56_actions.json`.
Leave `--promote` off: promotion intentionally refuses to replace an already
expanded master.

No browser, full motion-audit or test suite was run for this expansion, following
the user's request to handle verification. These internal preservation checks
do not establish collision-free skinning or linguistic correctness. Review the
new motions from the front and side, including transitions and fingers, before
approving a clip. Source pose limitations remain present in the new combinations.
