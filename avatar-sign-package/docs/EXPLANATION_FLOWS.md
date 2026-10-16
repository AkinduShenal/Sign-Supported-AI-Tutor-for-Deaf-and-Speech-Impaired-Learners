# Connected tutor explanation flows — 2026-10-14

The current adaptive tutor uses one explanation compiler for introductions,
worked-example instructions and reasons, practice introductions and solutions,
revealed hints, retrieved lesson help and generated Q&A answers. Each teaching
part retains its English/Sinhala caption and mathematical context. Equation
reading remains a separate ordered-token presentation.

The master GLB contains 153 actions: all 83 previous actions preserved exactly,
plus 70 connected flows. These are mathematical meaning demonstrations with
written support, **not verified SLSL sentence translations**. Coverage means the
current authored content has a motion plan; it does not prove that every word,
grammatical relation or facial expression has been signed correctly. Generated
Q&A uses one dominant teaching concept per paragraph and requests one idea per
paragraph from the generator; arbitrary prose is not a general sign translator.

## Learner behavior

- Different flows cover equality, balance, an unknown, isolating x, inverse
  operations, collecting terms, expansion, checking, practice and retrying.
- Numbers 1–9 have separate substitution flows and separate flows for each
  operation on both sides. The amount is retained in the caption and phase cue.
- For “ඉහත දැක්වෙන මුල් සමීකරණයේ x වෙනුවට 4 ආදේශ කරන්න.” the sequence is
  original equation → x position → 4 → place 4 → replaced equation. The original
  `x + 3 = 7` becomes `(4) + 3 = 7` on the meaning board. Its mathematical
  equivalence is unchanged; it avoids the expanded coefficient form obscuring x.
- Captions and equation highlights follow actual GLB playback time, including
  speed changes, pause/resume and seeking. Numbered phrase buttons replay from
  each phrase. A completed substitution keeps the result visible; “Next part”
  continues to the remaining explanation.
- Supported Q&A answers automatically select their avatar presentation. Generated
  answers use the text actually displayed to the learner and the checked current
  example step, instead of unrelated retrieved-note captions.
- Existing preview opt-in and reduced-motion preferences remain effective.
  Fractions, negative values, zero and unsupported symbol shapes retain explicit
  written support; the compiler does not pretend to sign them as single digits.

## Inspected primary references

Video frames from these SLSL Dictionary entries were inspected:

| Entry | Reference | Use in the draft |
| --- | --- | --- |
| look at | [SLSL video](https://cdn.srilankansignlanguage.org/media/2026_Voc_look_at.mp4) | Raised dominant hand and outward direction; manually adapted |
| above | [SLSL video](https://cdn.srilankansignlanguage.org/media/2026_Voc_above_kJTR0sL.mp4) | One hand above another; manually adapted for referencing the equation |
| put | [SLSL video](https://cdn.srilankansignlanguage.org/media/SLCFD_Verbs_Put.mp4) | Gather, lower/extend and release; manually adapted for placement |
| four | [SLSL video](https://cdn.srilankansignlanguage.org/media/4.mp4) | Four extended fingers with thumb folded; compared with the existing rig |

No direct entry establishing the mathematical sentence or a lexical sign for
“substitute in the original equation” was found in the inspected catalogue.
“Put” is a placement reference, not evidence that it is linguistically equivalent
to mathematical substitution. Mathematics strokes reuse the existing unvalidated
drafts. Source links are stored on the relevant manifest entries; inheriting a
source link does not validate a composite or its grammar.

The supplied [Sign Math channel](https://www.youtube.com/@sign_math) is retained
as a reference for review. Its video motion was not accessible for inspection
during this revision, so these flows do not claim transcription of that channel.
References from other countries are not treated as interchangeable SLSL signs.

## Build and technical checks

`tools/build_explanation_flows.py` requires the precise 83-action source SHA
`c8aad3c97da38389380eaa7c5edc14176a4340880bc18926ffe576b5e738c214`.
It preserves existing animation tracks and mesh/skin/material data, connects
active poses with eased rotations sampled at 60 Hz and keeps neutral endpoints.
Each flow stores its role/timing cue sheet in GLB extras and both manifests.
Current manifest version: 1.6.0. Current master SHA:
`dc6624627dd8b4f4a1ddc462a79fb9b6656983e65436a11297675de0f4e6ca4d`.

Re-running promotion against this already-expanded master is intentionally
rejected. The local pre-flow source backup and build report are under ignored
`tmp/explanation-flow-review/`.

Automated checks cover all four levels and five teaching strategies, all authored
knowledge parts, numeric-flow selection, original-equation substitution, matching
generated-answer captions, joint ranges/speeds, finite normalized rotations,
neutral endpoints, action presence and manifest checksums. Browser checks cover
phrase seeking, paused timing, substitution diagrams, full playback completion,
Q&A routing, hints, strict fallback, reduced motion, mobile layout and GLB failure.
Front and side transition sheets are generated in the ignored
`frontend/artifacts/tutor-qa/` folder and were visually inspected.

Language review still needs a fluent Sri Lankan Deaf signer/interpreter to check
handshape, palm orientation, location, movement, spatial grammar and nonmanual
features against each caption. Technical checks do not establish student
comprehension or linguistic accuracy. The asset is roughly 43 MiB, so first load
is larger than before; no animation is synthesized during a lesson request.
