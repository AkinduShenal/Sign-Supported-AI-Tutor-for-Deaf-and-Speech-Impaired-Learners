# Game Question Bank Milestone 2 - Teacher Review

Prepared October 20, 2026 (Asia/Colombo). PP1: October 22, 2026.

**DRAFT - TEACHER REVIEW REQUIRED. No proposed v2 questions are active or approved.**

Print landscape and adjust scale in print preview. Use `teacher_review_live_v1.csv` for the 18 original questions and `new_variant_review.csv` for the 12 primary additions and 6 reserves. CSVs are UTF-8 with BOM; preserve original ID/equation text and negative-answer signs when importing.

Teacher name: ____________________  Review date: ____________________
Rubric decision/reference: __________________________________________

## Proposed rubric - not yet approved

- Beginner: one inverse operation; judge negative-number demand separately.
- Intermediate: two inverse operations, variable on one side; constant denominators may be included.
- Advanced: variables on both sides, multi-step bracket/denominator reasoning or three or more inverse operations.
- The two original simple multiplicative-bracket questions are provisionally Advanced following the initial guideline, but each has a two-operation shortcut. The teacher may choose Intermediate.
- A grouped numerator divided by a constant is provisionally Intermediate when solved in two inverse operations. Confirm this boundary consistently.
- Classify the actual interaction: guided operation choice in Drag & Drop, final integer in Hangman. A word-problem activity name does not establish equation-construction evidence.

Allowed approval values: `beginner`, `intermediate`, `advanced`. Leave pending/rejected approval cells blank and explain rejections in comments. Blank is never approval. Review the equation, answer, operation sequence, hints and distractors, not difficulty alone. Grade 10 suitability and Sinhala instructions/hints require teacher judgement; engineering arithmetic checks are not educational approval.

## A. All 18 live questions - exact original identities preserved

Source: [equationVariants.ts](../../../frontend/src/game/data/equationVariants.ts). Source SHA-256: `6563e3d337b7e0016adc22cf08100b569093ff01f1216ad2d805f7f0582fe60c`.

Original tier values are exactly `easy`, `medium`, `hard`. The proposed values do not change the live bank. All answers and keyed balanced-operation sequences passed offline arithmetic checks.

| Original variant ID | Original activity ID | Equation | Answer | Original tier | Proposed tier | Mathematical reasoning | Reason | Teacher-approved tier | Teacher comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LEQ_E_001 | LEQ_ONE_STEP_ADD | x + 3 = 7 | 4 | easy | beginner | Apply -3 to both sides. | One inverse operation; retain the tier under its proposed display label. |  |  |
| LEQ_E_002 | LEQ_ONE_STEP_SUB | x - 5 = 8 | 13 | easy | beginner | Apply +5 to both sides. | One inverse operation; retain the tier under its proposed display label. |  |  |
| LEQ_E_003 | LEQ_ONE_STEP_MUL | 3x = 12 | 4 | easy | beginner | Apply ÷3 to both sides. | One inverse operation; retain the tier under its proposed display label. |  |  |
| LEQ_E_004 | LEQ_ONE_STEP_DIV | x ÷ 4 = 5 | 20 | easy | beginner | Apply ×4 to both sides. | One inverse operation; retain the tier under its proposed display label. |  |  |
| LEQ_E_005 | LEQ_ONE_STEP_ADD | x + 8 = 15 | 7 | easy | beginner | Apply -8 to both sides. | One inverse operation; retain the tier under its proposed display label. |  |  |
| LEQ_E_006 | LEQ_ONE_STEP_MUL | 5x = 35 | 7 | easy | beginner | Apply ÷5 to both sides. | One inverse operation; retain the tier under its proposed display label. |  |  |
| LEQ_M_001 | LEQ_TWO_STEP | 2x + 3 = 11 | 4 | medium | intermediate | Apply -3, then ÷2 to both sides. | Two inverse operations; Medium maps to Intermediate. |  |  |
| LEQ_M_002 | LEQ_TWO_STEP | 3x - 4 = 11 | 5 | medium | intermediate | Apply +4, then ÷3 to both sides. | Two inverse operations; Medium maps to Intermediate. |  |  |
| LEQ_M_003 | LEQ_BRACKET | 2(x + 3) = 16 | 5 | medium | advanced | Apply ÷2, then -3 to both sides. | Provisional Advanced under the bracket guideline, but dividing first gives two operations. Teacher may approve Intermediate. |  |  |
| LEQ_M_004 | LEQ_BRACKET | 3(x - 2) = 18 | 8 | medium | advanced | Apply ÷3, then +2 to both sides. | Provisional Advanced under the bracket guideline, but dividing first gives two operations. Teacher may approve Intermediate. |  |  |
| LEQ_M_005 | LEQ_VAR_BOTH_SIDES | 2x + 3 = x + 7 | 4 | medium | advanced | Apply -x, then -3 to both sides. | Collect variable terms from both sides; proposed Advanced conceptual demand. |  |  |
| LEQ_M_006 | LEQ_VAR_BOTH_SIDES | 3x + 4 = x + 10 | 3 | medium | advanced | Apply -x, then -4, then ÷2 to both sides. | Collect variable terms from both sides and complete three operations. |  |  |
| LEQ_H_001 | LEQ_FRACTIONAL | x ÷ 2 + 3 = 7 | 8 | hard | intermediate | Apply -3, then ×2 to both sides. | Two inverse operations with a constant denominator; Hard overstates the proposed tier. |  |  |
| LEQ_H_002 | LEQ_FRACTIONAL | x ÷ 3 - 2 = 5 | 21 | hard | intermediate | Apply +2, then ×3 to both sides. | Two inverse operations with a constant denominator; Hard overstates the proposed tier. |  |  |
| LEQ_H_003 | LEQ_ALGEBRAIC_FRACTION | (x + 1) ÷ 2 = 5 | 9 | hard | intermediate | Apply ×2, then -1 to both sides. | Two inverse operations on a grouped numerator; no variable denominator or domain restriction. |  |  |
| LEQ_H_004 | LEQ_ALGEBRAIC_FRACTION | (x - 3) ÷ 4 = 2 | 11 | hard | intermediate | Apply ×4, then +3 to both sides. | Two inverse operations on a grouped numerator; no variable denominator or domain restriction. |  |  |
| LEQ_H_005 | LEQ_WORD_PROBLEM | x + 6 = 20 | 14 | hard | beginner | Apply -6 to both sides. | One-step equation is supplied. Its old word-problem activity name does not establish equation-construction evidence. |  |  |
| LEQ_H_006 | LEQ_WORD_PROBLEM | 2x - 5 = 13 | 9 | hard | intermediate | Apply +5, then ÷2 to both sides. | Two-step equation is supplied; its old word-problem activity name does not make it Advanced. |  |  |

## B. Twelve primary additions - proposed, not active

All final answers are signed integer strings supported by the existing digits/minus answer representation. Each step has four distinct operation choices, one keyed choice, a hint and a resulting equation in [the draft manifest](v2_release_manifest.DRAFT.json). These are mathematical proposals, not student observations.

| Candidate ID | Equation | Answer | Proposed tier | Operation sequence | Reason | Teacher-approved tier | Teacher comments |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GQBV2_Q019_R01 | x + 9 = 2 | -7 | beginner | -9 | One inverse operation with a negative solution; explicit teacher sign-demand decision. |  |  |
| GQBV2_Q020_R01 | 7x = 42 | 6 | beginner | ÷7 | One division with a new positive coefficient. |  |  |
| GQBV2_Q021_R01 | x ÷ 6 = 4 | 24 | beginner | ×6 | One multiplication to undo division. |  |  |
| GQBV2_Q022_R01 | 4x + 7 = -9 | -4 | intermediate | -7 -> ÷4 | Two inverse operations with signed arithmetic. |  |  |
| GQBV2_Q023_R01 | x ÷ 4 - 3 = -1 | 8 | intermediate | +3 -> ×4 | Two operations with a constant denominator and a negative right side. |  |  |
| GQBV2_Q024_R01 | (x + 5) ÷ 3 = 6 | 13 | intermediate | ×3 -> -5 | Grouped numerator with two inverse operations and no variable denominator. |  |  |
| GQBV2_Q025_R01 | 4x + 5 = 2x + 17 | 6 | advanced | -2x -> -5 -> ÷2 | Variables on both sides; collect terms and use two further inverse operations. |  |  |
| GQBV2_Q026_R01 | 5x + 16 = 2x + 7 | -3 | advanced | -2x -> -16 -> ÷3 | Variables on both sides plus a negative solution. |  |  |
| GQBV2_Q027_R01 | 2(x + 4) + 3 = 21 | 5 | advanced | -3 -> ÷2 -> -4 | Bracket and outer constant require three inverse operations. |  |  |
| GQBV2_Q028_R01 | (3x + 6) ÷ 2 = x + 7 | 8 | advanced | ×2 -> -2x -> -6 | Clear a denominator, distribute on the right and collect variable terms. |  |  |
| GQBV2_Q029_R01 | 4(x - 1) + 6 = 30 | 7 | advanced | -6 -> ÷4 -> +1 | Bracketed subtraction and an outer constant require three operations. |  |  |
| GQBV2_Q030_R01 | -2x + 7 = x - 8 | 5 | advanced | -x -> -7 -> ÷(-3) | Variables on both sides and division by a negative coefficient. |  |  |

## C. Six replacement candidates - excluded from the primary roster

Two reserves per tier support substitutions after approval. They are not automatically selected, approved, or added to the 30-question roster. They do not guarantee coverage of unlimited rejections; request further candidates if a tier's reserves are exhausted.

| Reserve ID | Equation | Answer | Proposed tier | Operation sequence | Teacher-approved tier | Teacher comments |
| --- | --- | --- | --- | --- | --- | --- |
| GQBV2_Q031_R01 | x - 11 = 6 | 17 | beginner | +11 |  |  |
| GQBV2_Q032_R01 | 9x = 54 | 6 | beginner | ÷9 |  |  |
| GQBV2_Q033_R01 | 5x - 6 = 29 | 7 | intermediate | +6 -> ÷5 |  |  |
| GQBV2_Q034_R01 | (x - 7) ÷ 2 = -4 | -1 | intermediate | ×2 -> +7 |  |  |
| GQBV2_Q035_R01 | 6x - 7 = 3x + 20 | 9 | advanced | -3x -> +7 -> ÷3 |  |  |
| GQBV2_Q036_R01 | 5(x - 2) + 4 = 24 | 6 | advanced | -4 -> ÷5 -> +2 |  |  |

## D. Expected count, conditional on teacher decisions

| Group | Beginner | Intermediate | Advanced | Total |
| --- | ---: | ---: | ---: | ---: |
| Original 18 under proposed labels | 7 | 7 | 4 | 18 |
| Twelve primary additions | 3 | 3 | 6 | 12 |
| Proposed primary v2 roster | 10 | 10 | 10 | 30 |
| Excluded reserves | 2 | 2 | 2 | 6 |
| Actually active v2 questions | 0 | 0 | 0 | 0 |

## E. Special teacher decisions

1. `LEQ_M_003` and `LEQ_M_004`: Advanced under the bracket guideline, or Intermediate based on the two-operation shortcut?
2. `LEQ_H_001`-`LEQ_H_004`: confirm constant-denominator/grouped-numerator questions as Intermediate, consistently with the bracket decision.
3. `LEQ_H_005` and `LEQ_H_006`: approve Beginner/Intermediate based on the supplied equation; the original word-problem IDs do not prove equation construction.
4. `GQBV2_Q019_R01` and `GQBV2_Q022_R01`: approve negative-answer demand at Beginner/Intermediate. Reserves Q031 and Q033 offer positive alternatives.
5. `GQBV2_Q026_R01` and `GQBV2_Q030_R01`: approve signed Advanced arithmetic; Q030 divides by negative 3.
6. `GQBV2_Q028_R01`: multiplying both sides by 2 distributes on the right. Confirm that the operation card, result and hint communicate this clearly.
7. Review Grade 10 suitability, distractors, hints and Sinhala language before activation. The pack does not claim teacher-approved translations.

If both original bracket questions become Intermediate, keeping all original 18 gives 7 Beginner / 9 Intermediate / 2 Advanced. The additions would then need 3 Beginner / 1 Intermediate / 8 Advanced. After approval, two proposed new Intermediate questions could be replaced by Advanced reserves Q035/Q036. No substitution is automatic. Changed classifications/content need new question revisions; changed selection needs a new release manifest.

Teacher overall decision: ____________________
Approved rubric version: ____________________
Further replacements / language corrections required: ____________________

See [V2_DESIGN.md](V2_DESIGN.md) for immutable identities, hashes, compatibility contracts, remaining database verification and the implementation sequence. This review is not a learner assessment label or a research outcome.
