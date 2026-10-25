export const GAME_ML_LEVELS = ['Beginner', 'Intermediate', 'Advanced'] as const
export type GameMLLevel = typeof GAME_ML_LEVELS[number]

/** Matches the protected backend PredictionResponse; contains no learner identity. */
export interface GameMLPrediction {
  status: 'experimental_prediction'
  predicted_level: GameMLLevel
  probabilities: Record<GameMLLevel, number>
  model_name: string
  model_version: 'game-ml-experimental-v1'
  model_status: 'EXPERIMENTAL_NOT_PRODUCTION_APPROVED'
  teacher_verified: false
  feature_source: 'validated_saved_game_session'
  feature_contract: 'legacy-nine-feature-observed-single-session-v1'
  model_checksum: string
  model_metadata: Record<string, unknown>
  runtime: { python: string; dependencies: Record<string, string> }
}

export type GameMLPredictionState =
  | { status: 'loading' }
  | { status: 'unavailable' }
  | { status: 'error' }
  | { status: 'ready'; prediction: GameMLPrediction }

const percentage = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 })

/** Display rounding only; the source probability and progress value stay intact. */
export function formatMLProbability(value: number): string {
  return Number.isFinite(value) && value >= 0 && value <= 1 ? percentage.format(value) : 'Unavailable'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Reject incomplete/invalid responses rather than inventing or normalizing values. */
export function isGameMLPrediction(value: unknown): value is GameMLPrediction {
  if (!isRecord(value) || !isRecord(value.probabilities) || !isRecord(value.runtime)) return false
  const probabilities = value.probabilities
  const values = GAME_ML_LEVELS.map(level => probabilities[level])
  return value.status === 'experimental_prediction'
    && GAME_ML_LEVELS.some(level => level === value.predicted_level)
    && Object.keys(probabilities).length === 3
    && values.every(p => typeof p === 'number' && Number.isFinite(p) && p >= 0 && p <= 1)
    && Math.abs((values as number[]).reduce((sum, p) => sum + p, 0) - 1) <= 1e-12
    && typeof value.model_name === 'string' && value.model_name.trim().length > 0
    && value.model_version === 'game-ml-experimental-v1'
    && value.model_status === 'EXPERIMENTAL_NOT_PRODUCTION_APPROVED'
    && value.teacher_verified === false
    && value.feature_source === 'validated_saved_game_session'
    && value.feature_contract === 'legacy-nine-feature-observed-single-session-v1'
    && typeof value.model_checksum === 'string' && /^[a-f0-9]{64}$/.test(value.model_checksum)
    && isRecord(value.model_metadata)
    && typeof value.runtime.python === 'string'
    && isRecord(value.runtime.dependencies)
    && Object.values(value.runtime.dependencies).every(version => typeof version === 'string')
}
