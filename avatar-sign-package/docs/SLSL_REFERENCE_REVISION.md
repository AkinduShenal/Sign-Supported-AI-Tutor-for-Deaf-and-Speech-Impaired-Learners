# Ordered mathematics support and SLSL number drafts — 2026-10-14

## Actual asset change

The runtime `frontend/public/models/louise_signs_master.glb` still contains 83
actions. `NUMBER_6` through `NUMBER_9` now use one hand rather than generic
two-handed `5 + n` counting. The following handshapes were observed in sampled
frames of the SLSL Dictionary videos, including the held pose and its transitions:

| Action | Extended right-hand fingers | Primary reference |
| --- | --- | --- |
| NUMBER_6 | Thumb and little finger | [6.mp4](https://cdn.srilankansignlanguage.org/media/6.mp4) |
| NUMBER_7 | Thumb and index finger | [7.mp4](https://cdn.srilankansignlanguage.org/media/7.mp4) |
| NUMBER_8 | Thumb, index and middle fingers | [8.mp4](https://cdn.srilankansignlanguage.org/media/8.mp4) |
| NUMBER_9 | Thumb, index, middle and ring fingers | [9.mp4](https://cdn.srilankansignlanguage.org/media/9.mp4) |

The right-arm, wrist and body tracks reuse the existing audited `NUMBER_1`
presentation; the left hand rests. Finger targets reuse the existing same-rig
open/closed rotations with eased transitions on the full arm timing grid. No IK,
new mesh, altered limb proportions or guessed foreign-language substitution is
used. The other 79 actions are preserved exactly, as are nodes, skins, meshes,
textures and materials. This revision does **not** repair skin weights or legs.

These are **source-referenced drafts**, not approved SLSL clips. Reference
placement is nearer the face than the existing avatar's presentation. Palm
orientation, finger splay/contact, placement, transitions, and comprehension
still need qualified SLSL review. Non-manual grammar has not been authored.

`NUMBER_0` playback is withheld: the reference [0.mp4](https://cdn.srilankansignlanguage.org/media/0.mp4)
shows a circular handshape, whereas the old asset uses a closed fist. Its old
track is retained for repair; the learner receives visual/reference support.

## Traceable sources

The public [SLSL Dictionary source](https://github.com/banool/slsl_dictionary)
identifies `https://cdn.srilankansignlanguage.org/dump/dump.json` as its dictionary
catalogue and `/media/<filename>` as its video path. The catalogue was inspected
for the specific number and arithmetic entries. Multiple dictionary variants
exist; a catalogue match alone does not approve the avatar motion.

The user supplied [Sign Math](https://www.youtube.com/@sign_math). Its public
video listing identifies the following Sinhala Sign Language demonstrations:

- [Numbers 1–5](https://www.youtube.com/watch?v=5-f1lsP1EKY)
- [Numbers 6–9](https://www.youtube.com/watch?v=qSz2nmgGelc)
- [Addition](https://www.youtube.com/watch?v=c0BTeMrbC7I)
- [Subtraction](https://www.youtube.com/watch?v=SzMytTC6Akk)
- [Multiplication](https://www.youtube.com/watch?v=C0TR5M5wHGM)
- [Division](https://www.youtube.com/watch?v=MDOSezSyWW4)

The YouTube listing was inspected, but video extraction failed. Handshape
transcription above uses the downloaded **SLSL Dictionary** videos, not unseen
YouTube footage. Addition reference frames were also inspected; the current
avatar operator clips are still generic prototypes, not faithful transcriptions.

The [University of Kelaniya AYATI Sign Language Laboratory](https://medicine.kln.ac.lk/ayati/index.php/sign-language-laboratory)
describes Deaf-led sign collection, dialect verification, dialogues and sample
sentences. That is the relevant review model. Similarity to ISL, PSL, NSL,
Bangladeshi signs, BSL, Auslan or NZSL does not establish SLSL equivalence.
No clips from those languages were silently substituted.

Comparative sources inspected at the catalogue/page level (their video motions
were not transcribed into this SLSL avatar):

| Region | Language-specific source |
| --- | --- |
| India | [ISLRTC ISL Dictionary](https://islrtc.nic.in/isl-dictionary/) |
| Pakistan | [FESF Pakistan Sign Language](https://psl.org.pk/) |
| Nepal | [NDFN NSL Dictionary](https://deafnepal.org.np/nsl/index.html) |
| Bangladesh | [IsharaKotha Bangla avatar corpus research](https://arxiv.org/abs/2511.16896) |
| United Kingdom | [Scottish Sensory Centre BSL Mathematics Glossary](https://www.ssc.education.ed.ac.uk/BSL/maths.html) |
| Australia | [Auslan Signbank](https://auslan.org.au/) |
| New Zealand | [NZSL Online](https://www.nzsl.nz/) |

These resources identify their own languages. No per-sign SLSL equivalence or
permission to redistribute/adapt foreign motion is inferred from a similar
English gloss. The Bangla research is contextual background, not an official
SLSL dictionary or a library imported into this project.

## Teaching and playback

Equations retain variable, operator and digit order, including repetitions:

- `x + 3 = 7`: VARIABLE → ADDITION → NUMBER_3 → EQUATION → NUMBER_7.
- `x = 4`: VARIABLE → EQUATION → NUMBER_4.
- `x + 3 - 3 = 7 - 3`: all nine occurrences survive.

Every adaptive worked step has a separate equation-reading part. Introductions,
revealed hints, and checked-step Q&A preserve their equation context. Token
offsets connect the active animation to its displayed symbol; selecting a symbol
replays only that occurrence and stays on the current part. A closer hand view,
slower playback, and relevant human-reference links are available.

Parentheses, unsigned multi-digit cardinals, signed numbers, fractions and
decimals without an authored rule remain explicit visual slots. They are never
silently spelled as unrelated digits or replaced by a balance gesture. A part
with missing/unavailable content does not automatically advance as if complete.
Prose remains authored bilingual **key-term support**, not automatic full-sentence
SLSL translation. Complete language support requires reviewed lexical clips,
sentence grammar and facial/body markers; rearranging topic cues cannot supply it.

## Reproduction and checks

Builder: `tools/repair_slsl_number_handshapes.py`. It pins the input checksum,
requires a separate candidate, verifies shared neutral endpoints, compares all
79 retained actions and the complete model structure, and saves backups before
promotion. It refuses an unknown/current already-revised master.

- Input SHA-256: `bc3aefd5a335199ec3936087060f9aaadb184b23a2246b288cd119d029ea2c4a`.
- Output SHA-256: `c8aad3c97da38389380eaa7c5edc14176a4340880bc18926ffe576b5e738c214`.
- Original backup: `tmp/slsl-number-review/louise_signs_master_before_number_revision.glb`.
- Original manifest: `tmp/slsl-number-review/signs_before_number_revision.json`.
- Build report: `tmp/slsl-number-review/number_revision_report.json`.
- Source video contact sheets: `tmp/sign-references/` (local, ignored).

To reproduce a candidate, use `--source` with the original backup and `--output`
with a new review path. `--promote` only accepts the original master as the
current installation; it is not a general-purpose overwrite command.

Validation commands:

```sh
backend/.venv/bin/python avatar-sign-package/tools/validate_sign_package.py
backend/.venv/bin/python -m pytest backend/tests/test_avatar_motion.py backend/tests/test_math_sign_planner.py backend/tests/test_expression_sign_support.py -q
cd frontend
npm run build
npm test
npm run test:e2e
```

Automated rig checks verify timing, neutral endpoints, finite unit rotations,
arm/wrist bounds and hand clearance. They do not certify finger mesh collisions,
natural signing, language correctness or student comprehension.

The full local Chrome scenario passed: 83 clips loaded, equation-token replay
and highlighting, closer hand framing, pause/resume, explanation/hint navigation,
mobile layouts, strict fallback, reduced motion and missing-model recovery,
with no uncaught JavaScript errors. New front/65-degree transition sheets for
numbers 6–9 were visually inspected in `frontend/artifacts/tutor-qa/`. This is
technical and visual QA, not a linguistic acceptance decision.
