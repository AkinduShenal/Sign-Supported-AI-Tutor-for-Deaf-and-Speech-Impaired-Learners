import Phaser from 'phaser'
import { MAX_WRONG_SUBMISSIONS } from './hangmanLogic'
import { prefersReducedMotion } from './viewport'
import { confettiBurst } from './theme/gameEffects'

interface HangmanFigureOptions {
  x: number
  y: number
  // Overall height available for the figure, used to scale the drawing so
  // it fits both the wide and compact layouts.
  height: number
}

// The local design space every coordinate below is written in. The
// Graphics object's own position+scale transform maps it into the scene.
const DESIGN_W = 300
const DESIGN_H = 300

const INK = 0x2b2338
const SKIN = 0xf0b88c
const SKIN_SHADE = 0xe0a273
const HAIR = 0x4a3728
const SHIRT = 0x6a4cf0
const SHIRT_LIGHT = 0x8a73ff
const PANTS = 0x34406b
const SHOE = 0x241f2e
const SOLE = 0xffffff
const STEEL = 0x8f98bd
const STEEL_LIGHT = 0xc9cfe6
const MAT = 0x4f86e8
const MAT_TOP = 0x7fa8f2
const SWEAT = 0x7cc6ff

const CX = DESIGN_W / 2
const BAR_Y = 52
const POST_X = 112
const FLOOR_Y = DESIGN_H - 14
const MAT_W = 210
const MAT_H = 28
const MAT_TOP_Y = FLOOR_Y - MAT_H
const HAND_SPREAD = 44
const SHOULDER_HALF = 13
// Shoulder centre below the hands while hanging with a full grip.
const ARM_REACH = 42

// Finger ids on each hand: 0 index, 1 middle, 2 ring, 3 little, 4 thumb.
export const FINGER = { index: 0, middle: 1, ring: 2, little: 3, thumb: 4 } as const

// A realistic loss of grip: on each hand the thumb goes first, then the
// little, ring and middle fingers, and the index finger holds on longest.
// Hands alternate, right hand first, so neither hand lets go before the
// other is also down to its last fingers.
const PER_HAND_ORDER = [FINGER.thumb, FINGER.little, FINGER.ring, FINGER.middle, FINGER.index]
const SLIP_ORDER: Array<{ side: number; finger: number }> = []
for (const finger of PER_HAND_ORDER) {
  SLIP_ORDER.push({ side: 1, finger })
  SLIP_ORDER.push({ side: -1, finger })
}

// Which wrong answer (0-based) slips this finger — shared with the grip
// meter in HangmanGameScene so the two always agree.
export function slipOrderIndex(side: number, finger: number): number {
  return SLIP_ORDER.findIndex((f) => f.side === side && f.finger === finger)
}

const SLIP_SECONDS = 0.55
const RELEASE_SECONDS = 0.4
const CHEER_SECONDS = 1.5
const SURPRISE_SECONDS = 0.75

type Vec = { x: number; y: number }

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}
function clamp01(t: number): number {
  return Math.max(0, Math.min(1, t))
}
function easeOutBack(t: number): number {
  const c = 1.9
  return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2)
}
function easeInQuad(t: number): number {
  return t * t
}

// A cartoon gymnast hanging from a gym bar by both hands (5 fingers each),
// above a soft crash mat. One finger visibly slips off the bar per wrong
// answer — it uncurls, flicks open and the hand jolts while the body swings
// — and a correct answer never changes the grip, only celebrates with
// pull-ups (Milestone 4 §7). At MAX_WRONG_SUBMISSIONS both hands let go and
// the figure drops onto the mat, which squashes like a cushion: no impact
// effects and no injury (research constraint, Milestone_4 §9/§18).
//
// Procedural animation: the whole figure is redrawn every frame from a
// small pose state (swing, sag, per-finger grip, cheer and fall progress),
// built with Phaser Graphics only, no image assets. Under
// prefers-reduced-motion nothing sways or animates; each state is drawn
// directly in its final pose.
export class HangmanFigure {
  private readonly scene: Phaser.Scene
  private readonly graphics: Phaser.GameObjects.Graphics
  private readonly scale: number
  private readonly reducedMotion: boolean

  // Public-facing state (read by the browser regression test).
  private fingersLost = 0
  private fallProgress = 0
  private celebrating = false

  // Animation state.
  private elapsed = 0
  private swing = 0
  private swingVelocity = 0
  private bodyShift = 0
  private slipping: { order: number; t: number } | null = null
  private handJolt = { [-1]: 0, [1]: 0 } as Record<number, number>
  private release = { [-1]: 0, [1]: 0 } as Record<number, number>
  private surprise = 0
  private cheer = -1
  private blink = 2.5
  private destroyed = false

  constructor(scene: Phaser.Scene, options: HangmanFigureOptions) {
    this.scene = scene
    this.scale = options.height / DESIGN_H
    this.reducedMotion = prefersReducedMotion()
    this.graphics = scene.add.graphics()
    // Local (0,0)..(DESIGN_W,DESIGN_H) maps onto world space centred
    // horizontally on options.x, with its bottom edge at options.y (the
    // scene passes a floor reference, not a top-left corner).
    this.graphics.setPosition(options.x - (DESIGN_W / 2) * this.scale, options.y - DESIGN_H * this.scale)
    this.graphics.setScale(this.scale)
    scene.events.on(Phaser.Scenes.Events.UPDATE, this.tick, this)
    scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => this.destroy())
    this.render()
  }

  // Resting grip for a fresh question (0) or after a resize; no animation.
  setGrip(fingersLost: number): void {
    this.fingersLost = clamp(fingersLost)
    this.fallProgress = 0
    this.celebrating = false
    this.cheer = -1
    this.slipping = null
    this.surprise = 0
    this.swing = 0
    this.swingVelocity = 0
    for (const side of [-1, 1]) {
      this.handJolt[side] = 0
      this.release[side] = this.handReleasedBy(side, this.fingersLost) ? 1 : 0
    }
    this.bodyShift = this.targetBodyShift()
    this.render()
  }

  // A wrong answer: the next finger slips off the bar. State updates
  // immediately (so input is never held up); the motion plays on top and a
  // newer slip simply replaces one still in progress.
  slipTo(fingersLost: number): void {
    const next = clamp(fingersLost)
    if (next <= this.fingersLost) {
      this.setGrip(next)
      return
    }
    // Settle any earlier slip instantly before starting the new one.
    if (this.slipping) this.finishSlip()
    this.fingersLost = next
    this.celebrating = false
    this.cheer = -1
    if (this.reducedMotion) {
      for (const side of [-1, 1]) this.release[side] = this.handReleasedBy(side, next) ? 1 : 0
      this.bodyShift = this.targetBodyShift()
      this.render()
      return
    }
    const slipped = SLIP_ORDER[next - 1]
    this.slipping = { order: next - 1, t: 0 }
    this.handJolt[slipped.side] = 7
    this.swingVelocity += 0.9 * slipped.side
    this.surprise = SURPRISE_SECONDS
    if (next >= 3) this.spawnSweat()
  }

  // Correct answer: the grip is left exactly as it was (never advances on
  // success — Milestone 4 §7); the figure cheers with two pull-ups and
  // kicking legs, and confetti bursts from above its head.
  celebrate(fingersLost: number): void {
    this.fingersLost = clamp(fingersLost)
    if (this.slipping) this.finishSlip()
    this.fallProgress = 0
    this.celebrating = true
    this.surprise = 0
    this.cheer = this.reducedMotion ? -1 : 0
    const head = this.toWorld(CX + this.bodyShift, BAR_Y + 10)
    confettiBurst(this.scene, head.x, head.y, { count: 44, power: 380 * this.scale + 200 })
    this.render()
  }

  // Drives the fall. The scene owns the tween and calls this once per frame
  // with progress 0 (just released) .. 1 (settled on the mat).
  setFallProgress(progress: number): void {
    this.fallProgress = clamp01(progress)
    this.celebrating = false
    this.cheer = -1
    if (this.slipping) this.finishSlip()
    if (this.reducedMotion) this.render()
  }

  destroy(): void {
    if (this.destroyed) return
    this.destroyed = true
    this.scene.events.off(Phaser.Scenes.Events.UPDATE, this.tick, this)
    this.graphics.destroy()
  }

  // ---- animation ---------------------------------------------------------

  private tick(_time: number, deltaMs: number): void {
    if (this.destroyed || this.reducedMotion) return
    const dt = Math.min(deltaMs, 50) / 1000
    this.elapsed += dt

    if (this.slipping) {
      this.slipping.t += dt / SLIP_SECONDS
      if (this.slipping.t >= 1) this.finishSlip()
    }
    for (const side of [-1, 1]) {
      this.handJolt[side] -= this.handJolt[side] * Math.min(1, dt * 9)
      const wantRelease = this.handReleasedBy(side, this.fingersLost) && !this.isSlippingHand(side) ? 1 : 0
      this.release[side] += Math.sign(wantRelease - this.release[side]) * Math.min(Math.abs(wantRelease - this.release[side]), dt / RELEASE_SECONDS)
    }
    this.bodyShift += (this.targetBodyShift() - this.bodyShift) * Math.min(1, dt * 4)
    this.surprise = Math.max(0, this.surprise - dt)
    if (this.cheer >= 0) {
      this.cheer += dt / CHEER_SECONDS
      if (this.cheer >= 1) this.cheer = -1
    }
    this.blink -= dt
    if (this.blink < -0.12) this.blink = 2.4 + Math.random() * 2.6

    // A damped pendulum: a gentle idle sway plus impulses from each slip.
    // Leaning toward the gripping hand once the other has let go.
    const idle = 0.035 * Math.sin(this.elapsed * 1.15)
    const lean = (this.release[1] - this.release[-1]) * 0.1
    const target = this.fallProgress > 0 ? 0 : idle + lean
    const accel = -9 * (this.swing - target) - 1.4 * this.swingVelocity
    this.swingVelocity += accel * dt
    this.swing += this.swingVelocity * dt
    if (this.fallProgress > 0) this.swing *= 1 - this.fallProgress

    this.render()
  }

  private finishSlip(): void {
    this.slipping = null
  }

  private isSlippingHand(side: number): boolean {
    return this.slipping !== null && SLIP_ORDER[this.slipping.order].side === side
  }

  // A hand lets go of the bar once all five of its fingers have slipped
  // (only ever one hand before the final, falling slip).
  private handReleasedBy(side: number, fingersLost: number): boolean {
    if (fingersLost >= MAX_WRONG_SUBMISSIONS) return false
    return SLIP_ORDER.slice(0, fingersLost).filter((f) => f.side === side).length >= 5
  }

  private targetBodyShift(): number {
    // Hanging from one hand pulls the body under that hand.
    const right = this.handReleasedBy(1, this.fingersLost) ? 1 : 0
    const left = this.handReleasedBy(-1, this.fingersLost) ? 1 : 0
    return (left - right) * (HAND_SPREAD - SHOULDER_HALF - 6)
  }

  // Per-finger grip, 1 = curled over the bar, 0 = open. The finger
  // currently slipping animates between the two with a little overshoot,
  // which reads as the finger being dragged over the bar and flicking off.
  private fingerGrip(side: number, finger: number): number {
    const order = slipOrderIndex(side, finger)
    if (this.fallProgress > 0) return order < this.fingersLost ? 0 : 1 - clamp01(this.fallProgress * 8)
    if (order >= this.fingersLost) return 1
    if (this.slipping && this.slipping.order === order) return 1 - easeOutBack(clamp01(this.slipping.t))
    return 0
  }

  // ---- drawing -----------------------------------------------------------

  private render(): void {
    const g = this.graphics
    g.clear()
    this.drawRig()

    const fall = this.fallProgress
    const cheering = this.cheer >= 0
    // Two pull-ups over the cheer: shoulders rise toward the bar and back.
    const lift = cheering ? -26 * Math.sin(Math.PI * ((this.cheer * 2) % 1)) : 0
    const sag = (this.fingersLost / MAX_WRONG_SUBMISSIONS) * 14
    const handDrop = (side: number) => {
      const lostOnHand = SLIP_ORDER.slice(0, this.fingersLost).filter((f) => f.side === side).length
      return Math.min(5, lostOnHand) * 1.2 + this.handJolt[side]
    }

    // Shoulder centre in design space: hanging pose (swinging about the bar)
    // blending into the seated pose on the mat as the fall progresses.
    const pivot = { x: CX + this.bodyShift, y: BAR_Y + (handDrop(-1) + handDrop(1)) / 2 }
    const reach = ARM_REACH + sag + lift
    const hang = { x: pivot.x - Math.sin(this.swing) * reach, y: pivot.y + Math.cos(this.swing) * reach }
    const seatedY = MAT_TOP_Y - 48 + this.matSquash() * MAT_H * 0.3
    const drop = fall < 0.12 ? 0 : easeInQuad(clamp01((fall - 0.12) / 0.6))
    // One small, soft bounce on the cushion after landing.
    const bounce = fall > 0.72 ? -Math.sin(clamp01((fall - 0.72) / 0.2) * Math.PI) * 8 * (fall < 0.92 ? 1 : 0) : 0
    const shoulder = {
      x: lerp(hang.x, CX, drop),
      y: lerp(hang.y, seatedY, drop) + bounce,
    }
    const angle = this.swing * (1 - drop)
    const P = (lx: number, ly: number): Vec => ({
      x: shoulder.x + lx * Math.cos(angle) - ly * Math.sin(angle),
      y: shoulder.y + lx * Math.sin(angle) + ly * Math.cos(angle),
    })
    const seated = fall >= 0.72
    const airborne = fall > 0 && !seated

    // Legs first (behind the torso).
    this.drawLegs(P, seated, airborne, cheering)

    // Torso: a rounded capsule shirt with a lighter chest panel and a star.
    this.capsule(P(0, 6), P(0, 40), 15, SHIRT)
    g.fillStyle(SHIRT_LIGHT, 1)
    const chest = P(0, 14)
    g.fillCircle(chest.x, chest.y, 7)
    g.fillStyle(0xffd34d, 1)
    const star = P(0, 14)
    g.fillPoints(starShape(star.x, star.y, 5, 2.2, angle), true)

    // Arms.
    for (const side of [-1, 1]) {
      const shoulderJoint = P(side * SHOULDER_HALF, 2)
      if (fall > 0) {
        // Arms fly up while dropping, then rest on the knees once seated.
        // Hands leave the bar over the first moment of the fall.
        const flail = Math.sin(this.elapsed * 22 + side) * 4
        const up = P(side * 30 + flail, -34)
        const letGo = clamp01(fall / 0.12)
        const fromBar = { x: CX + side * HAND_SPREAD, y: BAR_Y + 10 }
        const hand = seated ? P(side * 22, 40)
          : { x: lerp(fromBar.x, up.x, letGo), y: lerp(fromBar.y, up.y, letGo) }
        this.capsule(shoulderJoint, hand, 5.5, SKIN)
        this.palm(hand.x, hand.y, 6.5)
        continue
      }
      const barHand = { x: CX + side * HAND_SPREAD, y: BAR_Y + handDrop(side) }
      const hangingHand = P(side * 20, 44)
      const r = this.release[side]
      const wrist = { x: lerp(barHand.x, hangingHand.x, r), y: lerp(barHand.y + 10, hangingHand.y, r) }
      this.capsule(shoulderJoint, wrist, 6, SKIN)
      if (r < 0.5) {
        this.drawGrippingHand(barHand.x, barHand.y, side)
      } else {
        this.palm(wrist.x, wrist.y + 3, 7)
      }
    }

    // Head (on top of the shoulders and arms).
    const head = P(0, -21)
    this.circle(head.x, head.y, 15, SKIN)
    g.fillStyle(HAIR, 1)
    g.beginPath()
    g.arc(head.x, head.y, 16, Math.PI * 1.08 + angle, Math.PI * 1.92 + angle, false)
    g.closePath()
    g.fillPath()
    const fringe = P(-6, -33)
    g.fillCircle(fringe.x, fringe.y, 5)
    this.drawFace(P, fall, cheering)

    // Effort lines beside the slipping hand.
    if (this.slipping && this.slipping.t < 0.7) {
      const s = SLIP_ORDER[this.slipping.order].side
      const alpha = 0.6 * (1 - this.slipping.t / 0.7)
      g.lineStyle(2.2, INK, alpha)
      const hx = CX + s * HAND_SPREAD
      const hy = BAR_Y + handDrop(s)
      for (let i = 0; i < 3; i += 1) {
        const a = -0.9 + i * 0.6
        g.lineBetween(hx + s * (14 + Math.cos(a) * 3), hy + Math.sin(a) * 9, hx + s * (22 + Math.cos(a) * 3), hy + Math.sin(a) * 13)
      }
    }

    // Short speed lines while dropping, nothing more (no impact effects).
    if (airborne && drop > 0.05) {
      g.lineStyle(2, INK, 0.3 * Math.sin(drop * Math.PI))
      for (const dx of [-24, 0, 24]) g.lineBetween(shoulder.x + dx, shoulder.y - 60, shoulder.x + dx, shoulder.y - 40)
    }
  }

  // The gym frame (two posts and the bar) and the crash mat.
  private drawRig(): void {
    const g = this.graphics
    // Floor shadow.
    g.fillStyle(INK, 0.08).fillEllipse(CX, FLOOR_Y + 4, MAT_W + 90, 16)
    // Posts with feet.
    for (const side of [-1, 1]) {
      const x = CX + side * POST_X
      g.fillStyle(INK, 1).fillRoundedRect(x - 6.5, BAR_Y - 12, 13, FLOOR_Y - BAR_Y + 12, 5)
      g.fillStyle(STEEL, 1).fillRoundedRect(x - 5, BAR_Y - 10.5, 10, FLOOR_Y - BAR_Y + 9, 4)
      g.fillStyle(STEEL_LIGHT, 1).fillRect(x - 3, BAR_Y - 6, 2.5, FLOOR_Y - BAR_Y)
      g.fillStyle(INK, 1).fillRoundedRect(x - 20, FLOOR_Y - 5, 40, 10, 5)
      g.fillStyle(STEEL, 1).fillRoundedRect(x - 18.5, FLOOR_Y - 3.5, 37, 7, 3.5)
    }
    // The bar (a tiny wobble while a finger slips).
    const wobble = this.slipping ? Math.sin(this.slipping.t * Math.PI * 5) * (1 - this.slipping.t) * 1.2 : 0
    g.fillStyle(INK, 1).fillRoundedRect(CX - POST_X - 4, BAR_Y - 5 + wobble, POST_X * 2 + 8, 10, 5)
    g.fillStyle(STEEL_LIGHT, 1).fillRoundedRect(CX - POST_X - 2.5, BAR_Y - 3.5 + wobble, POST_X * 2 + 5, 7, 3.5)
    g.fillStyle(0xffffff, 0.7).fillRect(CX - POST_X, BAR_Y - 2.5 + wobble, POST_X * 2, 1.6)

    // Crash mat: squashes like a cushion when the figure lands.
    const squash = this.matSquash()
    const h = MAT_H * (1 - squash * 0.3)
    const w = MAT_W * (1 + squash * 0.06)
    const top = FLOOR_Y - h
    g.fillStyle(INK, 1).fillRoundedRect(CX - w / 2 - 2, top - 2, w + 4, h + 4, 10)
    g.fillStyle(MAT, 1).fillRoundedRect(CX - w / 2, top, w, h, 9)
    g.fillStyle(MAT_TOP, 1).fillRoundedRect(CX - w / 2 + 4, top + 3, w - 8, Math.max(4, h * 0.3), 6)
    g.lineStyle(1.5, INK, 0.25)
    for (const fx of [-0.33, 0, 0.33]) g.lineBetween(CX + w * fx, top + h * 0.45, CX + w * fx, top + h - 4)
  }

  // Cushion compression after landing: a quick damped squash.
  private matSquash(): number {
    const f = this.fallProgress
    if (f < 0.7) return 0
    const t = (f - 0.7) / 0.3
    return Math.max(0, Math.sin(t * Math.PI * 2.2) * Math.exp(-t * 3.2)) * 0.9
  }

  private drawGrippingHand(x: number, y: number, side: number): void {
    const g = this.graphics
    // Back of the hand, just below the bar.
    this.circle(x, y + 8, 7.5, SKIN)
    // Four fingers (index nearest the thumb, little finger outermost):
    // curled over the bar when gripping, flicked open sideways when slipped. A slipped finger stays attached to the hand —
    // it has just let go of the bar.
    for (let i = 0; i < 4; i += 1) {
      const grip = this.fingerGrip(side, i)
      const knuckle = { x: x + side * (i - 1.5) * 3.6, y: y + 4 }
      const openAngle = side * (1.75 + i * 0.16) // radians from straight up, outward
      // Unclamped on purpose: the slip's overshoot swings the finger a
      // little past fully open before it settles (the "flick").
      const a = lerp(openAngle, 0, grip)
      const curlLength = knuckle.y - (BAR_Y - 6)
      const length = lerp(10.5, curlLength, clamp01(grip))
      const tip = { x: knuckle.x + Math.sin(a) * length, y: knuckle.y - Math.cos(a) * length }
      this.capsule(knuckle, tip, 2.6, grip > 0.5 ? SKIN : SKIN_SHADE)
      // A gripping finger hooks over the bar: its tip curls down in front.
      const hook = clamp01((grip - 0.6) / 0.4)
      if (hook > 0) this.capsule(tip, { x: tip.x + side * 3 * hook, y: tip.y + 9 * hook }, 2.5, SKIN)
    }
    // Thumb wraps under the bar on the inner side.
    const thumbGrip = this.fingerGrip(side, FINGER.thumb)
    const base = { x: x - side * 6, y: y + 10 }
    // Unclamped, like the fingers, so the thumb flicks away as it slips.
    const a = lerp(-side * 2.3, -side * 0.5, thumbGrip)
    const tip = { x: base.x + Math.sin(a) * 8, y: base.y - Math.cos(a) * 8 }
    this.capsule(base, tip, 2.7, thumbGrip > 0.5 ? SKIN : SKIN_SHADE)
    // Knuckle line.
    g.lineStyle(1.2, INK, 0.35)
    g.lineBetween(x - 5, y + 6, x + 5, y + 6)
  }

  private drawLegs(P: (x: number, y: number) => Vec, seated: boolean, airborne: boolean, cheering: boolean): void {
    for (const side of [-1, 1]) {
      const hip = P(side * 7, 50)
      if (seated) {
        // Sitting on the mat, legs forward toward the viewer.
        const knee = P(side * 17, 60)
        const foot = P(side * 24, 66)
        this.capsule(hip, knee, 6, PANTS)
        this.capsule(knee, foot, 5.5, PANTS)
        this.foot(foot.x, foot.y + 2, side, 1.15)
        continue
      }
      // Hanging legs trail the swing slightly; cheering kicks them
      // alternately; airborne legs spread a little.
      const trail = -this.swingVelocity * 0.25
      const kick = cheering ? Math.max(0, Math.sin(this.cheer * Math.PI * 6 + (side > 0 ? 0 : Math.PI))) : 0
      const spread = airborne ? 0.3 : 0.06
      const thigh = 22
      const shin = 22
      const kneeAngle = side * spread + trail
      const knee = P(side * 7 + Math.sin(kneeAngle) * thigh, 50 + Math.cos(kneeAngle) * thigh - kick * 10)
      const bend = kick * 1.6
      const footLocal = {
        x: side * 7 + Math.sin(kneeAngle) * thigh + Math.sin(kneeAngle * 1.4 + side * bend * 0.4) * shin,
        y: 50 + Math.cos(kneeAngle) * thigh - kick * 10 + Math.cos(bend) * shin,
      }
      const foot = P(footLocal.x, footLocal.y)
      this.capsule(hip, knee, 6, PANTS)
      this.capsule(knee, foot, 5.5, PANTS)
      this.foot(foot.x, foot.y + 2, side, 1)
    }
  }

  // Expressions, picked by state: happy on a correct answer, surprised for
  // a moment after a slip and while dropping, gently sad once on the mat
  // (mild — no tears), otherwise a focused "holding on" face whose brows
  // tilt as the grip weakens (effort, never pain).
  private drawFace(P: (x: number, y: number) => Vec, fall: number, cheering: boolean): void {
    if (fall > 0 && fall < 0.9) return this.surprisedFace(P)
    if (fall >= 0.9) return this.sadFace(P)
    if (this.celebrating || cheering) return this.happyFace(P)
    if (this.surprise > 0) return this.surprisedFace(P)
    this.strainFace(P, Math.min(1, this.fingersLost / MAX_WRONG_SUBMISSIONS))
  }

  private strainFace(P: (x: number, y: number) => Vec, strain: number): void {
    const g = this.graphics
    const blinking = !this.reducedMotion && this.blink < 0
    for (const side of [-1, 1]) {
      const eye = P(side * 5.5, -21)
      if (blinking) {
        g.lineStyle(1.6, INK, 1)
        g.lineBetween(eye.x - 2.2, eye.y, eye.x + 2.2, eye.y)
      } else {
        g.fillStyle(0xffffff, 1).fillCircle(eye.x, eye.y, 3)
        // Pupils glance up at the hands as the grip weakens.
        const look = P(side * 5.5, -21 - strain * 1.3)
        g.fillStyle(INK, 1).fillCircle(look.x, look.y, 1.7)
      }
      const tilt = strain * 2.6
      const browIn = P(side * 2.4, -26.5 + tilt)
      const browOut = P(side * 8.4, -27.5 - tilt * 0.4)
      g.lineStyle(1.7, INK, 1)
      g.lineBetween(browIn.x, browIn.y, browOut.x, browOut.y)
    }
    const mouth = P(0, -13)
    if (strain < 0.25) {
      const l = P(-3.5, -13.5)
      const r = P(3.5, -13.5)
      g.lineStyle(1.6, INK, 1)
      g.lineBetween(l.x, l.y, r.x, r.y)
    } else {
      // Gritted teeth: a white bar with an outline.
      const w = lerp(7, 9, strain)
      g.fillStyle(INK, 1).fillRoundedRect(mouth.x - w / 2 - 1, mouth.y - 2.8, w + 2, 5.6, 2.5)
      g.fillStyle(0xffffff, 1).fillRoundedRect(mouth.x - w / 2, mouth.y - 1.8, w, 3.6, 1.8)
    }
    if (strain >= 0.5) {
      // Rosy effort cheeks.
      g.fillStyle(0xff8a8a, 0.35)
      for (const side of [-1, 1]) {
        const c = P(side * 9, -15)
        g.fillCircle(c.x, c.y, 2.8)
      }
    }
  }

  private surprisedFace(P: (x: number, y: number) => Vec): void {
    const g = this.graphics
    for (const side of [-1, 1]) {
      const eye = P(side * 5.5, -22)
      g.fillStyle(0xffffff, 1).fillCircle(eye.x, eye.y, 3.6)
      g.lineStyle(1.2, INK, 1).strokeCircle(eye.x, eye.y, 3.6)
      g.fillStyle(INK, 1).fillCircle(eye.x, eye.y, 1.6)
      const browIn = P(side * 2.6, -29)
      const browOut = P(side * 8.4, -29.5)
      g.lineStyle(1.6, INK, 1).lineBetween(browIn.x, browIn.y, browOut.x, browOut.y)
    }
    const mouth = P(0, -12)
    g.fillStyle(INK, 1).fillEllipse(mouth.x, mouth.y, 5.6, 7)
  }

  private sadFace(P: (x: number, y: number) => Vec): void {
    const g = this.graphics
    for (const side of [-1, 1]) {
      const eye = P(side * 5.5, -20)
      g.fillStyle(INK, 1).fillCircle(eye.x, eye.y, 1.7)
      const browIn = P(side * 2.4, -26)
      const browOut = P(side * 8.4, -23.5)
      g.lineStyle(1.6, INK, 1).lineBetween(browIn.x, browIn.y, browOut.x, browOut.y)
    }
    const mouth = P(0, -9)
    g.lineStyle(1.6, INK, 1)
    g.beginPath()
    g.arc(mouth.x, mouth.y, 4, Math.PI * 1.15, Math.PI * 1.85, false)
    g.strokePath()
  }

  private happyFace(P: (x: number, y: number) => Vec): void {
    const g = this.graphics
    g.lineStyle(1.7, INK, 1)
    for (const side of [-1, 1]) {
      const eye = P(side * 5.5, -20)
      g.beginPath()
      g.arc(eye.x, eye.y, 2.4, Math.PI, 0, false)
      g.strokePath()
    }
    const mouth = P(0, -15)
    g.fillStyle(INK, 1)
    g.beginPath()
    g.arc(mouth.x, mouth.y, 5, Math.PI * 0.05, Math.PI * 0.95, false)
    g.closePath()
    g.fillPath()
    g.fillStyle(0xff7a7a, 1).fillCircle(mouth.x, mouth.y + 3, 2)
    g.fillStyle(0xff8a8a, 0.35)
    for (const side of [-1, 1]) {
      const c = P(side * 9.5, -15)
      g.fillCircle(c.x, c.y, 2.8)
    }
  }

  // ---- shape helpers -------------------------------------------------
  // Every limb is a dark outline capsule with a narrower coloured one on
  // top, built from two circles plus a filled quad (Phaser Graphics has no
  // native round line cap).

  private capsule(a: Vec, b: Vec, r: number, color: number): void {
    this.capsuleShape(a, b, r + 1.5, INK)
    this.capsuleShape(a, b, r, color)
  }

  private capsuleShape(a: Vec, b: Vec, r: number, color: number): void {
    const g = this.graphics
    const angle = Math.atan2(b.y - a.y, b.x - a.x)
    const nx = Math.cos(angle + Math.PI / 2) * r
    const ny = Math.sin(angle + Math.PI / 2) * r
    g.fillStyle(color, 1)
    g.fillPoints([
      new Phaser.Math.Vector2(a.x + nx, a.y + ny),
      new Phaser.Math.Vector2(b.x + nx, b.y + ny),
      new Phaser.Math.Vector2(b.x - nx, b.y - ny),
      new Phaser.Math.Vector2(a.x - nx, a.y - ny),
    ], true)
    g.fillCircle(a.x, a.y, r)
    g.fillCircle(b.x, b.y, r)
  }

  private circle(x: number, y: number, r: number, color: number): void {
    const g = this.graphics
    g.fillStyle(INK, 1).fillCircle(x, y, r + 1.5)
    g.fillStyle(color, 1).fillCircle(x, y, r)
  }

  private palm(x: number, y: number, r: number): void {
    this.circle(x, y, r, SKIN)
  }

  private foot(x: number, y: number, side: number, size: number): void {
    const g = this.graphics
    g.fillStyle(INK, 1).fillEllipse(x + side * 4, y, 23 * size, 13 * size)
    g.fillStyle(SHOE, 1).fillEllipse(x + side * 4, y, 19 * size, 9.5 * size)
    g.fillStyle(SOLE, 0.9).fillRect(x + side * 4 - 8 * size, y + 2 * size, 16 * size, 1.6 * size)
  }

  // A sweat drop that flies off the head — a cartoon "this is getting
  // hard" cue from the third slip on. A short-lived world-space object.
  private spawnSweat(): void {
    const side = Math.random() < 0.5 ? -1 : 1
    const start = this.toWorld(CX + this.bodyShift + side * 14, BAR_Y + ARM_REACH - 34)
    const drop = this.scene.add.graphics({ x: start.x, y: start.y })
    const s = Math.max(0.6, this.scale)
    drop.fillStyle(SWEAT, 1)
    drop.fillCircle(0, 0, 3.4 * s)
    drop.fillTriangle(-3 * s, -1 * s, 3 * s, -1 * s, 0, -7 * s)
    drop.lineStyle(1.2, INK, 0.6).strokeCircle(0, 0, 3.4 * s)
    this.scene.tweens.addCounter({
      from: 0, to: 1, duration: 650,
      onUpdate: (tween) => {
        const t = tween.getValue() ?? 0
        drop.x = start.x + side * t * 26 * s
        drop.y = start.y - Math.sin(t * Math.PI) * 14 * s + t * 22 * s
        drop.alpha = 1 - t * t
      },
      onComplete: () => drop.destroy(),
    })
  }

  private toWorld(localX: number, localY: number): Vec {
    return {
      x: this.graphics.x + localX * this.scale,
      y: this.graphics.y + localY * this.scale,
    }
  }
}

function clamp(fingersLost: number): number {
  return Math.max(0, Math.min(MAX_WRONG_SUBMISSIONS, Math.round(fingersLost)))
}

function starShape(x: number, y: number, outer: number, inner: number, rotation: number): Phaser.Math.Vector2[] {
  const points: Phaser.Math.Vector2[] = []
  for (let i = 0; i < 10; i += 1) {
    const r = i % 2 === 0 ? outer : inner
    const a = -Math.PI / 2 + rotation + (i * Math.PI) / 5
    points.push(new Phaser.Math.Vector2(x + Math.cos(a) * r, y + Math.sin(a) * r))
  }
  return points
}
