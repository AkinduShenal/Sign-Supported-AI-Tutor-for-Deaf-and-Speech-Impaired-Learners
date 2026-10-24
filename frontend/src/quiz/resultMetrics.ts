import type { QuizCollectionSession } from './pendingQuizWrites'
import type { ConfidenceLevel, QuizDiagnosticResult, QuizQuestion } from './types'

export interface QuizResultQuestionMetric {
  questionOrder: number
  questionCode: string | null
  isCorrect: boolean
  confidence: ConfidenceLevel
  responseTimeSec: number
  attemptCount: number | null
}

export interface QuizResultMetrics {
  questions: QuizResultQuestionMetric[]
  averageResponseTimeSec: number
  confidenceCounts: Record<ConfidenceLevel, number>
  totalAttempts: number | null
}

export function isDynamicQuizResultSession(
  sessionId: string,
  bankVersion: string | null | undefined,
  collection: QuizCollectionSession | null,
  questions: QuizQuestion[],
): boolean {
  if (bankVersion) return true
  if (collection?.completed === true
    && collection.request.bank_mode === 'dynamic_dev'
    && `QUIZ-${collection.request.client_session_id}` === sessionId) return true
  return questions.length === 10 && questions.every((question, index) =>
    new RegExp(`^PP1-DYN-S${String(index + 1).padStart(2, '0')}-V0[1-6]$`).test(question.question_code))
}

export function buildQuizResultMetrics(
  result: QuizDiagnosticResult,
  questions: QuizQuestion[],
  collection: QuizCollectionSession | null,
): QuizResultMetrics | null {
  const evidence = result.diagnostic_evidence?.question_evidence
  if (!evidence || result.questions_total <= 0 || evidence.length !== result.questions_total
    || result.questions_attempted !== result.questions_total
    || new Set(evidence.map(row => row.question_id)).size !== evidence.length
    || evidence.filter(row => row.is_correct).length !== result.correct_answers) return null

  const ordered = [...evidence].sort((a, b) => a.question_order - b.question_order)
  if (ordered.some((row, index) => row.question_order !== index + 1
    || !Number.isFinite(row.response_time_sec) || row.response_time_sec < 0
    || !['low', 'medium', 'high'].includes(row.confidence_level))) return null

  const questionById = new Map(questions.map(question => [question.id, question]))
  const verifiedCollection = collection?.completed === true
    && `QUIZ-${collection.request.client_session_id}` === result.quiz_session_id
    && collection.question_ids.length === ordered.length
    && collection.responses.length === ordered.length
    && collection.responses.every((write, index) => {
      const row = ordered[index]
      return write.saved && collection.question_ids[index] === row.question_id
        && write.body.question_id === row.question_id
        && write.body.question_order === row.question_order
        && write.body.confidence_level === row.confidence_level
        && Math.abs(write.body.response_time_sec - row.response_time_sec) < 1e-6
        && write.is_correct === row.is_correct
        && (write.practice_attempts?.length ?? 0) <= 2
        && (!row.is_correct || (write.practice_attempts?.length ?? 0) === 0)
    })

  const confidenceCounts: Record<ConfidenceLevel, number> = { low: 0, medium: 0, high: 0 }
  const rows = ordered.map((row, index): QuizResultQuestionMetric => {
    confidenceCounts[row.confidence_level] += 1
    return {
      questionOrder: row.question_order,
      questionCode: questionById.get(row.question_id)?.question_code ?? null,
      isCorrect: row.is_correct,
      confidence: row.confidence_level,
      responseTimeSec: row.response_time_sec,
      attemptCount: verifiedCollection ? 1 + (collection.responses[index].practice_attempts?.length ?? 0) : null,
    }
  })

  return {
    questions: rows,
    averageResponseTimeSec: rows.reduce((sum, row) => sum + row.responseTimeSec, 0) / rows.length,
    confidenceCounts,
    totalAttempts: verifiedCollection ? rows.reduce((sum, row) => sum + row.attemptCount!, 0) : null,
  }
}
