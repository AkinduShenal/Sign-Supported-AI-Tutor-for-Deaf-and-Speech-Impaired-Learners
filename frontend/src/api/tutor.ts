import type { TutorLesson } from '../types/tutor'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '')

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
