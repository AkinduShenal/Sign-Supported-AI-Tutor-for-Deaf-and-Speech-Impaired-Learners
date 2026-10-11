import type { QuizQuestion } from './types'

export const QUIZ_LENGTH = 10

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
  return questions
}

export function elapsedQuestionSeconds(startedAt: number, submittedAt: number): number {
  return Math.max(0, Math.round((submittedAt - startedAt) / 10) / 100)
}
