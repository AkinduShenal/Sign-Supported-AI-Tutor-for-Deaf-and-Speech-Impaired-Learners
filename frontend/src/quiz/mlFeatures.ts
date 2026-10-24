import type { QuizCollectionSession } from './pendingQuizWrites'
import type { QuizDiagnosticResult, QuizQuestion } from './types'

// Column order from QUIZ_ML_INPUTS in Quiz_ML_Inputs_202_No_Colors.xlsx.
// student_code and concept_id are identifiers excluded by the Colab notebook.
export const ML_FEATURE_COLUMNS = [
  'correct_answers', 'wrong_answers', 'accuracy',
  'beginner_accuracy', 'intermediate_accuracy', 'advanced_accuracy',
  'q01_option_code', 'q02_option_code', 'q03_option_code', 'q04_option_code', 'q05_option_code',
  'q06_option_code', 'q07_option_code', 'q08_option_code', 'q09_option_code', 'q10_option_code',
  'q01_correct', 'q02_correct', 'q03_correct', 'q04_correct', 'q05_correct',
  'q06_correct', 'q07_correct', 'q08_correct', 'q09_correct', 'q10_correct',
  'avg_response_time_sec', 'median_response_time_sec',
  'avg_correct_response_time_sec', 'avg_wrong_response_time_sec',
  'mean_confidence_1to3', 'low_conf_count', 'medium_conf_count', 'high_conf_count',
  'wrong_high_conf_count', 'correct_low_conf_count',
  'inverse_operation_wrong_count', 'sign_error_wrong_count',
  'arithmetic_error_wrong_count', 'concept_confusion_wrong_count',
  'most_frequent_wrong_tag_count', 'repeated_wrong_tag_count',
  'max_consecutive_wrong', 'correct_first5_count', 'correct_last5_count',
] as const

export type MlFeatures = Record<(typeof ML_FEATURE_COLUMNS)[number], number | string | null>

const wrongTags = [
  'inverse_operation', 'sign_error', 'arithmetic_error', 'concept_confusion',
] as const

function requireEvidence(condition: unknown): asserts condition {
  if (!condition) throw new Error('The completed Quiz evidence does not match the training inputs.')
}

// The source responses store seconds to two decimals. The workbook's four-place
// subgroup means reflect rounding a compensated floating-point mean.
function meanSeconds(centiseconds: number[]): number | null {
  if (!centiseconds.length) return null
  let sum = 0
  let correction = 0
  for (const value of centiseconds) {
    const seconds = value / 100
    const next = sum + seconds
    correction += Math.abs(sum) >= Math.abs(seconds)
      ? (sum - next) + seconds : (seconds - next) + sum
    sum = next
  }
  return Number(((sum + correction) / centiseconds.length).toFixed(4))
}

export function buildMlFeatures(
  collection: QuizCollectionSession,
  questions: QuizQuestion[],
  diagnostic: QuizDiagnosticResult,
): MlFeatures {
  const savedSession = collection.session
  const evidence = diagnostic.diagnostic_evidence?.question_evidence
  requireEvidence(collection.completed && savedSession?.status === 'completed')
  requireEvidence(!savedSession.bank_version)
  requireEvidence(savedSession.quiz_session_id === diagnostic.quiz_session_id)
  requireEvidence(savedSession.student_id === collection.request.student_id)
  requireEvidence(savedSession.concept_id === 'linear_equations' && collection.request.concept_id === 'linear_equations')
  requireEvidence(savedSession.assessment_phase === 'pre_tutor' && collection.request.assessment_phase === 'pre_tutor')
  requireEvidence(questions.length === 10 && collection.responses.length === 10 && evidence?.length === 10)
  requireEvidence(diagnostic.questions_total === 10 && diagnostic.questions_attempted === 10)
  requireEvidence(collection.question_ids.length === 10 && new Set(collection.question_ids).size === 10)
  requireEvidence(new Set(evidence.map(row => row.question_order)).size === 10)

  const correct: number[] = []
  const times: number[] = []
  const confidences: number[] = []
  const optionCodes: string[] = []
  const counts: Record<(typeof wrongTags)[number], number> = {
    inverse_operation: 0, sign_error: 0, arithmetic_error: 0, concept_confusion: 0,
  }
  const tierCorrect = { easy: 0, medium: 0, hard: 0 }
  const tierCounts = { easy: 0, medium: 0, hard: 0 }
  let wrongHigh = 0
  let correctLow = 0
  let wrongRun = 0
  let maxWrongRun = 0

  for (let index = 0; index < 10; index += 1) {
    const question = questions[index]
    const write = collection.responses[index]
    const row = evidence[index]
    const answer = write.body
    // This development bank and its order are the source of the training rows.
    requireEvidence(question.question_code === `DEV-PRE-LE-${String(index + 1).padStart(2, '0')}`)
    requireEvidence(question.id === collection.question_ids[index] && answer.question_id === question.id)
    requireEvidence(answer.question_order === index + 1 && row.question_order === index + 1 && row.question_id === question.id)
    requireEvidence(question.concept_id === 'linear_equations' && question.question_type === 'multiple_choice')
    requireEvidence(question.difficulty_level === (index < 4 ? 'easy' : index < 8 ? 'medium' : 'hard'))
    requireEvidence(row.difficulty_level === question.difficulty_level && row.subconcept_code === question.subconcept_code)
    requireEvidence(write.saved && !!write.response_id && typeof write.is_correct === 'boolean')
    requireEvidence(row.is_correct === write.is_correct && row.confidence_level === answer.confidence_level)
    requireEvidence(Number.isFinite(answer.response_time_sec) && answer.response_time_sec >= 0)
    requireEvidence(Math.abs(row.response_time_sec - answer.response_time_sec) < 1e-8)
    const centiseconds = Math.round(answer.response_time_sec * 100)
    requireEvidence(Number.isSafeInteger(centiseconds) && Math.abs(centiseconds / 100 - answer.response_time_sec) < 1e-8)
    requireEvidence(['low', 'medium', 'high'].includes(answer.confidence_level))
    requireEvidence(question.options.length === 4 && new Set(question.options.map(option => option.option_code)).size === 4)
    requireEvidence(question.options.every(option => ['A', 'B', 'C', 'D'].includes(option.option_code)))
    const selected = question.options.find(option => option.id === answer.selected_option_id)
    requireEvidence(selected)
    requireEvidence(write.is_correct ? write.correct_option === null : !!write.correct_option
      && write.correct_option.id !== selected.id
      && question.options.some(option => option.id === write.correct_option?.id))

    const isCorrect = write.is_correct ? 1 : 0
    correct.push(isCorrect)
    times.push(centiseconds)
    optionCodes.push(selected.option_code)
    confidences.push({ low: 1, medium: 2, high: 3 }[answer.confidence_level])
    tierCounts[question.difficulty_level] += 1
    tierCorrect[question.difficulty_level] += isCorrect
    if (isCorrect) {
      requireEvidence(row.misconception_code === null)
      wrongRun = 0
      if (answer.confidence_level === 'low') correctLow += 1
    } else {
      requireEvidence(wrongTags.some(tag => tag === row.misconception_code))
      counts[row.misconception_code as (typeof wrongTags)[number]] += 1
      wrongRun += 1
      maxWrongRun = Math.max(maxWrongRun, wrongRun)
      if (answer.confidence_level === 'high') wrongHigh += 1
    }
  }

  requireEvidence(tierCounts.easy === 4 && tierCounts.medium === 4 && tierCounts.hard === 2)
  const totalCorrect = correct.reduce((sum, value) => sum + value, 0)
  requireEvidence(diagnostic.correct_answers === totalCorrect)
  const wrongCount = 10 - totalCorrect
  const sortedTimes = [...times].sort((left, right) => left - right)
  const correctTimes = times.filter((_, index) => correct[index] === 1)
  const wrongTimes = times.filter((_, index) => correct[index] === 0)
  const tagCounts = wrongTags.map(tag => counts[tag])
  const values: Record<string, number | string | null> = {
    correct_answers: totalCorrect,
    wrong_answers: wrongCount,
    accuracy: totalCorrect / 10,
    beginner_accuracy: tierCorrect.easy / 4,
    intermediate_accuracy: tierCorrect.medium / 4,
    advanced_accuracy: tierCorrect.hard / 2,
  }
  for (let index = 0; index < 10; index += 1) values[`q${String(index + 1).padStart(2, '0')}_option_code`] = optionCodes[index]
  for (let index = 0; index < 10; index += 1) values[`q${String(index + 1).padStart(2, '0')}_correct`] = correct[index]
  Object.assign(values, {
    avg_response_time_sec: meanSeconds(times),
    median_response_time_sec: (sortedTimes[4] + sortedTimes[5]) / 200,
    avg_correct_response_time_sec: meanSeconds(correctTimes),
    avg_wrong_response_time_sec: meanSeconds(wrongTimes),
    mean_confidence_1to3: confidences.reduce((sum, value) => sum + value, 0) / 10,
    low_conf_count: confidences.filter(value => value === 1).length,
    medium_conf_count: confidences.filter(value => value === 2).length,
    high_conf_count: confidences.filter(value => value === 3).length,
    wrong_high_conf_count: wrongHigh,
    correct_low_conf_count: correctLow,
    inverse_operation_wrong_count: counts.inverse_operation,
    sign_error_wrong_count: counts.sign_error,
    arithmetic_error_wrong_count: counts.arithmetic_error,
    concept_confusion_wrong_count: counts.concept_confusion,
    most_frequent_wrong_tag_count: Math.max(...tagCounts),
    repeated_wrong_tag_count: tagCounts.filter(count => count >= 2).reduce((sum, count) => sum + count, 0),
    max_consecutive_wrong: maxWrongRun,
    correct_first5_count: correct.slice(0, 5).reduce((sum, value) => sum + value, 0),
    correct_last5_count: correct.slice(5).reduce((sum, value) => sum + value, 0),
  })
  requireEvidence(ML_FEATURE_COLUMNS.length === 45 && ML_FEATURE_COLUMNS.every(column => values[column] !== undefined))
  return Object.fromEntries(ML_FEATURE_COLUMNS.map(column => [column, values[column]])) as MlFeatures
}
