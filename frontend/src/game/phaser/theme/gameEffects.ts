import Phaser from 'phaser'
import { FONT_FAMILY, SINHALA_TEXT, inline } from '../gameText'
import type { Bilingual } from '../gameText'
import { prefersReducedMotion } from '../viewport'
import { GAME_THEME as T, cssColor } from './gameTheme'
import { RoundedPanel, bindLanguageText } from './gameUi'

// Reusable, visual-only game feedback shared by every Game scene. None of
// these touch gameplay state, input or analytics, and none block input:
// they are short-lived decorations that destroy themselves. Every effect
// has a reduced-motion path (nothing moves; at most a static badge shows
// briefly), and none rely on sound — this tutor is non-audio by design.

const EFFECT_DEPTH = 900

type Point = { x: number; y: number }

// A celebratory burst of paper confetti that arcs up and drifts down under
// gravity. Decorative only, so it is skipped entirely under reduced motion.
export function confettiBurst(scene: Phaser.Scene, x: number, y: number, options: { count?: number; power?: number } = {}): void {
  if (prefersReducedMotion()) return
  const count = options.count ?? 40
  const power = options.power ?? 420
  const gravity = 900
  for (let i = 0; i < count; i += 1) {
    const color = T.confetti[i % T.confetti.length]
    const piece = i % 3 === 0
      ? scene.add.circle(x, y, 4.5, color)
      : scene.add.rectangle(x, y, 9, 14, color)
    piece.setDepth(EFFECT_DEPTH).setRotation(Math.random() * Math.PI)
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.15
    const speed = power * (0.45 + Math.random() * 0.65)
    const vx = Math.cos(angle) * speed
    const vy = Math.sin(angle) * speed
    const spin = (Math.random() - 0.5) * 14
    const flutter = 6 + Math.random() * 6
    const life = 1.5 + Math.random() * 0.7
    scene.tweens.addCounter({
      from: 0, to: life, duration: life * 1000,
      onUpdate: (tween) => {
        const t = tween.getValue() ?? 0
        // Air drag caps the fall speed so pieces float rather than plummet.
        piece.x = x + vx * t * 0.8 + Math.sin(t * flutter) * 10
        piece.y = y + vy * t + 0.5 * gravity * t * t * 0.55
        piece.rotation += spin * 0.016
        piece.scaleX = Math.cos(t * flutter * 1.3)
        piece.alpha = t > life * 0.7 ? 1 - (t - life * 0.7) / (life * 0.3) : 1
      },
      onComplete: () => piece.destroy(),
    })
  }
}

// A round ✓ (green) or ✕ (red) badge that pops in, holds, then floats away.
// Drawn with Graphics rather than Text, and the shape (not only the colour)
// carries the meaning.
export function popBadge(scene: Phaser.Scene, x: number, y: number, kind: 'correct' | 'wrong', size = 56): void {
  const g = scene.add.graphics()
  const r = size / 2
  const fill = kind === 'correct' ? T.color.success : T.color.error
  g.fillStyle(T.color.shadow, 0.12).fillCircle(0, 4, r)
  g.fillStyle(0xffffff, 1).fillCircle(0, 0, r + 4)
  g.fillStyle(fill, 1).fillCircle(0, 0, r)
  g.lineStyle(size * 0.12, 0xffffff, 1)
  if (kind === 'correct') {
    g.beginPath()
    g.moveTo(-r * 0.45, 0)
    g.lineTo(-r * 0.1, r * 0.36)
    g.lineTo(r * 0.5, -r * 0.34)
    g.strokePath()
  } else {
    g.lineBetween(-r * 0.36, -r * 0.36, r * 0.36, r * 0.36)
    g.lineBetween(-r * 0.36, r * 0.36, r * 0.36, -r * 0.36)
  }
  const badge = scene.add.container(x, y, [g]).setDepth(EFFECT_DEPTH)
  if (prefersReducedMotion()) {
    scene.time.delayedCall(900, () => badge.destroy())
    return
  }
  badge.setScale(0.2).setAlpha(0)
  scene.tweens.add({ targets: badge, scale: 1, alpha: 1, duration: 280, ease: 'Back.easeOut' })
  if (kind === 'wrong') {
    scene.tweens.add({ targets: badge, angle: { from: -14, to: 14 }, duration: 70, yoyo: true, repeat: 2, delay: 260 })
  }
  scene.tweens.add({
    targets: badge, y: y - 36, alpha: 0, duration: 360, delay: 900, ease: 'Quad.easeIn',
    onComplete: () => badge.destroy(),
  })
}

// A gold star that flies along an arc from one point to another (e.g. from
// the solved question to its node in the progress path), then calls back so
// the scene can redraw the path with the newly earned stars.
export function flyStar(scene: Phaser.Scene, from: Point, to: Point, onArrive: () => void, delay = 0): void {
  if (prefersReducedMotion()) {
    onArrive()
    return
  }
  const star = scene.add.graphics().setDepth(EFFECT_DEPTH + 1)
  star.fillStyle(T.color.gold, 1)
  star.lineStyle(3, 0xffffff, 1)
  const points = starPoints(18, 8)
  star.fillPoints(points, true)
  star.strokePoints(points, true)
  star.setPosition(from.x, from.y).setScale(0.3)
  const lift = Math.max(80, Math.abs(to.y - from.y) * 0.4)
  scene.tweens.addCounter({
    from: 0, to: 1, duration: 750, delay, ease: 'Sine.easeInOut',
    onUpdate: (tween) => {
      const t = tween.getValue() ?? 0
      star.x = from.x + (to.x - from.x) * t
      star.y = from.y + (to.y - from.y) * t - Math.sin(Math.PI * t) * lift
      star.setScale(0.3 + Math.sin(Math.PI * Math.min(1, t * 1.4)) * 1.1 + (1 - t) * 0.1)
      star.rotation = t * Math.PI * 2
    },
    onComplete: () => {
      star.destroy()
      ring(scene, to.x, to.y, T.color.gold)
      onArrive()
    },
  })
}

// An expanding ring, used where something "lands".
export function ring(scene: Phaser.Scene, x: number, y: number, color: number): void {
  if (prefersReducedMotion()) return
  const circle = scene.add.circle(x, y, 14).setStrokeStyle(4, color).setDepth(EFFECT_DEPTH)
  scene.tweens.add({ targets: circle, scale: 2.4, alpha: 0, duration: 450, ease: 'Quad.easeOut', onComplete: () => circle.destroy() })
}

// A quick side-to-side shake of one or more objects, returning each to the
// exact x it started from (safe to call repeatedly).
export function shake(scene: Phaser.Scene, targets: Array<Phaser.GameObjects.GameObject & { x: number }>, amplitude = 9): void {
  if (prefersReducedMotion()) return
  targets.forEach((target) => {
    const base = (target.getData('shakeBaseX') as number | undefined) ?? target.x
    target.setData('shakeBaseX', base)
    const existing = target.getData('shakeTween') as Phaser.Tweens.Tween | undefined
    existing?.stop()
    target.x = base
    const tween = scene.tweens.addCounter({
      from: 0, to: 1, duration: 380, ease: 'Linear',
      onUpdate: (tw) => {
        const t = tw.getValue() ?? 0
        target.x = base + Math.sin(t * Math.PI * 6) * amplitude * (1 - t)
      },
      onComplete: () => { target.x = base },
      onStop: () => { target.x = base },
    })
    target.setData('shakeTween', tween)
  })
}

// A small scale "pop" (grow and settle back).
export function pulse(scene: Phaser.Scene, target: Phaser.GameObjects.GameObject & { scale: number }, amount = 1.12): void {
  if (prefersReducedMotion()) return
  scene.tweens.add({ targets: target, scale: amount, duration: 140, yoyo: true, ease: 'Quad.easeOut' })
}

// A ribbon that announces the next level ("Level 3 · Medium") and gets out
// of the way. Non-interactive, so it never blocks a tap underneath.
export function levelBanner(scene: Phaser.Scene, x: number, y: number, text: Bilingual): void {
  const label = scene.add.text(0, 0, '', {
    fontFamily: FONT_FAMILY, fontSize: '22px', fontStyle: 'bold', color: cssColor(0xffffff), align: 'center',
    ...SINHALA_TEXT, padding: { top: 2, bottom: 2 },
  }).setOrigin(0.5)
  bindLanguageText(label, () => inline(text))
  const width = Math.max(240, label.width + 56)
  const height = 54
  const shadow = new RoundedPanel(scene, 0, 5, width, height, T.color.shadow, T.color.shadow, height / 2)
  shadow.setFillStyle(T.color.shadow, 0.16).setStrokeStyle(0, T.color.shadow)
  const plate = new RoundedPanel(scene, 0, 0, width, height, T.color.primary, 0xffffff, height / 2)
  plate.setStrokeStyle(3, 0xffffff)
  const banner = scene.add.container(x, y, [shadow, plate, label]).setDepth(EFFECT_DEPTH + 2)
  if (prefersReducedMotion()) {
    scene.time.delayedCall(1000, () => banner.destroy())
    return
  }
  banner.setScale(0.5).setAlpha(0)
  scene.tweens.add({ targets: banner, scale: 1, alpha: 1, duration: 320, ease: 'Back.easeOut' })
  scene.tweens.add({
    targets: banner, alpha: 0, scale: 0.9, y: y - 20, duration: 300, delay: 1150, ease: 'Quad.easeIn',
    onComplete: () => banner.destroy(),
  })
}

export function starPoints(outer: number, inner: number): Phaser.Math.Vector2[] {
  const points: Phaser.Math.Vector2[] = []
  for (let i = 0; i < 10; i += 1) {
    const r = i % 2 === 0 ? outer : inner
    const a = -Math.PI / 2 + (i * Math.PI) / 5
    points.push(new Phaser.Math.Vector2(Math.cos(a) * r, Math.sin(a) * r))
  }
  return points
}
