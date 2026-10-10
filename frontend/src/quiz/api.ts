import type { QuizAnswer, QuizAnswerSaved, QuizQuestion, QuizSession, QuizSessionDetail } from './types'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '')

async function quizRequest<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/quiz/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      Accept: 'application/json',
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  if (!response.ok) {
    const details = await response.json().catch(() => null) as { detail?: unknown } | null
    const message = typeof details?.detail === 'string' ? details.detail : null
    throw new Error(message || `Quiz request failed (${response.status}). Please try again.`)
  }
  return response.json() as Promise<T>
}

export function getPreQuizQuestions(signal?: AbortSignal): Promise<QuizQuestion[]> {
  return quizRequest<QuizQuestion[]>(
    'questions?concept_id=linear_equations&assessment_phase=pre_tutor',
    undefined,
    signal,
  )
}

export function createPreQuizSession(studentId: string): Promise<QuizSession> {
  return quizRequest<QuizSession>('sessions', {
    student_id: studentId,
    concept_id: 'linear_equations',
    assessment_phase: 'pre_tutor',
    display_language: 'bilingual',
  })
}

export function getQuizSession(sessionId: string): Promise<QuizSessionDetail> {
  return quizRequest<QuizSessionDetail>(`sessions/${encodeURIComponent(sessionId)}`)
}

export function submitQuizAnswer(sessionId: string, answer: QuizAnswer): Promise<QuizAnswerSaved> {
  return quizRequest<QuizAnswerSaved>(`sessions/${encodeURIComponent(sessionId)}/responses`, answer)
}

export function completeQuizSession(sessionId: string): Promise<QuizSession> {
  return quizRequest<QuizSession>(`sessions/${encodeURIComponent(sessionId)}/complete`, {})
}
