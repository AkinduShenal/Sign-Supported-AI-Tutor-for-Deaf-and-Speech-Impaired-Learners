export interface OperationChoice {
  label: string
  isCorrect: boolean
}

// One balancing move within a level. Most levels have a single step;
// level 5 has two, solved one after another without leaving the level.
export interface LevelStep {
  choices: OperationChoice[]
  // Shown briefly after a correct choice, to show the operation being
  // applied to both sides of the equation.
  stepText: string
  // What the equation becomes after this step. For a level with another
  // step after this one, this text is also what gets displayed as the
  // "current equation" while that next step is being solved.
  resultText: string
  hint: string
}

export interface EquationLevel {
  id: string
  title: string
  concept: string
  startingEquation: string
  steps: LevelStep[]
}

// --- EDIT HERE to change levels, equations, choices, or hints ---
export const EQUATION_LEVELS: EquationLevel[] = [
  {
    id: 'level-1',
    title: 'Level 1',
    concept: 'one_step_addition',
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
    id: 'level-2',
    title: 'Level 2',
    concept: 'one_step_subtraction',
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
    id: 'level-3',
    title: 'Level 3',
    concept: 'one_step_multiplication',
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
    id: 'level-4',
    title: 'Level 4',
    concept: 'one_step_division',
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
    id: 'level-5',
    title: 'Level 5',
    concept: 'two_step_equation',
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
]
