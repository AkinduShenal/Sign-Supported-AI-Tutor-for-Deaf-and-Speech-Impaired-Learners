import Phaser from 'phaser'
import { FONT_FAMILY, SINHALA_TEXT } from '../gameText'
import type { Bilingual } from '../gameText'
import { getGameLanguage, primaryGameText, secondaryGameText, subscribeGameLanguage } from '../../gameLanguage'
import { formatStars } from '../stars'
import { GAME_THEME as T, cssColor, textResolution, renderPixelRatio } from './gameTheme'

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

export function bilingualPair(scene: Phaser.Scene, options: {
  x: number; primaryY: number; secondaryY: number; text: Bilingual; width: number
  primarySize: number; secondarySize: number; color: string; secondaryColor?: string; wrap?: boolean
}): [Phaser.GameObjects.Text, Phaser.GameObjects.Text] {
  const make = (y: number, color: string) => scene.add.text(options.x, y, '', {
    fontFamily: FONT_FAMILY, color, align: 'center', ...SINHALA_TEXT,
    ...(options.wrap ? { wordWrap: { width: options.width } } : {}),
  }).setOrigin(0.5)
  const first = make(options.primaryY, options.color)
  const second = make(options.secondaryY, options.secondaryColor ?? options.color)
  const fit = (object: Phaser.GameObjects.Text, size: number) => {
    object.setFontSize(size)
    if (!options.wrap && object.width > options.width) object.setFontSize(Math.max(14, Math.floor(size * options.width / object.width)))
  }
  const update = () => {
    first.setText(primaryGameText(options.text)).setFontStyle(getGameLanguage() === 'en' ? 'bold' : '')
    second.setText(secondaryGameText(options.text)).setFontStyle('')
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
    fontSize: options.operation ? T.font.operation : subLabel ? T.font.body : 23,
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
        .setFontStyle(getGameLanguage() === 'en' ? 'bold' : '')
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
  button.on('pointerover', () => background.setStrokeStyle(2, T.color.primary))
  button.on('pointerout', rest)
  button.on('pointerdown', () => {
    if (options.dragAware) button.setData('dragging', false)
    background.setFillStyle(primary ? T.color.primaryHover : T.color.primarySoft).setStrokeStyle(2, T.color.primary)
  })
  button.on('pointerup', () => {
    rest()
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

export function crispSceneText(scene: Phaser.Scene): void {
  const sharpen = (object: Phaser.GameObjects.GameObject) => {
    if (object instanceof Phaser.GameObjects.Text) {
      object.setResolution(textResolution(scene.cameras.main.zoom))
    }
  }
  scene.events.on(Phaser.Scenes.Events.ADDED_TO_SCENE, sharpen)
  scene.events.once(Phaser.Scenes.Events.SHUTDOWN, () => scene.events.off(Phaser.Scenes.Events.ADDED_TO_SCENE, sharpen))
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

export function progressStepper(scene: Phaser.Scene, options: {
  x: number; y: number; width: number; count: number; current: number; stars: number[]
}): Phaser.GameObjects.GameObject[] {
  const { x, y, width, count, current, stars } = options
  const gap = Math.min(70, width / Math.max(1, count - 1))
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
