// Presentation/copy contract only. This is not the repository models' schema.
export const ML_INPUT_NAMES = [
  'first_attempt_accuracy', 'game_success_rate', 'wrong_attempt_count',
  'retry_count', 'total_hint_count', 'skipped_step_count',
  'game_active_time_sec', 'game_hint_rate', 'game_avg_attempts_per_task',
] as const

export type MLInputName = typeof ML_INPUT_NAMES[number]
export type MLInputFeatures = Record<MLInputName, number | null>
export interface MLInputPreview {
  game_session_id: string
  features: MLInputFeatures
  unavailable_reasons: Partial<Record<MLInputName, string>>
  all_features_available: boolean
  ready_for_inference: boolean
  model_compatibility: string
}

// A Phaser presentation event, separate from recorded gameplay events.
export const ML_PREVIEW_EVENT = 'game-results-ml-preview'

export function mlFeaturesForCopy(input?: Partial<Record<MLInputName, unknown>> | null): MLInputFeatures {
  return Object.fromEntries(ML_INPUT_NAMES.map(name => {
    const value = input?.[name]
    const rate = name === 'first_attempt_accuracy' || name === 'game_success_rate' || name === 'game_hint_rate'
    const count = name.endsWith('_count') || name === 'game_active_time_sec'
    const valid = typeof value === 'number' && Number.isFinite(value) && value >= 0
      && (!rate || value <= 1) && (!count || Number.isInteger(value))
    return [name, valid ? value : null]
  })) as MLInputFeatures
}

export function mlFeaturesJson(input?: Partial<Record<MLInputName, unknown>> | null): string {
  // Never use the rounded percentages or .toFixed() strings on the game board.
  return JSON.stringify(mlFeaturesForCopy(input), null, 2)
}

export async function copyMlFeatures(
  input: Partial<Record<MLInputName, unknown>> | null,
  clipboard: Pick<Clipboard, 'writeText'> | undefined,
): Promise<void> {
  if (!clipboard) throw new Error('Clipboard unavailable. Select and copy the JSON below.')
  await clipboard.writeText(mlFeaturesJson(input))
}
