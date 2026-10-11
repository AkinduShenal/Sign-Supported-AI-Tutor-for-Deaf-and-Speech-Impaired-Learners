import Phaser from 'phaser'
import { splitEquation } from './equationSides'

const BEAM_COLOR = 0x6b6375
const BEAM_DONE_COLOR = 0xf5b301
const ACCENT = 0xaa3bff
const PAN_FILL = 0xf4f3ec
const WRONG_COLOR = 0xb3261e
const TEXT_COLOR = '#1a1a1a'
const MIN_FONT = 12

interface BalanceScaleOptions {
  x: number
  y: number
  width: number
  fontFamily: string
  // When true, nothing tilts, flies or bursts; feedback is shown with
  // static colour changes instead.
  reducedMotion: boolean
}

// A drawn balance scale whose two pans show the two sides of the current
// equation. It is purely visual: the equation text always stays readable in
// the pans (and again in the caption under the scale), and the scale never
// decides correctness.
export class BalanceScale {
  private readonly scene: Phaser.Scene
  private readonly x: number
  private readonly y: number
  private readonly half: number
  private readonly panWidth: number
  private readonly panHeight = 44
  private readonly drop = 38
  private readonly fontFamily: string
  private readonly reducedMotion: boolean

  private readonly beam: Phaser.GameObjects.Graphics
  private readonly leftPan: Phaser.GameObjects.Container
  private readonly rightPan: Phaser.GameObjects.Container
  private readonly leftBox: Phaser.GameObjects.Rectangle
  private readonly rightBox: Phaser.GameObjects.Rectangle
  private readonly leftText: Phaser.GameObjects.Text
  private readonly rightText: Phaser.GameObjects.Text

  private angleRadians = 0
  private beamColor = BEAM_COLOR
  private tilt: Phaser.Tweens.Tween | null = null

  constructor(scene: Phaser.Scene, options: BalanceScaleOptions) {
    this.scene = scene
    this.x = options.x
    this.y = options.y
    this.fontFamily = options.fontFamily
    this.reducedMotion = options.reducedMotion

    this.panWidth = Math.min(132, options.width * 0.3)
    this.half = Math.min(150, options.width / 2 - this.panWidth / 2 - 10)

    // Stand: a post and a base under the pivot.
    const stand = scene.add.graphics()
    stand.fillStyle(BEAM_COLOR, 1)
    stand.fillRect(this.x - 4, this.y, 8, this.drop + this.panHeight)
    stand.fillRoundedRect(this.x - 40, this.y + this.drop + this.panHeight - 4, 80, 10, 4)

    this.beam = scene.add.graphics()

    const makePan = () => {
      const box = scene.add
        .rectangle(0, 0, this.panWidth, this.panHeight, PAN_FILL)
        .setStrokeStyle(3, BEAM_COLOR)
      const text = scene.add
        .text(0, 0, '', {
          fontFamily: this.fontFamily,
          fontSize: '22px',
          fontStyle: 'bold',
          color: TEXT_COLOR,
        })
        .setOrigin(0.5)
      const container = scene.add.container(this.x, this.y, [box, text])
      return { box, text, container }
    }
    const left = makePan()
    const right = makePan()
    this.leftPan = left.container
    this.rightPan = right.container
    this.leftBox = left.box
    this.rightBox = right.box
    this.leftText = left.text
    this.rightText = right.text

    this.render()
  }

  // Shows both sides of an equation like "x + 3 = 7" in the two pans.
  setSides(equation: string): void {
    const [left, right] = splitEquation(equation)
    this.setPanText(this.leftText, left)
    this.setPanText(this.rightText, right)
    this.pop(this.leftPan)
    this.pop(this.rightPan)
  }

  // Turns the beam gold (and keeps it level) once a task is finished; reset
  // when the next task starts.
  setTaskComplete(complete: boolean): void {
    this.beamColor = complete ? BEAM_DONE_COLOR : BEAM_COLOR
    this.render()
  }

  // The chosen operation visibly lands on both pans, because balancing means
  // doing the same thing to both sides.
  applyOperation(label: string, fromX: number, fromY: number): void {
    if (this.reducedMotion) return
    for (const pan of [this.leftPan, this.rightPan]) {
      const chip = this.scene.add
        .text(fromX, fromY, label, {
          fontFamily: this.fontFamily,
          fontSize: '24px',
          fontStyle: 'bold',
          color: '#ffffff',
          backgroundColor: '#aa3bff',
          padding: { x: 8, y: 4 },
        })
        .setOrigin(0.5)
      this.scene.tweens.add({
        targets: chip,
        x: pan.x,
        y: pan.y,
        scale: 0.7,
        alpha: 0.2,
        duration: 450,
        ease: 'Quad.easeIn',
        onComplete: () => chip.destroy(),
      })
    }
  }

  // A wrong choice tips the scale and flashes the pans, then it rights
  // itself. The red flash is a supplement; the "Try again" text is the
  // primary message.
  tipWrong(): void {
    this.flashPans(WRONG_COLOR)
    if (this.reducedMotion) return
    this.tiltTo(11, 150, 'Quad.easeOut', () =>
      this.tiltTo(-6, 220, 'Sine.easeInOut', () => this.tiltTo(0, 300, 'Back.easeOut')),
    )
  }

  // Settles level and celebrates when x has been isolated.
  celebrate(): void {
    this.setTaskComplete(true)
    this.flashPans(BEAM_DONE_COLOR)
    if (this.reducedMotion) {
      this.tiltTo(0, 0)
      return
    }
    this.tiltTo(0, 500, 'Elastic.easeOut')
    this.burst()
  }

  // ---- internals ------------------------------------------------------

  private setPanText(text: Phaser.GameObjects.Text, value: string): void {
    const maxWidth = this.panWidth - 14
    text.setFontSize(22)
    text.setText(value)
    if (text.width > maxWidth) {
      text.setFontSize(Math.max(MIN_FONT, Math.floor(22 * (maxWidth / text.width))))
    }
  }

  private pop(pan: Phaser.GameObjects.Container): void {
    if (this.reducedMotion) return
    this.scene.tweens.add({ targets: pan, scale: 1.08, duration: 110, yoyo: true })
  }

  private flashPans(color: number): void {
    for (const box of [this.leftBox, this.rightBox]) {
      box.setStrokeStyle(4, color)
    }
    this.scene.time.delayedCall(450, () => {
      for (const box of [this.leftBox, this.rightBox]) {
        box.setStrokeStyle(3, BEAM_COLOR)
      }
    })
  }

  private tiltTo(
    degrees: number,
    duration: number,
    ease = 'Linear',
    onComplete?: () => void,
  ): void {
    this.tilt?.stop()
    const from = this.angleRadians
    const to = Phaser.Math.DegToRad(degrees)
    if (duration <= 0) {
      this.angleRadians = to
      this.render()
      onComplete?.()
      return
    }
    this.tilt = this.scene.tweens.addCounter({
      from,
      to,
      duration,
      ease,
      onUpdate: (tween) => {
        this.angleRadians = tween.getValue() ?? to
        this.render()
      },
      onComplete: () => onComplete?.(),
    })
  }

  private burst(): void {
    const count = 10
    for (let i = 0; i < count; i += 1) {
      const star = this.scene.add
        .text(this.x, this.y, '★', {
          fontFamily: this.fontFamily,
          fontSize: '22px',
          color: '#f5b301',
        })
        .setOrigin(0.5)
      const angle = (i / count) * Math.PI * 2
      const distance = 70 + (i % 3) * 18
      this.scene.tweens.add({
        targets: star,
        x: this.x + Math.cos(angle) * distance,
        y: this.y + 20 + Math.sin(angle) * distance * 0.7,
        alpha: 0,
        duration: 700,
        ease: 'Quad.easeOut',
        onComplete: () => star.destroy(),
      })
    }
  }

  // Redraws the beam and strings for the current angle and moves the pans
  // to hang from the beam's ends.
  private render(): void {
    const cos = Math.cos(this.angleRadians)
    const sin = Math.sin(this.angleRadians)
    const leftEnd = { x: this.x - this.half * cos, y: this.y - this.half * sin }
    const rightEnd = { x: this.x + this.half * cos, y: this.y + this.half * sin }

    this.beam.clear()
    this.beam.lineStyle(8, this.beamColor, 1)
    this.beam.lineBetween(leftEnd.x, leftEnd.y, rightEnd.x, rightEnd.y)

    this.beam.lineStyle(2, this.beamColor, 1)
    const inset = this.panWidth * 0.4
    for (const [end, pan] of [
      [leftEnd, this.leftPan],
      [rightEnd, this.rightPan],
    ] as const) {
      const panTop = end.y + this.drop
      this.beam.lineBetween(end.x, end.y, end.x - inset, panTop)
      this.beam.lineBetween(end.x, end.y, end.x + inset, panTop)
      pan.setPosition(end.x, panTop + this.panHeight / 2)
    }

    this.beam.fillStyle(ACCENT, 1)
    this.beam.fillCircle(this.x, this.y, 9)
  }
}
