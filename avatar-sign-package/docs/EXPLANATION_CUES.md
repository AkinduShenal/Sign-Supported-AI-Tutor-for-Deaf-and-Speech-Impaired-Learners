# Short explanation cues

The current master contains **83 actions**. Twelve new review-only cues reuse
the existing Louise motion. They are smaller combinations of the existing
educational gestures, not newly authored lexical signs, ASL transcriptions or
validated Sri Lankan Sign Language sentences.

## Teaching flow

The step-by-step introduction is now eight small bilingual ideas:

1. An equation is like a balanced scale.
2. Both sides have the same value.
3. x represents an unknown number.
4. Work through one small step at a time.
5. Apply the same operation to both sides.
6. Leave x by itself on one side.
7. Put the answer in place of x in the original equation.
8. Check that the two sides have the same value.

Every strategy has its own order and prompts. Worked steps break reasoning
into short ideas, preserving the bank's exact instructions, equations, answers
and operation/number gestures. Each hint is segmented from only the revealed
hint. No later hint or final answer is read to prepare an earlier hint.

The ten RAG notes have authored bilingual parts too. The index still ranks the
original excerpts. Avatar support plays the source parts and the checked current
step, rather than pretending to translate arbitrary generated text.

The player shows the current part's English/Sinhala caption and equation, and
advances on actual clip completion. Existing replay, pause, previous/next part,
prototype opt-in and reduced-motion controls remain. Default speed remains 1×.

## Appended motions

| Cue | Existing motion recipe | Duration at 1× |
| --- | --- | ---: |
| CUE_EQUATION_BALANCE | EQUATION → BALANCE | 7.906 s |
| CUE_EQUAL_SIDES | BOTH_SIDES → BALANCE | 8.282 s |
| CUE_ISOLATE_VARIABLE | VARIABLE → SOLVE | 8.702 s |
| CUE_SUBTRACT_BOTH | SUBTRACTION → BOTH_SIDES | 7.851 s |
| CUE_ADD_BOTH | ADDITION → BOTH_SIDES | 8.657 s |
| CUE_DIVIDE_BOTH | DIVISION → BOTH_SIDES | 8.741 s |
| CUE_MULTIPLY_BOTH | MULTIPLICATION → BOTH_SIDES | 8.611 s |
| CUE_INVERSE_ADDITION | ADDITION → SUBTRACTION | 8.225 s |
| CUE_INVERSE_MULTIPLICATION | MULTIPLICATION → DIVISION | 9.070 s |
| CUE_SUBSTITUTE_ANSWER | ANSWER → SUBSTITUTION | 8.062 s |
| CUE_VERIFY_EQUALITY | SUBSTITUTION → BALANCE | 8.221 s |
| CUE_COLLECT_VARIABLE | VARIABLE → BOTH_SIDES | 8.689 s |

## Preservation evidence

Builder: `tools/append_explanation_cue_actions.py --promote`.

- Source SHA-256: `27ca27d9a207128740d54cebe3ec76fda8d6f4af1ac3f31092bfbd63337f379d`.
- New master SHA-256: `bc3aefd5a335199ec3936087060f9aaadb184b23a2246b288cd119d029ea2c4a`.
- Backup: `tmp/avatar-explanation-cues/louise_signs_master_71_actions.glb`.
- Manifest backup: `tmp/avatar-explanation-cues/signs_71_actions.json`.
- Candidate and report: `tmp/avatar-explanation-cues/` (ignored).

Before installation, the builder compared all 71 old animation/accessor/view
definitions and the complete original binary prefix. Nodes, skeleton, meshes,
skins/inverse bind matrices, materials, textures and images remain unchanged.
Every appended rotation is an exact copy of a source rotation, with the same
movement duration and shared neutral endpoints at joins. Float32 key times
remain finite and strictly increasing. Both deployment manifests match.

Reproduce a candidate using `--source` with the 71-action backup and
`--source-manifest` with its saved manifest. Do not use `--promote` to replace an
already expanded master; the builder intentionally refuses unknown sources.

These internal preservation checks passed during asset creation. No test suite,
browser rendering or complete motion audit was run, following the user's request
to verify themselves. Existing pose limitations are inherited. Visual collision,
finger articulation and signing correctness still need review; clip names and
captions alone do not establish linguistic accuracy.
