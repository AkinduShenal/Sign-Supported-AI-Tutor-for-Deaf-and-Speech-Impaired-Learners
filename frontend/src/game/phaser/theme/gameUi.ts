import Phaser from 'phaser'
import { FONT_FAMILY, GAME_TEXT, SINHALA_TEXT } from '../gameText'
import type { Bilingual } from '../gameText'
import { getGameLanguage, primaryGameText, secondaryGameText, subscribeGameLanguage } from '../../gameLanguage'
import { formatStars } from '../stars'
import { GAME_THEME as T, cssColor, textResolution, renderPixelRatio } from './gameTheme'
import { prefersReducedMotion } from '../viewport'

// A rounded surface with the same fill/stroke API used by existing feedback.
// Graphics stays vector-based; no new textures or bitmap assets are necessary.
export class RoundedPanel extends Phaser.GameObjects.Graphics {
  private panelFill: number
  private fillAlpha: number
  private border: number
  private borderWidth: number
  private readonly panelWidth: number
  private readonly panelHeight: number
  private readonly radius: number
  private readonly shadow: boolean

  constructor(scene: Phaser.Scene, x: number, y: number, width: number, height: number,
    fill = T.color.surface as number, border = T.color.border as number,
    radius = T.radius.tile as number, shadow = false) {
    super(scene, { x, y })
    this.panelWidth = width
    this.panelHeight = height
    this.panelFill = fill
    this.fillAlpha = 1
    this.border = border
    this.borderWidth = 1
    this.radius = radius
    this.shadow = shadow
    scene.add.existing(this)
    this.redraw()
  }

  setFillStyle(color: number, alpha = 1): this {
    this.panelFill = color
    this.fillAlpha = alpha
    return this.redraw()
  }

  setStrokeStyle(width: number, color: number): this {
    this.borderWidth = width
    this.border = color
    return this.redraw()
  }

  private redraw(): this {
    const x = -this.panelWidth / 2
    const y = -this.panelHeight / 2
    this.clear()
    if (this.shadow) {
      this.fillStyle(T.color.shadow, 0.045)
      this.fillRoundedRect(x, y + 5, this.panelWidth, this.panelHeight, this.radius)
    }
    this.fillStyle(this.panelFill, this.fillAlpha)
    this.fillRoundedRect(x, y, this.panelWidth, this.panelHeight, this.radius)
    if (this.borderWidth > 0) {
      this.lineStyle(this.borderWidth, this.border, 1)
      this.strokeRoundedRect(x, y, this.panelWidth, this.panelHeight, this.radius)
    }
    return this
  }
}

export type ButtonKind = 'primary' | 'secondary' | 'quiet' | 'disabled'

const languageBindings = new WeakMap<Phaser.GameObjects.Text, { render: () => string }>()

// Update labels in place; never restart a scene or touch assessment state.
export function bindLanguageText(text: Phaser.GameObjects.Text, render: () => string): Phaser.GameObjects.Text {
  const previous = languageBindings.get(text)
  if (previous) previous.render = render
  else {
    const binding = { render }
    languageBindings.set(text, binding)
    const unsubscribe = subscribeGameLanguage(() => text.setText(binding.render()))
    text.once(Phaser.GameObjects.Events.DESTROY, () => { unsubscribe(); languageBindings.delete(text) })
  }
  return text.setText(render())
}

// Game typography. 'title' is the chunky outlined screen title (deep purple
// fill, thick white outline, a solid drop shadow); 'heading' is bold in both
// languages (the bundled Sinhala font has a real bold); the default keeps
// the primary line bold in English only.
export type TextVariant = 'title' | 'heading' | 'body'

const TITLE_FILL = '#2a1d8f'
const TITLE_SUB_FILL = '#4b3fc4'

export function applyTitleStyle(text: Phaser.GameObjects.Text, size: number, secondary = false): Phaser.GameObjects.Text {
  const outline = Math.max(4, Math.round(size * (secondary ? 0.2 : 0.24)))
  return text
    .setColor(secondary ? TITLE_SUB_FILL : TITLE_FILL)
    .setStroke('#ffffff', outline)
    .setShadow(0, Math.max(3, Math.round(size * 0.12)), secondary ? 'rgba(42,29,143,0.18)' : 'rgba(42,29,143,0.3)', 0, true, true)
}

export function bilingualPair(scene: Phaser.Scene, options: {
  x: number; primaryY: number; secondaryY: number; text: Bilingual; width: number
  primarySize: number; secondarySize: number; color: string; secondaryColor?: string; wrap?: boolean
  variant?: TextVariant
}): [Phaser.GameObjects.Text, Phaser.GameObjects.Text] {
  const variant = options.variant ?? 'body'
  const make = (y: number, color: string) => scene.add.text(options.x, y, '', {
    fontFamily: FONT_FAMILY, color, align: 'center', ...SINHALA_TEXT,
    ...(options.wrap ? { wordWrap: { width: options.width } } : {}),
  }).setOrigin(0.5)
  const first = make(options.primaryY, options.color)
  const second = make(options.secondaryY, options.secondaryColor ?? options.color)
  if (variant === 'title') {
    applyTitleStyle(first, options.primarySize)
    applyTitleStyle(second, options.secondarySize, true)
  }
  const fit = (object: Phaser.GameObjects.Text, size: number) => {
    object.setFontSize(size)
    if (!options.wrap && object.width > options.width) object.setFontSize(Math.max(14, Math.floor(size * options.width / object.width)))
  }
  const update = () => {
    const primaryBold = variant !== 'body' || getGameLanguage() === 'en'
    first.setText(primaryGameText(options.text)).setFontStyle(primaryBold ? 'bold' : '')
    second.setText(secondaryGameText(options.text)).setFontStyle(variant === 'title' ? '600' : '')
    fit(first, options.primarySize); fit(second, options.secondarySize)
  }
  update()
  const unsubscribe = subscribeGameLanguage(update)
  first.once(Phaser.GameObjects.Events.DESTROY, unsubscribe)
  return [first, second]
}

export function gameButton(scene: Phaser.Scene, options: {
  x: number; y: number; width: number; height: number; label: string; subLabel?: string
  onClick: () => void; kind?: ButtonKind; fill?: number; operation?: boolean; dragAware?: boolean; interactive?: boolean
}): Phaser.GameObjects.Container {
  const { x, y, width, label, subLabel, onClick } = options
  const displayedZoom = scene.cameras.main.zoom / renderPixelRatio(window.devicePixelRatio)
  const height = Math.max(options.height, Math.ceil(T.control.minPhysicalHeight / displayedZoom))
  const kind = options.kind ?? 'secondary'
  const primary = kind === 'primary'
  const disabled = kind === 'disabled'
  const fill = options.fill ?? (primary ? T.color.primary : kind === 'quiet' ? T.color.surface : T.color.surfaceSoft)
  const color = cssColor(primary ? T.color.surface : disabled ? T.color.muted : T.color.text)
  const background = new RoundedPanel(scene, 0, 0, width, height, fill,
    primary ? T.color.primary : T.color.border, T.radius.button, kind !== 'quiet')
  if (kind === 'quiet') background.setStrokeStyle(0, T.color.border)
  const labelText = scene.add.text(0, subLabel ? -12 : 0, label, {
    fontFamily: FONT_FAMILY,
    fontSize: options.operation ? T.font.operation + 3 : subLabel ? T.font.body : 27,
    fontStyle: 'bold', color, align: 'center', wordWrap: { width: width - 16 },
    ...(subLabel ? SINHALA_TEXT : {}),
  }).setOrigin(0.5)
  const children: Phaser.GameObjects.GameObject[] = [background, labelText]
  if (subLabel) {
    const secondary = scene.add.text(0, 15, subLabel, {
      fontFamily: FONT_FAMILY, fontSize: T.font.caption - 1, color,
      ...SINHALA_TEXT, wordWrap: { width: width - 12 }, align: 'center',
    }).setOrigin(0.5)
    children.push(secondary)
    const update = () => {
      labelText.setText(primaryGameText({ en: label, si: subLabel }))
        .setFontStyle('bold')
      secondary.setText(secondaryGameText({ en: label, si: subLabel }))
      // Fit the two labels inside their existing hit area in either language.
      labelText.setFontSize(T.font.body)
      secondary.setFontSize(T.font.caption - 1)
      const gap = 2
      const required = labelText.height + secondary.height + gap
      const scale = Math.min(1, (height - 8) / required)
      labelText.setScale(scale); secondary.setScale(scale)
      labelText.y = -(secondary.height * scale + gap) / 2
      secondary.y = (labelText.height * scale + gap) / 2
    }
    update()
    const unsubscribe = subscribeGameLanguage(update)
    labelText.once(Phaser.GameObjects.Events.DESTROY, unsubscribe)
  }
  const button = scene.add.container(Math.round(x), Math.round(y), children)
  if (disabled || options.interactive === false) return button
  button.setInteractive({
    hitArea: new Phaser.Geom.Rectangle(-width / 2, -height / 2, width, height),
    hitAreaCallback: Phaser.Geom.Rectangle.Contains, useHandCursor: true,
  })
  const rest = () => {
    background.setFillStyle(fill).setStrokeStyle(kind === 'quiet' ? 0 : 1, primary ? T.color.primary : T.color.border)
  }
  // A tactile press: plain buttons dip slightly while held. Draggable
  // operation cards are excluded — their scale is owned by the drag/snap
  // animations in EquationGameScene.
  const pressable = !options.dragAware && !prefersReducedMotion()
  const press = (scale: number) => {
    if (!pressable) return
    scene.tweens.add({ targets: button, scale, duration: 90, ease: 'Quad.easeOut' })
  }
  button.on('pointerover', () => background.setStrokeStyle(2, T.color.primary))
  button.on('pointerout', () => { rest(); press(1) })
  button.on('pointerdown', () => {
    if (options.dragAware) button.setData('dragging', false)
    background.setFillStyle(primary ? T.color.primaryHover : T.color.primarySoft).setStrokeStyle(2, T.color.primary)
    press(0.95)
  })
  button.on('pointerup', () => {
    rest()
    press(1)
    if (!options.dragAware || !button.getData('dragging')) onClick()
  })
  // Draw a disabled state when the existing gameplay code locks a control.
  // Observe only; never change its interactive state or its gameplay callback.
  let wasEnabled = true
  const syncState = () => {
    const enabled = button.input?.enabled === true
    if (enabled === wasEnabled) return
    wasEnabled = enabled
    const labels = children.filter((child): child is Phaser.GameObjects.Text => child instanceof Phaser.GameObjects.Text)
    if (enabled) { labels.forEach(text => text.setColor(color)); rest() }
    else {
      background.setFillStyle(T.color.track).setStrokeStyle(1, T.color.border)
      labels.forEach(text => text.setColor(cssColor(T.color.muted)))
    }
  }
  scene.events.on(Phaser.Scenes.Events.POST_UPDATE, syncState)
  button.once(Phaser.GameObjects.Events.DESTROY, () => scene.events.off(Phaser.Scenes.Events.POST_UPDATE, syncState))
  return button
}

// A persistent "still working" card for the one place every Game scene
// deliberately makes the learner wait on the network with nothing else on
// screen: calculating the session result. Three bouncing dots say it's
// still going (frozen under reduced motion); underneath, a tip card rotates
// through short equation-solving reminders every 3.5s with its own
// pagination dots, fading between them (an instant swap under reduced
// motion). Call `.destroy()` on the returned container once the result
// arrives, same as the plain loading Text it replaces.
export function createResultsLoadingCard(scene: Phaser.Scene, options: {
  x: number; y: number; status: Bilingual; tips: Bilingual[]
}): Phaser.GameObjects.Container {
  const { x, y, status, tips } = options
  const reduced = prefersReducedMotion()
  const cardW = 330
  const pad = 18
  const dotsH = 16
  const statusH = 36
  const tipH = 92
  const pageDotsH = 10
  const gap = 14
  const contentH = pad + dotsH + gap + statusH + gap + tipH + 10 + pageDotsH + pad
  const top = y - contentH / 2
  const children: Phaser.GameObjects.GameObject[] = []

  children.push(new RoundedPanel(scene, x, y, cardW, contentH, T.color.surface, T.color.border, T.radius.panel, true))

  let cy = top + pad + dotsH / 2
  ;[-16, 0, 16].forEach((dx, i) => {
    const dot = scene.add.circle(x + dx, cy, 4, T.color.primary)
    children.push(dot)
    if (reduced) dot.setAlpha(0.85)
    else {
      scene.tweens.add({
        targets: dot, y: cy - 6, alpha: 0.5, duration: 420, delay: i * 130,
        yoyo: true, repeat: -1, ease: 'Sine.easeInOut',
      })
    }
  })
  cy += dotsH / 2 + gap

  bilingualPair(scene, {
    x, primaryY: cy + 9, secondaryY: cy + 26,
    text: status, width: cardW - pad * 2, primarySize: 14, secondarySize: 11.5,
    color: cssColor(T.color.text),
  }).forEach((t) => children.push(t))
  cy += statusH + gap

  const tipTop = cy
  children.push(new RoundedPanel(scene, x, tipTop + tipH / 2, cardW - pad * 2, tipH, T.color.goldSoft, T.color.gold, T.radius.tile))
  const eyebrow = scene.add
    .text(x, tipTop + 16, '', { fontFamily: FONT_FAMILY, fontSize: '10.5px', fontStyle: 'bold', color: cssColor(T.color.gold) })
    .setOrigin(0.5)
  bindLanguageText(eyebrow, () => `💡 ${primaryGameText(GAME_TEXT.quickTip)}`)
  children.push(eyebrow)

  const tipPrimary = scene.add
    .text(x, tipTop + 40, '', {
      fontFamily: FONT_FAMILY, fontSize: '13px', fontStyle: 'bold', color: cssColor(T.color.text),
      align: 'center', wordWrap: { width: cardW - pad * 2 - 20 }, ...SINHALA_TEXT,
    })
    .setOrigin(0.5)
  const tipSecondary = scene.add
    .text(x, tipTop + 68, '', {
      fontFamily: FONT_FAMILY, fontSize: '11.5px', color: cssColor(T.color.muted),
      align: 'center', wordWrap: { width: cardW - pad * 2 - 20 },
    })
    .setOrigin(0.5)
  children.push(tipPrimary, tipSecondary)
  cy = tipTop + tipH + 10

  const pageDots = tips.map((_, i) => {
    const dot = scene.add.circle(x - (tips.length - 1) * 5 + i * 10, cy + pageDotsH / 2, 3, T.color.border)
    children.push(dot)
    return dot
  })

  let index = 0
  const paint = () => {
    tipPrimary.setText(primaryGameText(tips[index])).setFontStyle('bold')
    tipSecondary.setText(secondaryGameText(tips[index]))
    pageDots.forEach((dot, i) => dot.setFillStyle(i === index ? T.color.primary : T.color.border))
  }
  paint()
  const unsubscribe = subscribeGameLanguage(paint)

  const advance = () => {
    if (reduced) { index = (index + 1) % tips.length; paint(); return }
    scene.tweens.add({
      targets: [tipPrimary, tipSecondary], alpha: 0, duration: 160, yoyo: true, ease: 'Quad.easeInOut',
      onYoyo: () => { index = (index + 1) % tips.length; paint() },
    })
  }
  const timer = scene.time.addEvent({ delay: 3500, loop: true, callback: advance })

  const container = scene.add.container(0, 0, children)
  container.once(Phaser.GameObjects.Events.DESTROY, () => {
    timer.remove(false)
    unsubscribe()
  })
  return container
}

// A rounded "HUD chip" behind a Text (e.g. the level line), resized to fit
// whatever the text currently says — including after a language switch,
// which changes the text in place.
export function hudChip(scene: Phaser.Scene, text: Phaser.GameObjects.Text, options: {
  fill?: number; alpha?: number; border?: number; padX?: number; padY?: number
} = {}): Phaser.GameObjects.Graphics {
  const fill = options.fill ?? T.color.surface
  const alpha = options.alpha ?? 0.88
  const border = options.border ?? T.color.border
  const padX = options.padX ?? 18
  const padY = options.padY ?? 4
  // Behind every regular object, in front of the backdrop.
  const chip = scene.add.graphics().setDepth(-10)
  let last = ''
  const sync = () => {
    const key = [text.text, text.width, text.height, text.x, text.y, text.visible, text.alpha].join('|')
    if (key === last) return
    last = key
    chip.clear()
    if (!text.visible || text.text === '' || text.alpha === 0) return
    const w = text.width + padX * 2
    const h = text.height + padY * 2
    const left = text.x - text.width * text.originX - padX
    const top = text.y - text.height * text.originY - padY
    const r = Math.min(h / 2, 24)
    chip.fillStyle(T.color.shadow, 0.06).fillRoundedRect(left, top + 3, w, h, r)
    chip.fillStyle(fill, alpha).fillRoundedRect(left, top, w, h, r)
    chip.lineStyle(1, border, 1).strokeRoundedRect(left, top, w, h, r)
  }
  sync()
  scene.events.on(Phaser.Scenes.Events.POST_UPDATE, sync)
  text.once(Phaser.GameObjects.Events.DESTROY, () => {
    scene.events.off(Phaser.Scenes.Events.POST_UPDATE, sync)
    chip.destroy()
  })
  return chip
}

export function crispSceneText(scene: Phaser.Scene): void {
  const sharpen = (object: Phaser.GameObjects.GameObject) => {
    if (object instanceof Phaser.GameObjects.Text) {
      object.setResolution(textResolution(scene.cameras.main.zoom))
    }
  }
  scene.events.on(Phaser.Scenes.Events.ADDED_TO_SCENE, sharpen)
  scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => scene.events.off(Phaser.Scenes.Events.ADDED_TO_SCENE, sharpen))
}

// Text textures are rasterised for the camera zoom at creation time. After a
// resize that only refits the camera (e.g. entering full screen), re-render
// every Text at the new zoom so it stays crisp instead of being stretched.
export function resharpenSceneText(scene: Phaser.Scene): void {
  const resolution = textResolution(scene.cameras.main.zoom)
  const visit = (object: Phaser.GameObjects.GameObject) => {
    if (object instanceof Phaser.GameObjects.Text) {
      if (object.style.resolution !== resolution) object.setResolution(resolution)
    } else if (object instanceof Phaser.GameObjects.Container) {
      object.list.forEach(visit)
    }
  }
  scene.children.list.forEach(visit)
}

export function watchViewportSize(scene: Phaser.Scene, onResize: () => void): void {
  const size = () => [scene.scale.width, scene.scale.height,
    scene.scale.displaySize.width, scene.scale.displaySize.height].join(':')
  let previous = size()
  const resize = () => {
    const next = size()
    // Phaser 4 also emits RESIZE for parent position changes while scrolling.
    // Only dimensions require rebuilding the UI; a scroll must not restart it.
    if (next === previous) return
    previous = next
    onResize()
  }
  scene.scale.on(Phaser.Scale.Events.RESIZE, resize)
  scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => scene.scale.off(Phaser.Scale.Events.RESIZE, resize))
}

export function backgroundTouchScroll(scene: Phaser.Scene): void {
  const touch = scene.input.manager.touch
  if (!touch) return
  const capture = (pointer: Phaser.Input.Pointer, over: Phaser.GameObjects.GameObject[]) => {
    // Blank canvas may scroll the page. Gestures beginning on controls retain
    // Phaser's original capture, including operation-card dragging.
    if (pointer.wasTouch) touch.capture = over.length > 0
  }
  scene.input.on(Phaser.Input.Events.POINTER_DOWN, capture)
  scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
    scene.input.off(Phaser.Input.Events.POINTER_DOWN, capture)
    touch.capture = true
  })
}

function stepperGap(width: number, count: number): number {
  return Math.min(70, width / Math.max(1, count - 1))
}

// Where node `index` of a progressStepper() with the same options sits —
// used to fly an earned star into its node.
export function stepperNodeX(options: { x: number; width: number; count: number }, index: number): number {
  const gap = stepperGap(options.width, options.count)
  return Math.round(options.x - gap * (options.count - 1) / 2 + index * gap)
}

export function progressStepper(scene: Phaser.Scene, options: {
  x: number; y: number; width: number; count: number; current: number; stars: number[]
}): Phaser.GameObjects.GameObject[] {
  const { x, y, width, count, current, stars } = options
  const gap = stepperGap(width, count)
  const start = x - gap * (count - 1) / 2
  const objects: Phaser.GameObjects.GameObject[] = []
  for (let i = 0; i < count; i += 1) {
    const px = Math.round(start + i * gap)
    const done = stars[i] !== undefined
    const active = i === current && !done
    if (i > 0) objects.push(scene.add.rectangle(px - gap / 2, y, gap - 30, 3, done ? T.color.primary : T.color.track))
    objects.push(scene.add.circle(px, y, 14, done ? T.color.primary : active ? T.color.primarySoft : T.color.surface)
      .setStrokeStyle(active ? 2 : 1, active ? T.color.primary : T.color.border))
    objects.push(scene.add.text(px, y, String(i + 1), {
      fontFamily: FONT_FAMILY, fontSize: 15, fontStyle: 'bold',
      color: cssColor(done ? T.color.surface : active ? T.color.primary : T.color.muted),
    }).setOrigin(0.5))
    if (done) objects.push(scene.add.text(px, y + 24, formatStars(stars[i]), {
      fontFamily: FONT_FAMILY, fontSize: 11, color: cssColor(T.color.gold),
    }).setOrigin(0.5))
  }
  return objects
}
