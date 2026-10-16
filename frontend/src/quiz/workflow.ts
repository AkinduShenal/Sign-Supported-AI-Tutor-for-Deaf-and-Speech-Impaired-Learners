import type { DifficultyLevel, QuizQuestion } from './types'

export const QUIZ_LENGTH = 10
export const QUIZ_LEVELS: Record<DifficultyLevel, { en: string; si: string }> = {
  easy: { en: 'Beginner Level', si: 'ආරම්භක මට්ටම' },
  medium: { en: 'Intermediate Level', si: 'අතරමැදි මට්ටම' },
  hard: { en: 'Advanced Level', si: 'උසස් මට්ටම' },
}

export function transitionAfterAnswers(answeredCount: number): 'easy' | 'medium' | null {
  return answeredCount === 4 ? 'easy' : answeredCount === 8 ? 'medium' : null
}

export function validatePreQuestionBank(questions: QuizQuestion[]): QuizQuestion[] {
  const counts = { easy: 0, medium: 0, hard: 0 }
  const ids = new Set<string>()
  for (const question of questions) {
    if (
      !question.id || ids.has(question.id)
      || question.concept_id !== 'linear_equations'
      || question.question_type !== 'multiple_choice'
      || !question.question_text_en || !question.question_text_si
      || !Array.isArray(question.options) || question.options.length !== 4
      || new Set(question.options.map(option => option.id)).size !== 4
      || question.options.some(option => !option.id || !option.option_text_en || !option.option_text_si)
      || !(question.difficulty_level in counts)
    ) {
      throw new Error('The ten-question assessment is not ready. Please contact your teacher.')
    }
    ids.add(question.id)
    counts[question.difficulty_level] += 1
  }
  if (
    questions.length !== QUIZ_LENGTH
    || counts.easy !== 4 || counts.medium !== 4 || counts.hard !== 2
  ) {
    throw new Error('The ten-question assessment is not ready. Please contact your teacher.')
  }
  // Preserve the bank's order inside each difficulty group while enforcing the
  // official Beginner -> Intermediate -> Advanced learner progression.
  const tier = { easy: 0, medium: 1, hard: 2 }
  return [...questions].sort((left, right) => tier[left.difficulty_level] - tier[right.difficulty_level])
}

export function elapsedQuestionSeconds(startedAt: number, submittedAt: number): number {
  return Math.max(0, Math.round((submittedAt - startedAt) / 10) / 100)
}
