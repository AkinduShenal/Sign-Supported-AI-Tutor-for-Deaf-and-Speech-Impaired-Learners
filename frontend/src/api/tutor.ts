import type { AdaptiveLesson, LearningLevel, TutorLesson } from '../types/tutor'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '')

async function tutorRequest<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/tutor/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : JSON.stringify(body), signal,
  })
  if (!response.ok) {
    if (response.status === 422) throw new Error('Check the Quiz/Game JSON fields, score ranges, counts and linear-equation concept IDs. The payload must match the existing /tutor/strategy contract.')
    throw new Error(`Tutor request failed (${response.status}). Check that the current backend branch is running.`)
  }
  return response.json() as Promise<T>
}

export function getGrade10Preview(level: LearningLevel, signal?: AbortSignal) {
  return tutorRequest<AdaptiveLesson>(`grade10/${level}`, undefined, signal)
}

export function getAdaptiveLesson(payload: unknown, signal?: AbortSignal) {
  return tutorRequest<AdaptiveLesson>('adaptive-lesson', payload, signal)
}

export function checkPractice(questionId: string, answer: string) {
  return tutorRequest<{ correct: boolean; feedback: string }>('practice/check', { question_id: questionId, answer })
}

export async function getTutorLesson(
  conceptId: string,
  signal?: AbortSignal,
): Promise<TutorLesson> {
  const response = await fetch(
    `${API_BASE_URL}/tutor/lessons/${encodeURIComponent(conceptId)}`,
    {
      headers: { Accept: 'application/json' },
      signal,
    },
  )

  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? 'This lesson is not available on the connected backend yet.'
        : 'The lesson could not be loaded. Please try again.',
    )
  }

  return (await response.json()) as TutorLesson
}
