import type { GameType } from './types.ts'

// Registry of the interaction modes the Game Selection screen offers.
//
// GameType is the *interaction mode* only. It is deliberately separate from
// the mathematical identifiers on a question (activityId, concept,
// difficulty, variantId): every mode plays the same questions from
// data/equationVariants.ts.
//
// To add a mode: build its Phaser scene (it receives `{ session }` from
// GameSelectionScene, see session/GameSession.ts), register the scene in
// phaser/GameConfig.ts, then set `sceneKey` and `available: true` here.
export interface GameModeDefinition {
  type: GameType
  // Phaser scene key to start, or null while the mode isn't built yet.
  sceneKey: string | null
  available: boolean
}

export const GAME_MODES: readonly GameModeDefinition[] = [
  { type: 'drag_drop', sceneKey: 'EquationGameScene', available: true },
  { type: 'hangman', sceneKey: 'HangmanGameScene', available: true },
  { type: 'mystery_reveal', sceneKey: null, available: false },
]

export function getGameMode(type: GameType): GameModeDefinition {
  const mode = GAME_MODES.find((candidate) => candidate.type === type)
  if (!mode) throw new Error(`Unknown game type: ${type}`)
  return mode
}
