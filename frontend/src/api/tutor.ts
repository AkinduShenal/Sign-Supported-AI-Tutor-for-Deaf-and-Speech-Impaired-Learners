import type { AdaptiveLesson, LearningLevel, TeachingStrategy, TutorLesson, TutorQuestionAnswer } from '../types/tutor'
import type { TutorLearningStatus } from '../types/tutor'
import type { LearningContext } from '../learningContext'

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
    if (path === 'rag/answer') throw new Error('The question could not be answered. Use the current worked example or try again.')
    if (path.startsWith('learning-status') || path === 'adaptive-lesson/from-results') {
      if (response.status === 404) throw new Error('Complete the Quiz and Game for this learning session, then try again.')
      throw new Error('Your lesson could not be prepared. Please try again or ask your teacher for help.')
    }
    if (response.status === 422) throw new Error('Check the Quiz/Game JSON fields, score ranges, counts and linear-equation concept IDs. The payload must match the existing /tutor/strategy contract.')
    throw new Error(`Tutor request failed (${response.status}). Check that the current backend branch is running.`)
  }
  return response.json() as Promise<T>
}

export function getGrade10Preview(level: LearningLevel, signal?: AbortSignal, strategy: TeachingStrategy = 'step_by_step') {
  return tutorRequest<AdaptiveLesson>(`grade10/${level}?strategy=${encodeURIComponent(strategy)}`, undefined, signal)
}

export function getAdaptiveLesson(payload: unknown, signal?: AbortSignal) {
  return tutorRequest<AdaptiveLesson>('adaptive-lesson', payload, signal)
}

function learningReference(context: LearningContext) {
  return { student_id: context.studentId, learning_cycle_id: context.learningCycleId, concept_id: 'linear_equations' }
}

export function getTutorLearningStatus(context: LearningContext, signal?: AbortSignal) {
  return tutorRequest<TutorLearningStatus>(`learning-status?${new URLSearchParams(learningReference(context))}`, undefined, signal)
}

export function getAutomaticLesson(context: LearningContext, signal?: AbortSignal) {
  return tutorRequest<AdaptiveLesson>('adaptive-lesson/from-results', learningReference(context), signal)
}

export function checkPractice(questionId: string, answer: string) {
  return tutorRequest<{ correct: boolean; feedback: string }>('practice/check', { question_id: questionId, answer })
}

export function askTutorQuestion(question: string, level: LearningLevel, strategy: TeachingStrategy, exampleProblem: string, stepIndex: number, signal?: AbortSignal) {
  return tutorRequest<TutorQuestionAnswer>('rag/answer', {
    question, level, strategy, concept_id: 'linear_equation_balancing',
    example_problem: exampleProblem, step_index: stepIndex,
  }, signal)
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
