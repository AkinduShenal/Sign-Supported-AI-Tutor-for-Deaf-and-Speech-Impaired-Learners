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

// The calculated Game Analytics result (Milestone 3 Steps 15-19). The
// frontend never computes any of these rates itself — they always come
// from here. Mirrors backend/app/modules/game/schemas.py::GameResultResponse.
export interface GameResultResponse {
  game_session_id: string
  student_id: string
  concept_id: string
  learning_cycle_id: string | null
  assessment_phase: AssessmentPhase | null
  tasks_total: number
  tasks_attempted: number
  tasks_completed: number
  successful_tasks: number
  game_success_rate: number
  game_completion_rate: number
  game_avg_attempts_per_task: number
  game_hint_rate: number
  game_difficulty_level: string
  game_active_time_sec: number
  wrong_attempt_count: number
  retry_count: number
  total_hint_count: number
  skipped_step_count: number
  // Prototype heuristic indicators — not a trained model's output (see
  // model_version, e.g. "game-heuristic-v1").
  engagement_level: string
  behavioral_difficulty: string
  hint_dependency: number
  game_mastery_score: number
  game_mastery_level: string | null
  game_engagement_level: string | null
  hint_dependency_level: string | null
  model_version: string | null
  completed_at: string
}

// Only meaningful once the backend has decided the assessment is complete
// (2 Easy + 2 Medium + 2 Hard tasks processed — Milestone 3 Step 16) and
// created the game_results row as a side effect of completing the session
// (Step 17). Throws (404) if that hasn't happened yet.
export function fetchGameResult(gameSessionId: string): Promise<GameResultResponse> {
  return gameRequest<GameResultResponse>(`results/${gameSessionId}`)
}
