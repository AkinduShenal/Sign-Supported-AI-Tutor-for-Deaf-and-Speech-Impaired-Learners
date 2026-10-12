import Phaser from 'phaser'
import { MAX_WRONG_SUBMISSIONS } from './hangmanLogic'

interface HangmanFigureOptions {
  x: number
  y: number
  // Overall height available for the figure, used to scale the drawing so
  // it fits both the wide and compact layouts.
  height: number
}

// The local design space every coordinate below is written in — ported
// directly from the concept mockup (an HTML canvas prototype reviewed and
// iterated on before this was built), then rendered through this Graphics
// object's own position+scale transform (see the constructor) instead of
// converting every point by hand.
const DESIGN_W = 240
const DESIGN_H = 260

const INK = 0x2b2338
const SKIN = 0xf0b88c
const HAIR = 0x4a3728
const SHIRT = 0xaa3bff
const PANTS = 0x3a3550
const SHOE = 0x241f2e
const MAT_FILL = 0xe4ddf3
const CONFETTI_COLORS = [0xaa3bff, 0xf5b301, 0x0a7a3d, 0xff6b6b, 0x3bb6ff]

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}
function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t)
}

// A person hanging from a fixed bar by both hands (5 fingers each). One
// finger slips per wrong answer; a correct answer never moves the grip,
// only the face (Milestone 4 §7, revised design — see the project's
// hanging-man design discussion). At MAX_WRONG_SUBMISSIONS both hands
// release and the figure falls to a safe, gentle landing — no impact
// effects, no injury (research constraint, Milestone_4 §9/§18). Built with
// Phaser Graphics only, no image assets, an illustrated cartoon style
// rather than a stick figure or anything photorealistic (not achievable in
// vector line-art without images, which this project doesn't use here).
export class HangmanFigure {
  private readonly scene: Phaser.Scene
  private readonly graphics: Phaser.GameObjects.Graphics
  private readonly scale: number
  private fingersLost = 0
  private fallProgress = 0
  private celebrating = false

  constructor(scene: Phaser.Scene, options: HangmanFigureOptions) {
    this.scene = scene
    this.scale = options.height / DESIGN_H
    this.graphics = scene.add.graphics()
    // Local (0,0)..(DESIGN_W,DESIGN_H) now maps onto world space centered
    // horizontally on options.x, with its *bottom* edge at options.y — the
    // scene passes figureBaseY as a ground/floor reference (matching every
    // other layout constant it tunes), not a top-left corner, so the
    // vertical offset has to subtract the full scaled height. Every method
    // below then draws in plain 240x260 local coordinates, same as the
    // reviewed concept mockup.
    this.graphics.setPosition(options.x - (DESIGN_W / 2) * this.scale, options.y - DESIGN_H * this.scale)
    this.graphics.setScale(this.scale)
    this.render()
  }

  // Resting/hanging grip — a fresh question (0) or a wrong-but-not-failing
  // answer (1-9).
  setGrip(fingersLost: number): void {
    this.fingersLost = clamp(fingersLost)
    this.fallProgress = 0
    this.celebrating = false
    this.render()
  }

  // Correct answer: the grip is left exactly as it was (never advances on
  // success — Milestone 4 §7), just a happier face and a brief confetti
  // burst (the "small positive animation" §7 asks for).
  celebrate(fingersLost: number): void {
    this.fingersLost = clamp(fingersLost)
    this.fallProgress = 0
    this.celebrating = true
    this.render()
    this.burstConfetti()
  }

  // Drives the fall. The scene owns the tween and calls this once per
  // frame with progress 0 (just released) .. 1 (settled on the mat) — the
  // same "object exposes a redraw call, the scene's own tween drives it"
  // pattern BalanceScale.tiltTo() already uses in Drag & Drop.
  setFallProgress(progress: number): void {
    this.fallProgress = Math.max(0, Math.min(1, progress))
    this.celebrating = false
    this.render()
  }

  destroy(): void {
    this.graphics.destroy()
  }

  // ---- internals ---------------------------------------------------------

  private render(): void {
    const g = this.graphics
    g.clear()

    const cx = DESIGN_W / 2
    const barY = 46
    const barHalf = 62
    const matY = DESIGN_H - 22

    g.lineStyle(4, INK, 1)
    g.lineBetween(cx - barHalf, barY, cx + barHalf, barY)
    g.lineStyle(3, INK, 1)
    g.lineBetween(cx - barHalf, barY, cx - barHalf, barY - 14)
    g.lineBetween(cx + barHalf, barY, cx + barHalf, barY - 14)

    g.fillStyle(MAT_FILL, 1)
    g.fillEllipse(cx, matY, 148, 20)

    const fingersLost = this.fingersLost
    const settle = this.fallProgress
    const celebrate = this.celebrating

    const sag = (fingersLost / MAX_WRONG_SUBMISSIONS) * 26
    const handY = barY
    const handSpread = 46
    const shoulderYHang = handY + 46 + sag
    // The settled pose needs room below the shoulders for the torso (30),
    // a bent knee segment and a shin down to the mat — see the seated leg
    // constants below, which this must stay in sync with.
    const shoulderYSettled = matY - 66
    const shoulderY = lerp(shoulderYHang, shoulderYSettled, easeOutQuad(settle))
    const bodyCx = cx
    const lean = settle > 0 ? Math.sin(settle * Math.PI) * 10 : 0

    const headR = 15
    const torsoWidth = 30
    const torsoTop = shoulderY
    const torsoBottom = torsoTop + lerp(54, 30, settle)
    const headCx = bodyCx + lean * 0.3
    const headCy = torsoTop - headR + 6 + lean * 0.2
    const shoulderJointY = torsoTop + 8

    // Torso first, as the body's base shape — arms and head are layered on
    // top so their joints blend into its edges instead of floating beside
    // them (a filled rounded rect, not a thick capped line: a round cap
    // bulges past its own endpoint, which is what let an earlier version
    // of this cover the chin).
    this.filledRoundRect(bodyCx + lean * 0.2, torsoTop, torsoBottom, torsoWidth, 10, SHIRT)

    if (settle < 0.02) {
      ;[-1, 1].forEach((side) => {
        const handX = cx + side * handSpread
        const shoulderX = bodyCx + lean * 0.2 + side * (torsoWidth / 2 - 4)
        this.fillCapsule(handX, handY, shoulderX, shoulderJointY, 6, SKIN)
        this.drawHand(handX, handY, side, fingersLost)
      })
    } else {
      ;[-1, 1].forEach((side) => {
        const shoulderX = bodyCx + lean * 0.2 + side * (torsoWidth / 2 - 4)
        this.fillCapsule(
          shoulderX,
          shoulderJointY,
          bodyCx + lean * 0.15 + side * 18,
          torsoTop + 34,
          5,
          SKIN,
        )
      })
    }

    this.filledCircle(headCx, headCy, headR, SKIN)
    g.fillStyle(HAIR, 1)
    g.beginPath()
    g.moveTo(headCx - headR, headCy - 2)
    g.arc(headCx, headCy, headR + 1, Math.PI * 1.12, Math.PI * 1.88, false)
    g.closePath()
    g.fillPath()
    this.drawFace(headCx, headCy, fingersLost, settle, celebrate)

    // Legs: dangling while hanging, bent and seated once settled.
    ;[-1, 1].forEach((side) => {
      const hipX = bodyCx + lean * 0.15
      let footX: number
      let footY: number
      if (settle < 0.5) {
        const legLen = lerp(46, 20, settle * 2 <= 1 ? settle * 2 : 1)
        footX = hipX + side * 10
        footY = torsoBottom + legLen
        this.fillCapsule(hipX, torsoBottom, footX, footY, 5.5, PANTS)
      } else {
        // Seated-pose leg lengths — change these two numbers to make the
        // legs longer/shorter after the fall (and keep shoulderYSettled
        // above in sync so the feet still land on the mat).
        const SEATED_THIGH_LEN = 14
        const SEATED_SHIN_LEN = 16
        const kneeX = bodyCx + lean * 0.1 + side * 22
        const kneeY = torsoBottom + SEATED_THIGH_LEN
        footX = kneeX + side * 4
        footY = kneeY + SEATED_SHIN_LEN
        this.fillCapsule(hipX, torsoBottom, kneeX, kneeY, 5.5, PANTS)
        this.fillCapsule(kneeX, kneeY, footX, footY, 5, PANTS)
      }
      this.filledFoot(footX, footY, side)
    })

    if (settle > 0.05 && settle < 0.95) {
      // A couple of short motion lines while actually falling, nothing more.
      g.lineStyle(2, INK, 0.35 * Math.sin(settle * Math.PI))
      ;[-10, 10].forEach((dx) => {
        g.lineBetween(bodyCx + dx, shoulderY - 20, bodyCx + dx, shoulderY - 4)
      })
    }
  }

  private drawHand(x: number, y: number, side: number, fingersLost: number): void {
    // 5 fingers per hand, curled over the bar. Fingers are lost alternately
    // right-hand-first; side -1 = left hand, side 1 = right hand.
    const order: Array<{ side: number; i: number }> = []
    for (let i = 0; i < 5; i += 1) {
      order.push({ side: 1, i })
      order.push({ side: -1, i })
    }
    const lostSet = new Set(order.slice(0, fingersLost).map((f) => `${f.side}:${f.i}`))

    this.filledCircle(x, y + 8, 7, SKIN)
    for (let i = 0; i < 5; i += 1) {
      if (lostSet.has(`${side}:${i}`)) continue
      const spread = (i - 2) * 4.2
      this.fillCapsule(x + spread, y + 4, x + spread * 0.6, y - 6, 2.5, SKIN)
    }
  }

  // Three discrete cartoon expressions plus a neutral/strained default,
  // picked by state rather than blended — strained while hanging (eyebrows
  // tilt and the mouth tightens as fingers run out), surprised for the
  // brief mid-fall moment, gently sad once settled (failing isn't a good
  // outcome, so this reads as "aww, missed it" rather than relief, while
  // staying mild — no tears, no exaggeration, same reason the fall itself
  // has no impact effects), and happy on a correct answer at any point.
  private drawFace(
    headCx: number,
    headCy: number,
    fingersLost: number,
    settle: number,
    celebrate: boolean,
  ): void {
    if (settle > 0.05 && settle < 0.95) {
      this.drawSurprisedFace(headCx, headCy)
      return
    }
    if (settle >= 0.95) {
      this.drawSadFace(headCx, headCy)
      return
    }
    if (celebrate) {
      this.drawHappyFace(headCx, headCy)
      return
    }
    this.drawStrainFace(headCx, headCy, Math.min(1, fingersLost / MAX_WRONG_SUBMISSIONS))
  }

  private drawStrainFace(headCx: number, headCy: number, strain: number): void {
    const g = this.graphics
    ;[-1, 1].forEach((side) => {
      const ex = headCx + side * 5
      g.fillStyle(INK, 1)
      g.fillCircle(ex, headCy + 1, 1.6)
      // Eyebrow: tilts slightly inward/down as the grip gets harder to
      // hold — a small "working at it" cue, never a pained expression.
      const tilt = strain * 3
      g.lineStyle(1.6, INK, 1)
      g.lineBetween(ex - side * 3, headCy - 5 - tilt * side, ex + side * 3, headCy - 6 + tilt * side)
    })
    // Mouth: a flat neutral line at low strain, growing into a small open
    // "effort" oval as wrong answers add up — cartoon exertion, not pain.
    const mouthW = lerp(8, 6, strain)
    const mouthH = lerp(0, 5, strain)
    if (mouthH < 0.6) {
      g.lineStyle(1.6, INK, 1)
      g.lineBetween(headCx - mouthW / 2, headCy + 7, headCx + mouthW / 2, headCy + 7)
    } else {
      g.fillStyle(INK, 1)
      g.fillEllipse(headCx, headCy + 7, mouthW, mouthH)
    }
  }

  private drawSurprisedFace(headCx: number, headCy: number): void {
    const g = this.graphics
    ;[-1, 1].forEach((side) => {
      const ex = headCx + side * 5
      g.fillStyle(0xffffff, 1)
      g.fillCircle(ex, headCy, 3.4)
      g.lineStyle(1.2, INK, 1)
      g.strokeCircle(ex, headCy, 3.4)
      g.fillStyle(INK, 1)
      g.fillCircle(ex, headCy, 1.5)
    })
    g.fillStyle(INK, 1)
    g.fillEllipse(headCx, headCy + 8, 6.4, 8.4)
  }

  private drawSadFace(headCx: number, headCy: number): void {
    const g = this.graphics
    ;[-1, 1].forEach((side) => {
      const ex = headCx + side * 5
      g.fillStyle(INK, 1)
      g.fillCircle(ex, headCy + 1, 1.6)
      // Eyebrows: inner corner raised, outer corner low — the classic
      // gentle "sad" tilt, mirrored left/right.
      g.lineStyle(1.6, INK, 1)
      g.lineBetween(ex - side * 3, headCy - 7, ex + side * 3, headCy - 4)
    })
    // Mouth: a small downward curve — a mild frown, not a cry.
    g.lineStyle(1.6, INK, 1)
    g.beginPath()
    g.arc(headCx, headCy + 12, 4, Math.PI * 1.15, Math.PI * 1.85, false)
    g.strokePath()
  }

  private drawHappyFace(headCx: number, headCy: number): void {
    const g = this.graphics
    g.lineStyle(1.6, INK, 1)
    ;[-1, 1].forEach((side) => {
      const ex = headCx + side * 5
      // Closed, upward-curved eyes — reads as a genuine grin rather than
      // the neutral dot eyes the other expressions use.
      g.beginPath()
      g.arc(ex, headCy + 1, 2.2, Math.PI, 0, false)
      g.strokePath()
    })
    g.beginPath()
    g.arc(headCx, headCy + 4, 4.6, Math.PI * 0.1, Math.PI * 0.9, false)
    g.strokePath()
  }

  // ---- shape helpers -------------------------------------------------
  // Every "capsule" (limb/finger) is a dark outline capsule filled with a
  // narrower colored one on top, built from two circles (true rounded
  // caps, not a line-cap approximation) plus a filled quad between them —
  // Phaser Graphics has no native round line-cap, so this is the faithful
  // equivalent rather than a workaround.

  private fillCapsule(x1: number, y1: number, x2: number, y2: number, r: number, color: number): void {
    this.fillCapsuleShape(x1, y1, x2, y2, r + 1.5, INK)
    this.fillCapsuleShape(x1, y1, x2, y2, r, color)
  }

  private fillCapsuleShape(x1: number, y1: number, x2: number, y2: number, r: number, color: number): void {
    const g = this.graphics
    const angle = Math.atan2(y2 - y1, x2 - x1)
    const nx = Math.cos(angle + Math.PI / 2) * r
    const ny = Math.sin(angle + Math.PI / 2) * r
    g.fillStyle(color, 1)
    g.fillPoints(
      [
        new Phaser.Math.Vector2(x1 + nx, y1 + ny),
        new Phaser.Math.Vector2(x2 + nx, y2 + ny),
        new Phaser.Math.Vector2(x2 - nx, y2 - ny),
        new Phaser.Math.Vector2(x1 - nx, y1 - ny),
      ],
      true,
    )
    g.fillCircle(x1, y1, r)
    g.fillCircle(x2, y2, r)
  }

  private filledCircle(x: number, y: number, r: number, color: number): void {
    const g = this.graphics
    g.fillStyle(INK, 1)
    g.fillCircle(x, y, r + 1.5)
    g.fillStyle(color, 1)
    g.fillCircle(x, y, r)
  }

  private filledRoundRect(
    cx: number,
    yTop: number,
    yBottom: number,
    width: number,
    radius: number,
    color: number,
  ): void {
    const g = this.graphics
    const h = yBottom - yTop
    g.fillStyle(INK, 1)
    g.fillRoundedRect(cx - width / 2 - 1.5, yTop - 1.5, width + 3, h + 3, radius + 1.5)
    g.fillStyle(color, 1)
    g.fillRoundedRect(cx - width / 2, yTop, width, h, radius)
  }

  private filledFoot(x: number, y: number, side: number): void {
    const g = this.graphics
    g.fillStyle(INK, 1)
    g.fillEllipse(x + side * 4, y, 22, 12)
    g.fillStyle(SHOE, 1)
    g.fillEllipse(x + side * 4, y, 18, 9)
  }

  // ---- celebration burst -----------------------------------------------

  // A handful of small bursting dots above the figure's head — the "small
  // positive animation" Milestone 4 §7 asks for on a correct answer. These
  // are real, short-lived GameObjects (not part of the Graphics path),
  // positioned in world space, so they fade and self-destroy independently
  // of the next render().
  private burstConfetti(): void {
    const headCx = DESIGN_W / 2
    // Matches the celebrate-state head position computed in render() with
    // settle=0, lean=0 (celebration never happens mid-fall).
    const sag = (this.fingersLost / MAX_WRONG_SUBMISSIONS) * 26
    const shoulderY = 46 + 46 + sag
    const headR = 15
    const headCy = shoulderY - headR + 6
    const origin = this.toWorld(headCx, headCy)

    const count = 8
    for (let i = 0; i < count; i += 1) {
      const angle = (i / count) * Math.PI * 2 + 0.3
      const dist = (10 + Math.random() * 10) * this.scale
      const dot = this.scene.add.circle(
        origin.x,
        origin.y,
        3.2 * this.scale,
        CONFETTI_COLORS[i % CONFETTI_COLORS.length],
      )
      this.scene.tweens.add({
        targets: dot,
        x: origin.x + Math.cos(angle) * (dist + 46 * this.scale),
        y: origin.y + Math.sin(angle) * (dist + 46 * this.scale) * 0.7 - 14 * this.scale,
        alpha: 0,
        duration: 700,
        ease: 'Quad.easeOut',
        onComplete: () => dot.destroy(),
      })
    }
  }

  private toWorld(localX: number, localY: number): { x: number; y: number } {
    return {
      x: this.graphics.x + localX * this.scale,
      y: this.graphics.y + localY * this.scale,
    }
  }
}

function clamp(fingersLost: number): number {
  return Math.max(0, Math.min(MAX_WRONG_SUBMISSIONS, Math.round(fingersLost)))
}
