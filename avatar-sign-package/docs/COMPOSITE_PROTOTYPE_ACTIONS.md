# Composite Prototype Actions

The master avatar contains the original 22 repaired actions plus 34
**review-only composite actions**. The added actions concatenate existing,
technically checked neutral-to-neutral motion. They are useful for playback and
review, but they are not motion-captured transcriptions and are not validated
Sri Lankan Sign Language.

## Review references

Use these Sri Lankan resources to check or replace each prototype:

- SLSL Dictionary video app: https://play.google.com/store/apps/details?id=com.banool.slsl_dictionary
- Sri Lanka Sign Language learning channel: https://www.youtube.com/@SriLankaSignLanguage
- National Institute of Language Education and Training: https://nilet.gov.lk/index.php/en/academic-programs

The public sources do not expose a verified video for every specialised maths
or tutoring term. Do not treat an ASL or other-country sign as SLSL. A qualified
reviewer should record the accepted regional/reference variant, reviewer and
date before changing `validation_status`.

## Composite recipes

| Added action | Existing motion recipe |
| --- | --- |
| ALGEBRA | VARIABLE → EQUATION |
| EXPRESSION | VARIABLE → ANSWER |
| TERM | VARIABLE → NUMBER_1 |
| COEFFICIENT | NUMBER_2 → VARIABLE |
| POSITIVE | ADDITION → ANSWER |
| NEGATIVE | SUBTRACTION → ANSWER |
| BRACKET | BOTH_SIDES → BALANCE |
| START | ANSWER → SOLVE |
| NEXT | ANSWER → ADDITION |
| PREVIOUS | SUBTRACTION → ANSWER |
| STEP | NUMBER_1 |
| EXAMPLE | EQUATION → ANSWER |
| PRACTICE | SOLVE |
| QUESTION | VARIABLE → BALANCE |
| HINT | VARIABLE → ANSWER |
| REPEAT | SUBSTITUTION → SUBSTITUTION |
| TRY_AGAIN | SUBTRACTION → SOLVE |
| CHECK | SUBSTITUTION → EQUATION |
| CORRECT | EQUATION → ANSWER |
| INCORRECT | SUBTRACTION → BALANCE |
| FINISH | SOLVE → ANSWER |
| ERROR_CORRECTION | SUBTRACTION → SUBSTITUTION |
| FOUNDATION | BALANCE → EQUATION |
| STEP_BY_STEP | NUMBER_1 → NUMBER_2 |
| MATCH | EQUATION |
| DRAG_DROP | SUBSTITUTION |
| SIGN_KEYWORD | VARIABLE → ANSWER |
| VISUAL | ANSWER → VARIABLE |
| TEXT | EQUATION → ANSWER |
| EASY | ANSWER |
| DIFFICULT | BALANCE → VARIABLE |
| SLOW | time-stretched SOLVE |
| IMPROVED | ADDITION → SOLVE |
| NOT_IMPROVED | SUBTRACTION → BALANCE |

## Replacement workflow

1. Review the intended meaning with a qualified SLSL reviewer.
2. Record or author the accepted motion on the same Louise skeleton.
3. Keep the shared neutral start/end pose and exact manifest action name.
4. Replace only that action in the master GLB.
5. Run the package validator, motion audit, backend tests and browser review.
6. Mark an action `validated` only after the reviewer approves the final avatar
   rendering—not merely the human reference video.

The expansion tool is
`tools/append_composite_prototype_actions.py`. It accepts only the canonical
repaired 22-action source hash so that it cannot accidentally re-expand or
overwrite an unknown asset.
