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
