import type { AssessmentPhase, BalanceTask } from '../types'

// Reuses the tutor lesson's concept_id so pre/post results and the AI Tutor
// lesson refer to the same concept.
export const LINEAR_EQUATION_BALANCING_CONCEPT_ID = 'linear_equation_balancing'

// Operation distractors model the inverse-operation misconception (doing the
// wrong operation, or the right operation to the wrong side) rather than
// being arbitrary wrong answers — this is also one of the AI Tutor's
// recognised misconception codes.
function buildOperationChoices(constant: number): BalanceTask['operationChoices'] {
  return [
    {
      id: 'subtract',
      label: { en: `Subtract ${constant} from both sides`, si: `දෙපැත්තෙන්ම ${constant} අඩු කරන්න` },
      isCorrect: true,
    },
    {
      id: 'add',
      label: { en: `Add ${constant} to both sides`, si: `දෙපැත්තටම ${constant} එකතු කරන්න` },
      isCorrect: false,
    },
    {
      id: 'multiply',
      label: { en: `Multiply both sides by ${constant}`, si: `දෙපැත්තම ${constant} න් ගුණ කරන්න` },
      isCorrect: false,
    },
    {
      id: 'divide',
      label: { en: `Divide both sides by ${constant}`, si: `දෙපැත්තම ${constant} න් බෙදන්න` },
      isCorrect: false,
    },
  ]
}

const SHARED_HINTS: BalanceTask['hints'] = [
  {
    en: 'Whatever you do to one side of the balance, do the same to the other side.',
    si: 'තුලනයේ එක් පැත්තකට කරන ඕනෑම දෙයක්, අනෙක් පැත්තටත් එසේම කරන්න.',
  },
  {
    en: 'To isolate the variable, undo the operation that is attached to it.',
    si: 'විචල්‍යය තනිව තබා ගැනීමට, ඊට සම්බන්ධ ක්‍රියාව අහෝසි කරන්න.',
  },
]

// Pre/post tasks share the concept and difficulty but are not identical,
// so reassessment is not just an answer-memory test.
export const linearEquationBalancingTasksByPhase: Record<AssessmentPhase, BalanceTask[]> = {
  pre_tutor: [
    {
      id: 'leb-pre-1',
      variableLabel: 'x',
      leftSign: '+',
      leftConstant: 5,
      rightValue: 12,
      correctAnswer: 7,
      operationChoices: buildOperationChoices(5),
      hints: SHARED_HINTS,
    },
  ],
  post_tutor: [
    {
      id: 'leb-post-1',
      variableLabel: 'x',
      leftSign: '+',
      leftConstant: 4,
      rightValue: 11,
      correctAnswer: 7,
      operationChoices: buildOperationChoices(4),
      hints: SHARED_HINTS,
    },
  ],
}
