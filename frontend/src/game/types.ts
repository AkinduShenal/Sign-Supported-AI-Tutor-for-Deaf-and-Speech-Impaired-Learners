import type { Localized } from './i18n/language'

export type AssessmentPhase = 'pre_tutor' | 'post_tutor'

// Matches the gameplay_events.event_type vocabulary agreed for the backend contract.
export type GameplayEventType =
  | 'GAME_STARTED'
  | 'GAME_COMPLETED'
  | 'SESSION_ENDED'
  | 'TASK_STARTED'
  | 'TASK_COMPLETED'
  | 'QUESTION_SHOWN'
  | 'ANSWER_SUBMITTED'
  | 'ANSWER_CORRECT'
  | 'ANSWER_INCORRECT'
  | 'HINT_REQUESTED'
  | 'RETRY_STARTED'
  | 'STEP_SKIPPED'

export interface GameplayEvent {
  taskId: string
  eventType: GameplayEventType
  timestamp: string
  payload: Record<string, unknown>
}

export interface OperationChoice {
  id: string
  label: Localized<string>
  isCorrect: boolean
}

// One side of the balance is "<variableLabel> <leftSign> <leftConstant>",
// the other is "rightValue" — e.g. x + 5 = 12.
export interface BalanceTask {
  id: string
  variableLabel: string
  leftSign: '+' | '-'
  leftConstant: number
  rightValue: number
  correctAnswer: number
  operationChoices: OperationChoice[]
  hints: Localized<string>[]
}

export interface TaskAttemptSummary {
  taskId: string
  attemptsCount: number
  wrongAttempts: number
  hintsUsed: number
  skipped: boolean
  isCompleted: boolean
  isSuccessful: boolean
  timeTakenSec: number
}
