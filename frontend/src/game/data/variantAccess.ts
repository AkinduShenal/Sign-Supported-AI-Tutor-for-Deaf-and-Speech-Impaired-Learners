import type { LevelStep } from './equationLevels.ts'
import type { EquationVariant } from './equationVariants.ts'

// Small accessors so every game mode reads the same meanings out of a
// variant instead of re-deriving them from display strings.

// The operation card that is correct for this step (e.g. "-3").
export function expectedOperationOf(step: LevelStep): string {
  return step.choices.find((choice) => choice.isCorrect)?.label ?? ''
}

// The equation the learner sees when this step starts: the starting
// equation for step 0, otherwise the previous step's result.
export function equationBeforeStep(variant: EquationVariant, stepIndex: number): string {
  return stepIndex === 0 ? variant.startingEquation : variant.steps[stepIndex - 1].resultText
}

// Stable within one assessment (including a resize), but varied between
// learners/sessions so the correct operation is not always the first card.
export function orderedChoices<T>(choices: readonly T[], seed: string): T[] {
  let state = 2166136261
  for (const char of seed) state = Math.imul(state ^ char.charCodeAt(0), 16777619) >>> 0
  const result = [...choices]
  for (let index = result.length - 1; index > 0; index -= 1) {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0
    const other = state % (index + 1)
    ;[result[index], result[other]] = [result[other], result[index]]
  }
  return result
}
