import type { LevelStep } from './equationLevels'

export type DifficultyLevel = 'easy' | 'medium' | 'hard'

// One Easy/Medium/Hard diagnostic variant (Milestone 3 Steps 10-11). Reuses
// the exact same step/choice mechanic as the original 5 levels — balancing
// an equation one inverse-operation card at a time — so no new Phaser
// rendering or drag-and-drop is needed for the new equation types below.
// variantId doubles as the task_id sent to the backend for this task.
export interface EquationVariant {
  variantId: string
  activityId: string
  concept: string
  difficulty: DifficultyLevel
  startingEquation: string
  steps: LevelStep[]
}

// --- EDIT HERE to change variants, equations, choices, or hints ---

// EASY — basic one-step equations (addition/subtraction/multiplication/division).
export const EASY_VARIANTS: EquationVariant[] = [
  {
    variantId: 'LEQ_E_001',
    activityId: 'LEQ_ONE_STEP_ADD',
    concept: 'one_step_addition',
    difficulty: 'easy',
    startingEquation: 'x + 3 = 7',
    steps: [
      {
        choices: [
          { label: '-3', isCorrect: true },
          { label: '+3', isCorrect: false },
          { label: '×3', isCorrect: false },
          { label: '÷3', isCorrect: false },
        ],
        stepText: 'x + 3 - 3 = 7 - 3',
        resultText: 'x = 4',
        hint: 'Use the opposite operation to remove +3.',
      },
    ],
  },
  {
    variantId: 'LEQ_E_002',
    activityId: 'LEQ_ONE_STEP_SUB',
    concept: 'one_step_subtraction',
    difficulty: 'easy',
    startingEquation: 'x - 5 = 8',
    steps: [
      {
        choices: [
          { label: '+5', isCorrect: true },
          { label: '-5', isCorrect: false },
          { label: '×5', isCorrect: false },
          { label: '÷5', isCorrect: false },
        ],
        stepText: 'x - 5 + 5 = 8 + 5',
        resultText: 'x = 13',
        hint: 'Use the opposite operation to remove -5.',
      },
    ],
  },
  {
    variantId: 'LEQ_E_003',
    activityId: 'LEQ_ONE_STEP_MUL',
    concept: 'one_step_multiplication',
    difficulty: 'easy',
    startingEquation: '3x = 12',
    steps: [
      {
        choices: [
          { label: '÷3', isCorrect: true },
          { label: '×3', isCorrect: false },
          { label: '+3', isCorrect: false },
          { label: '-3', isCorrect: false },
        ],
        stepText: '3x ÷ 3 = 12 ÷ 3',
        resultText: 'x = 4',
        hint: '3 is multiplying x. Use the opposite operation.',
      },
    ],
  },
  {
    variantId: 'LEQ_E_004',
    activityId: 'LEQ_ONE_STEP_DIV',
    concept: 'one_step_division',
    difficulty: 'easy',
    startingEquation: 'x ÷ 4 = 5',
    steps: [
      {
        choices: [
          { label: '×4', isCorrect: true },
          { label: '÷4', isCorrect: false },
          { label: '+4', isCorrect: false },
          { label: '-4', isCorrect: false },
        ],
        stepText: '(x ÷ 4) × 4 = 5 × 4',
        resultText: 'x = 20',
        hint: 'x is divided by 4. Use the opposite operation.',
      },
    ],
  },
  {
    variantId: 'LEQ_E_005',
    activityId: 'LEQ_ONE_STEP_ADD',
    concept: 'one_step_addition',
    difficulty: 'easy',
    startingEquation: 'x + 8 = 15',
    steps: [
      {
        choices: [
          { label: '-8', isCorrect: true },
          { label: '+8', isCorrect: false },
          { label: '×8', isCorrect: false },
          { label: '÷8', isCorrect: false },
        ],
        stepText: 'x + 8 - 8 = 15 - 8',
        resultText: 'x = 7',
        hint: 'Use the opposite operation to remove +8.',
      },
    ],
  },
  {
    variantId: 'LEQ_E_006',
    activityId: 'LEQ_ONE_STEP_MUL',
    concept: 'one_step_multiplication',
    difficulty: 'easy',
    startingEquation: '5x = 35',
    steps: [
      {
        choices: [
          { label: '÷5', isCorrect: true },
          { label: '×5', isCorrect: false },
          { label: '+5', isCorrect: false },
          { label: '-5', isCorrect: false },
        ],
        stepText: '5x ÷ 5 = 35 ÷ 5',
        resultText: 'x = 7',
        hint: '5 is multiplying x. Use the opposite operation.',
      },
    ],
  },
]

// MEDIUM — two-step equations, bracket equations, variable on both sides.
export const MEDIUM_VARIANTS: EquationVariant[] = [
  {
    variantId: 'LEQ_M_001',
    activityId: 'LEQ_TWO_STEP',
    concept: 'two_step_equation',
    difficulty: 'medium',
    startingEquation: '2x + 3 = 11',
    steps: [
      {
        choices: [
          { label: '-3', isCorrect: true },
          { label: '+3', isCorrect: false },
          { label: '÷3', isCorrect: false },
          { label: '×3', isCorrect: false },
        ],
        stepText: '2x + 3 - 3 = 11 - 3',
        resultText: '2x = 8',
        hint: 'Remove +3 first.',
      },
      {
        choices: [
          { label: '÷2', isCorrect: true },
          { label: '×2', isCorrect: false },
          { label: '+2', isCorrect: false },
          { label: '-2', isCorrect: false },
        ],
        stepText: '2x ÷ 2 = 8 ÷ 2',
        resultText: 'x = 4',
        hint: 'Now remove the multiplication by 2.',
      },
    ],
  },
  {
    variantId: 'LEQ_M_002',
    activityId: 'LEQ_TWO_STEP',
    concept: 'two_step_equation',
    difficulty: 'medium',
    startingEquation: '3x - 4 = 11',
    steps: [
      {
        choices: [
          { label: '+4', isCorrect: true },
          { label: '-4', isCorrect: false },
          { label: '÷4', isCorrect: false },
          { label: '×4', isCorrect: false },
        ],
        stepText: '3x - 4 + 4 = 11 + 4',
        resultText: '3x = 15',
        hint: 'Remove -4 first.',
      },
      {
        choices: [
          { label: '÷3', isCorrect: true },
          { label: '×3', isCorrect: false },
          { label: '+3', isCorrect: false },
          { label: '-3', isCorrect: false },
        ],
        stepText: '3x ÷ 3 = 15 ÷ 3',
        resultText: 'x = 5',
        hint: 'Now remove the multiplication by 3.',
      },
    ],
  },
  {
    variantId: 'LEQ_M_003',
    activityId: 'LEQ_BRACKET',
    concept: 'bracket_equation',
    difficulty: 'medium',
    startingEquation: '2(x + 3) = 16',
    steps: [
      {
        choices: [
          { label: '÷2', isCorrect: true },
          { label: '×2', isCorrect: false },
          { label: '+2', isCorrect: false },
          { label: '-2', isCorrect: false },
        ],
        stepText: '2(x + 3) ÷ 2 = 16 ÷ 2',
        resultText: 'x + 3 = 8',
        hint: 'Remove the bracket by undoing the ×2 outside it first.',
      },
      {
        choices: [
          { label: '-3', isCorrect: true },
          { label: '+3', isCorrect: false },
          { label: '×3', isCorrect: false },
          { label: '÷3', isCorrect: false },
        ],
        stepText: 'x + 3 - 3 = 8 - 3',
        resultText: 'x = 5',
        hint: 'Now remove +3.',
      },
    ],
  },
  {
    variantId: 'LEQ_M_004',
    activityId: 'LEQ_BRACKET',
    concept: 'bracket_equation',
    difficulty: 'medium',
    startingEquation: '3(x - 2) = 18',
    steps: [
      {
        choices: [
          { label: '÷3', isCorrect: true },
          { label: '×3', isCorrect: false },
          { label: '+3', isCorrect: false },
          { label: '-3', isCorrect: false },
        ],
        stepText: '3(x - 2) ÷ 3 = 18 ÷ 3',
        resultText: 'x - 2 = 6',
        hint: 'Remove the bracket by undoing the ×3 outside it first.',
      },
      {
        choices: [
          { label: '+2', isCorrect: true },
          { label: '-2', isCorrect: false },
          { label: '×2', isCorrect: false },
          { label: '÷2', isCorrect: false },
        ],
        stepText: 'x - 2 + 2 = 6 + 2',
        resultText: 'x = 8',
        hint: 'Now remove -2.',
      },
    ],
  },
  {
    variantId: 'LEQ_M_005',
    activityId: 'LEQ_VAR_BOTH_SIDES',
    concept: 'variable_on_both_sides',
    difficulty: 'medium',
    startingEquation: '2x + 3 = x + 7',
    steps: [
      {
        choices: [
          { label: '-x', isCorrect: true },
          { label: '+x', isCorrect: false },
          { label: '-2x', isCorrect: false },
          { label: '+2x', isCorrect: false },
        ],
        stepText: '2x + 3 - x = x + 7 - x',
        resultText: 'x + 3 = 7',
        hint: 'Remove x from both sides to collect the variable on one side.',
      },
      {
        choices: [
          { label: '-3', isCorrect: true },
          { label: '+3', isCorrect: false },
          { label: '×3', isCorrect: false },
          { label: '÷3', isCorrect: false },
        ],
        stepText: 'x + 3 - 3 = 7 - 3',
        resultText: 'x = 4',
        hint: 'Now remove +3.',
      },
    ],
  },
  {
    variantId: 'LEQ_M_006',
    activityId: 'LEQ_VAR_BOTH_SIDES',
    concept: 'variable_on_both_sides',
    difficulty: 'medium',
    startingEquation: '3x + 4 = x + 10',
    steps: [
      {
        choices: [
          { label: '-x', isCorrect: true },
          { label: '+x', isCorrect: false },
          { label: '-3x', isCorrect: false },
          { label: '+3x', isCorrect: false },
        ],
        stepText: '3x + 4 - x = x + 10 - x',
        resultText: '2x + 4 = 10',
        hint: 'Remove x from both sides to collect the variable on one side.',
      },
      {
        choices: [
          { label: '-4', isCorrect: true },
          { label: '+4', isCorrect: false },
          { label: '×4', isCorrect: false },
          { label: '÷4', isCorrect: false },
        ],
        stepText: '2x + 4 - 4 = 10 - 4',
        resultText: '2x = 6',
        hint: 'Now remove +4.',
      },
      {
        choices: [
          { label: '÷2', isCorrect: true },
          { label: '×2', isCorrect: false },
          { label: '+2', isCorrect: false },
          { label: '-2', isCorrect: false },
        ],
        stepText: '2x ÷ 2 = 6 ÷ 2',
        resultText: 'x = 3',
        hint: 'Now remove the multiplication by 2.',
      },
    ],
  },
]

// HARD — fractional equations, algebraic fractions, word-problem-style
// one/two-step equations (Milestone 3 explicitly excludes simultaneous and
// quadratic equations from this milestone).
export const HARD_VARIANTS: EquationVariant[] = [
  {
    variantId: 'LEQ_H_001',
    activityId: 'LEQ_FRACTIONAL',
    concept: 'fractional_equation',
    difficulty: 'hard',
    startingEquation: 'x ÷ 2 + 3 = 7',
    steps: [
      {
        choices: [
          { label: '-3', isCorrect: true },
          { label: '+3', isCorrect: false },
          { label: '×3', isCorrect: false },
          { label: '÷3', isCorrect: false },
        ],
        stepText: 'x ÷ 2 + 3 - 3 = 7 - 3',
        resultText: 'x ÷ 2 = 4',
        hint: 'Remove +3 first.',
      },
      {
        choices: [
          { label: '×2', isCorrect: true },
          { label: '÷2', isCorrect: false },
          { label: '+2', isCorrect: false },
          { label: '-2', isCorrect: false },
        ],
        stepText: '(x ÷ 2) × 2 = 4 × 2',
        resultText: 'x = 8',
        hint: 'x is divided by 2. Use the opposite operation.',
      },
    ],
  },
  {
    variantId: 'LEQ_H_002',
    activityId: 'LEQ_FRACTIONAL',
    concept: 'fractional_equation',
    difficulty: 'hard',
    startingEquation: 'x ÷ 3 - 2 = 5',
    steps: [
      {
        choices: [
          { label: '+2', isCorrect: true },
          { label: '-2', isCorrect: false },
          { label: '×2', isCorrect: false },
          { label: '÷2', isCorrect: false },
        ],
        stepText: 'x ÷ 3 - 2 + 2 = 5 + 2',
        resultText: 'x ÷ 3 = 7',
        hint: 'Remove -2 first.',
      },
      {
        choices: [
          { label: '×3', isCorrect: true },
          { label: '÷3', isCorrect: false },
          { label: '+3', isCorrect: false },
          { label: '-3', isCorrect: false },
        ],
        stepText: '(x ÷ 3) × 3 = 7 × 3',
        resultText: 'x = 21',
        hint: 'x is divided by 3. Use the opposite operation.',
      },
    ],
  },
  {
    variantId: 'LEQ_H_003',
    activityId: 'LEQ_ALGEBRAIC_FRACTION',
    concept: 'algebraic_fraction',
    difficulty: 'hard',
    startingEquation: '(x + 1) ÷ 2 = 5',
    steps: [
      {
        choices: [
          { label: '×2', isCorrect: true },
          { label: '÷2', isCorrect: false },
          { label: '+2', isCorrect: false },
          { label: '-2', isCorrect: false },
        ],
        stepText: '((x + 1) ÷ 2) × 2 = 5 × 2',
        resultText: 'x + 1 = 10',
        hint: 'Clear the fraction first by multiplying both sides by 2.',
      },
      {
        choices: [
          { label: '-1', isCorrect: true },
          { label: '+1', isCorrect: false },
          { label: '×1', isCorrect: false },
          { label: '÷1', isCorrect: false },
        ],
        stepText: 'x + 1 - 1 = 10 - 1',
        resultText: 'x = 9',
        hint: 'Now remove +1.',
      },
    ],
  },
  {
    variantId: 'LEQ_H_004',
    activityId: 'LEQ_ALGEBRAIC_FRACTION',
    concept: 'algebraic_fraction',
    difficulty: 'hard',
    startingEquation: '(x - 3) ÷ 4 = 2',
    steps: [
      {
        choices: [
          { label: '×4', isCorrect: true },
          { label: '÷4', isCorrect: false },
          { label: '+4', isCorrect: false },
          { label: '-4', isCorrect: false },
        ],
        stepText: '((x - 3) ÷ 4) × 4 = 2 × 4',
        resultText: 'x - 3 = 8',
        hint: 'Clear the fraction first by multiplying both sides by 4.',
      },
      {
        choices: [
          { label: '+3', isCorrect: true },
          { label: '-3', isCorrect: false },
          { label: '×3', isCorrect: false },
          { label: '÷3', isCorrect: false },
        ],
        stepText: 'x - 3 + 3 = 8 + 3',
        resultText: 'x = 11',
        hint: 'Now remove -3.',
      },
    ],
  },
  {
    variantId: 'LEQ_H_005',
    activityId: 'LEQ_WORD_PROBLEM',
    concept: 'word_problem_one_step',
    difficulty: 'hard',
    startingEquation: 'x + 6 = 20',
    steps: [
      {
        choices: [
          { label: '-6', isCorrect: true },
          { label: '+6', isCorrect: false },
          { label: '×6', isCorrect: false },
          { label: '÷6', isCorrect: false },
        ],
        stepText: 'x + 6 - 6 = 20 - 6',
        resultText: 'x = 14',
        hint: 'A number increased by 6 gives 20 — remove +6 from both sides.',
      },
    ],
  },
  {
    variantId: 'LEQ_H_006',
    activityId: 'LEQ_WORD_PROBLEM',
    concept: 'word_problem_two_step',
    difficulty: 'hard',
    startingEquation: '2x - 5 = 13',
    steps: [
      {
        choices: [
          { label: '+5', isCorrect: true },
          { label: '-5', isCorrect: false },
          { label: '×5', isCorrect: false },
          { label: '÷5', isCorrect: false },
        ],
        stepText: '2x - 5 + 5 = 13 + 5',
        resultText: '2x = 18',
        hint: 'Double a number, then subtract 5, gives 13 — remove -5 first.',
      },
      {
        choices: [
          { label: '÷2', isCorrect: true },
          { label: '×2', isCorrect: false },
          { label: '+2', isCorrect: false },
          { label: '-2', isCorrect: false },
        ],
        stepText: '2x ÷ 2 = 18 ÷ 2',
        resultText: 'x = 9',
        hint: 'Now remove the multiplication by 2.',
      },
    ],
  },
]

export const ALL_VARIANTS: EquationVariant[] = [
  ...EASY_VARIANTS,
  ...MEDIUM_VARIANTS,
  ...HARD_VARIANTS,
]
