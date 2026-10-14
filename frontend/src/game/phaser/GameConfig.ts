import Phaser from 'phaser'
import { EquationGameScene } from './scenes/EquationGameScene'

// These values are fallbacks while Phaser reads the real container size.
const GAME_WIDTH = 800
const GAME_HEIGHT = 600

// `parent` is the DOM element Phaser should insert its <canvas> into.
export function createGameConfig(parent: HTMLElement): Phaser.Types.Core.GameConfig {
  return {
    type: Phaser.AUTO,
    width: GAME_WIDTH,
    height: GAME_HEIGHT,
    parent,
    backgroundColor: '#ffffff',
    scale: {
      // RESIZE keeps one game pixel equal to one CSS pixel. This prevents
      // touch buttons from becoming tiny when the screen gets narrower.
      mode: Phaser.Scale.RESIZE,
      autoCenter: Phaser.Scale.CENTER_BOTH,
    },
    scene: [EquationGameScene],
  }
}
