import Phaser from 'phaser'
import { EquationGameScene } from './scenes/EquationGameScene'
import { GameSelectionScene } from './scenes/GameSelectionScene'
import { HangmanGameScene } from './scenes/HangmanGameScene'
import { GAME_THEME, cssColor, renderPixelRatio } from './theme/gameTheme'

// These values are fallbacks while Phaser reads the real container size.
const GAME_WIDTH = 800
const GAME_HEIGHT = 600

// `parent` is the DOM element Phaser should insert its <canvas> into.
export function createGameConfig(parent: HTMLElement): Phaser.Types.Core.GameConfig {
  const ratio = renderPixelRatio(window.devicePixelRatio)
  return {
    type: Phaser.AUTO,
    width: Math.round((parent.clientWidth || GAME_WIDTH) * ratio),
    height: Math.round((parent.clientHeight || GAME_HEIGHT) * ratio),
    parent,
    backgroundColor: cssColor(GAME_THEME.color.surface),
    render: { antialias: true, roundPixels: true },
    scale: {
      // Phaser 4 RESIZE writes canvas.width = parent CSS width, ignoring DPR.
      // NONE + explicit resize lets the backing buffer use up to 2x pixels,
      // while inverse scale zoom keeps its displayed size in CSS pixels.
      mode: Phaser.Scale.NONE,
      zoom: 1 / ratio,
      autoRound: true,
      expandParent: false,
    },
    // The first scene listed starts automatically: the Game Selection screen.
    scene: [GameSelectionScene, EquationGameScene, HangmanGameScene],
  }
}
