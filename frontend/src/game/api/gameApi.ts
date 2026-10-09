import type { AssessmentPhase, DifficultyLevel, GameplayEventType } from '../types'
import { gameRequest } from './game'

export interface GameSessionResponse {
  game_session_id: string
  student_id: string
  concept_id: string
  learning_cycle_id: string
  assessment_phase: AssessmentPhase
  status: 'in_progress' | 'completed' | 'abandoned'
  started_at: string
  completed_at: string | null
}

export interface CreateGameSessionInput {
  student_id: string
  concept_id: string
  learning_cycle_id: string
  assessment_phase: AssessmentPhase
}

export function createGameSession(
  input: CreateGameSessionInput,
): Promise<GameSessionResponse> {
  return gameRequest<GameSessionResponse>('sessions', input)
}

export interface SendGameplayEventInput {
  game_session_id: string
  task_id?: string | null
  event_type: GameplayEventType
  event_timestamp: string
  event_payload?: Record<string, unknown>
}

export function sendGameplayEvent(input: SendGameplayEventInput): Promise<unknown> {
  return gameRequest('events', input)
}

export interface SaveTaskAttemptInput {
  game_session_id: string
  task_id: string
  attempt_number?: number
  attempts_count?: number
  wrong_attempts?: number
  hints_used?: number
  skipped_steps?: number
  time_taken_sec?: number
  is_completed?: boolean
  is_successful?: boolean
  score?: number | null
  activity_id?: string | null
  variant_id?: string | null
  difficulty_level?: DifficultyLevel | null
}

export function saveTaskAttempt(input: SaveTaskAttemptInput): Promise<unknown> {
  return gameRequest('task-attempts', input)
}

export function completeGameSession(gameSessionId: string): Promise<GameSessionResponse> {
  // gameRequest only POSTs when a body is passed; the backend route takes
  // no body, so an empty object just forces POST and is otherwise ignored.
  return gameRequest<GameSessionResponse>(`sessions/${gameSessionId}/complete`, {})
}

export interface VariantUsageResponse {
  usage_counts: Record<string, number>
}

// Used once, at the start of a fresh assessment, to apply the "maximum two
// uses" rule (Milestone 3 Step 13) before picking that assessment's 6
// tasks. Unlike the rest of this module, this is awaited rather than
// fire-and-forget — it decides what content to show, not just what to log.
export function getVariantUsage(
  studentId: string,
  conceptId: string,
): Promise<VariantUsageResponse> {
  const query = new URLSearchParams({ student_id: studentId, concept_id: conceptId })
  return gameRequest<VariantUsageResponse>(`variant-usage?${query.toString()}`)
}
