import Phaser from 'phaser'
import type { DesignSize } from '../viewport'
import { prefersReducedMotion } from '../viewport'
import { GAME_THEME as T } from './gameTheme'

export type BackdropKind = keyof typeof T.backdrop

// Drawn far past the design edges so any letterbox (a resize that only
// refits the camera, or full screen on an unusual aspect ratio) still shows
// the game world instead of a blank strip.
const BLEED = 1600
const BACK_DEPTH = -1000

// A soft, decorative game world behind every Game scene: a sky gradient,
// rolling hills, drifting clouds and faint maths symbols. Purely visual: no
// text, no input, never on top of content. Clouds and symbols drift slowly
// and stop entirely under prefers-reduced-motion.
export function drawBackdrop(scene: Phaser.Scene, size: DesignSize, kind: BackdropKind): void {
  const palette = T.backdrop[kind]
  const { width, height } = size
  const left = -BLEED
  const right = width + BLEED
  const reduced = prefersReducedMotion()

  const sky = scene.add.graphics().setDepth(BACK_DEPTH)
  // Banded gradient: works identically on Canvas and WebGL renderers.
  const bands = 36
  const top = Phaser.Display.Color.IntegerToColor(palette.top)
  const bottom = Phaser.Display.Color.IntegerToColor(palette.bottom)
  sky.fillStyle(palette.top, 1).fillRect(left, -BLEED, right - left, BLEED)
  for (let i = 0; i < bands; i += 1) {
    const mixed = Phaser.Display.Color.Interpolate.ColorWithColor(top, bottom, bands - 1, i)
    sky.fillStyle(Phaser.Display.Color.GetColor(mixed.r, mixed.g, mixed.b), 1)
    sky.fillRect(left, (height * i) / bands, right - left, height / bands + 1)
  }
  sky.fillStyle(palette.bottom, 1).fillRect(left, height, right - left, BLEED)

  // A soft sun glow, top right.
  sky.fillStyle(0xffffff, 0.35).fillCircle(width * 0.86, height * 0.1, 90)
  sky.fillStyle(0xffffff, 0.25).fillCircle(width * 0.86, height * 0.1, 140)

  // Two layers of rolling hills along the bottom.
  const hills = scene.add.graphics().setDepth(BACK_DEPTH + 1)
  hills.fillStyle(palette.hillFar, 1)
  for (let x = left; x < right; x += 260) hills.fillEllipse(x, height - 40, 420, 190)
  hills.fillRect(left, height - 40, right - left, BLEED)
  hills.fillStyle(palette.hill, 1)
  for (let x = left + 130; x < right; x += 300) hills.fillEllipse(x, height + 10, 480, 170)
  hills.fillRect(left, height + 10, right - left, BLEED)

  for (let i = 0; i < 5; i += 1) {
    const cloud = drawCloud(scene, 0.7 + (i % 3) * 0.18)
    const y = height * (0.06 + ((i * 37) % 30) / 100)
    const startX = ((i * 0.23) % 1) * (width + 400) - 200
    cloud.setPosition(startX, y)
    if (!reduced) {
      const travel = width + 600
      const speed = 9 + (i % 3) * 4 // design px per second: a slow drift
      const firstLeg = ((width + 300 - startX) / speed) * 1000
      scene.tweens.add({
        targets: cloud, x: width + 300, duration: firstLeg, ease: 'Linear',
        onComplete: () => {
          cloud.x = -300
          scene.tweens.add({ targets: cloud, x: width + 300, duration: (travel / speed) * 1000, ease: 'Linear', repeat: -1 })
        },
      })
    }
  }

  drawSymbols(scene, size, reduced)
}

function drawCloud(scene: Phaser.Scene, scale: number): Phaser.GameObjects.Graphics {
  const g = scene.add.graphics().setDepth(BACK_DEPTH + 2)
  g.fillStyle(0xffffff, 0.75)
  g.fillCircle(0, 0, 26 * scale)
  g.fillCircle(28 * scale, -10 * scale, 32 * scale)
  g.fillCircle(60 * scale, 0, 24 * scale)
  g.fillRoundedRect(-24 * scale, 0, 108 * scale, 24 * scale, 12 * scale)
  return g
}

// Faint + − × ÷ = shapes scattered around the edges, drawn as strokes (not
// Text) so they never compete with real equations or interfere with tests
// that look up controls by their labels.
function drawSymbols(scene: Phaser.Scene, size: DesignSize, reduced: boolean): void {
  const kinds = ['plus', 'minus', 'times', 'divide', 'equals'] as const
  const spots = [
    [0.05, 0.3], [0.95, 0.42], [0.08, 0.72], [0.93, 0.8], [0.03, 0.52], [0.97, 0.18], [0.5, 0.97],
  ]
  spots.forEach(([fx, fy], i) => {
    const g = scene.add.graphics({ x: size.width * fx, y: size.height * fy }).setDepth(BACK_DEPTH + 3)
    g.lineStyle(5, T.color.primary, 0.12)
    const r = 13
    switch (kinds[i % kinds.length]) {
      case 'plus': g.lineBetween(-r, 0, r, 0).lineBetween(0, -r, 0, r); break
      case 'minus': g.lineBetween(-r, 0, r, 0); break
      case 'times': g.lineBetween(-r * 0.75, -r * 0.75, r * 0.75, r * 0.75).lineBetween(-r * 0.75, r * 0.75, r * 0.75, -r * 0.75); break
      case 'divide':
        g.lineBetween(-r, 0, r, 0)
        g.fillStyle(T.color.primary, 0.12).fillCircle(0, -r * 0.65, 3.5).fillCircle(0, r * 0.65, 3.5)
        break
      case 'equals': g.lineBetween(-r, -5, r, -5).lineBetween(-r, 5, r, 5); break
    }
    if (!reduced) {
      scene.tweens.add({
        targets: g, y: g.y - 10, angle: i % 2 === 0 ? 8 : -8,
        duration: 2600 + i * 310, yoyo: true, repeat: -1, ease: 'Sine.easeInOut',
      })
    }
  })
}
