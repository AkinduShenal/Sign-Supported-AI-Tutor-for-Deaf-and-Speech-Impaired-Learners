import Phaser from 'phaser'
import { GAME_MODES } from '../../gameModes'
import { getCollectionStore } from '../../api/collectionStore'
import type { GameModeDefinition } from '../../gameModes'
import type { GameType } from '../../types'
import { GAME_TEXT, GAME_TYPE_TEXT } from '../gameText'
import { designSize, fitCameraToDesign, isCompactScreen } from '../viewport'
import { GAME_THEME as T, cssColor } from '../theme/gameTheme'
import { RoundedPanel, backgroundTouchScroll, bilingualPair, crispSceneText, gameButton, watchViewportSize } from '../theme/gameUi'

// Only presentation lives here. Available modes and scene/session creation
// continue to come from the existing registry and startMode callback.
export class GameSelectionScene extends Phaser.Scene {
  private compact = false

  constructor() { super({ key: 'GameSelectionScene' }) }

  create(): void {
    this.compact = isCompactScreen(this)
    fitCameraToDesign(this, this.compact)
    crispSceneText(this)
    backgroundTouchScroll(this)
    this.drawTitle()
    GAME_MODES.forEach((mode, index) => this.drawCard(mode, index))
    watchViewportSize(this, () => this.handleResize())
  }

  private handleResize(): void { this.scene.restart() }

  private drawTitle(): void {
    const { width } = designSize(this.compact)
    bilingualPair(this, { x: width / 2, primaryY: 48, secondaryY: 92,
      text: GAME_TEXT.chooseGame, width: width - 40,
      primarySize: this.compact ? 30 : 36, secondarySize: T.font.subtitle,
      color: cssColor(T.color.text), secondaryColor: cssColor(T.color.muted) })
  }

  private drawCard(mode: GameModeDefinition, index: number): void {
    const text = GAME_TYPE_TEXT[mode.type]
    const { width } = designSize(this.compact)
    const cardWidth = this.compact ? 380 : 280
    const cardHeight = this.compact ? 300 : 410
    const x = this.compact ? width / 2 : width / 2 + (index - 1) * 300
    const y = this.compact ? 292 + index * 320 : 386
    const background = new RoundedPanel(this, 0, 0, cardWidth, cardHeight,
      mode.available ? T.color.surface : T.color.surfaceSoft, T.color.border, T.radius.card, true)
    const iconX = this.compact ? -140 : 0
    const iconY = this.compact ? -4 : -134
    const icon = this.drawIcon(mode.type, iconX, iconY)
    const textX = this.compact ? 38 : 0
    const textWidth = 250
    const nameY = this.compact ? -112 : -62
    const children: Phaser.GameObjects.GameObject[] = [background, icon]
    children.push(
      ...bilingualPair(this, { x: textX, primaryY: nameY, secondaryY: nameY + 36,
        text: text.name, width: textWidth, primarySize: this.compact ? 23 : 25,
        secondarySize: T.font.body, color: cssColor(T.color.text), secondaryColor: cssColor(T.color.muted) }),
      ...bilingualPair(this, { x: textX, primaryY: this.compact ? -16 : 27, secondaryY: this.compact ? 40 : 72,
        text: text.description, width: textWidth, primarySize: T.font.body,
        secondarySize: T.font.caption, color: cssColor(T.color.text), secondaryColor: cssColor(T.color.muted), wrap: true }),
    )
    const actionY = this.compact ? 110 : 151
    const status = mode.available ? GAME_TEXT.play : GAME_TEXT.comingNext
    // The whole available card remains the tap target, as before. Its action
    // uses the shared visual style but does not add a second input handler.
    const action = gameButton(this, {
      x: textX, y: actionY, width: this.compact ? 224 : 236, height: T.control.compactHeight,
      label: mode.available ? `${status.en}  →` : status.en, subLabel: status.si,
      kind: mode.available ? 'primary' : 'disabled', interactive: false, onClick: () => {},
    })
    children.push(action)
    if (!mode.available) {
      const lock = this.add.graphics({ x: iconX + 23, y: iconY + 23 })
      lock.fillStyle(T.color.surface, 1).fillCircle(0, 0, 16)
      lock.lineStyle(2, T.color.muted).strokeRoundedRect(-5, -9, 10, 10, 5)
      lock.fillStyle(T.color.muted).fillRoundedRect(-7, -3, 14, 12, 3)
      lock.fillStyle(T.color.surface).fillCircle(0, 2, 1.5)
      children.push(lock)
    }
    const card = this.add.container(x, y, children)
    if (mode.available) {
      card.setInteractive({
        hitArea: new Phaser.Geom.Rectangle(-cardWidth / 2, -cardHeight / 2, cardWidth, cardHeight),
        hitAreaCallback: Phaser.Geom.Rectangle.Contains, useHandCursor: true,
      })
      card.on('pointerover', () => background.setStrokeStyle(2, T.color.primary))
      card.on('pointerdown', () => background.setFillStyle(T.color.primarySoft))
      card.on('pointerout', () => background.setFillStyle(T.color.surface).setStrokeStyle(1, T.color.border))
      card.on('pointerup', () => this.startMode(mode))
    }
  }

  private drawIcon(type: GameType, x: number, y: number): Phaser.GameObjects.Graphics {
    const g = this.add.graphics({ x, y })
    g.fillStyle(T.color.primarySoft).fillRoundedRect(-38, -38, 76, 76, 22)
    g.lineStyle(3, T.color.primary)
    if (type === 'drag_drop') {
      g.lineBetween(0, -22, 0, 23).lineBetween(-13, 24, 13, 24)
      g.lineBetween(-24, -12, 24, -12)
      for (const side of [-1, 1]) {
        g.lineBetween(side * 22, -12, side * 22 - 12, 11)
        g.lineBetween(side * 22, -12, side * 22 + 12, 11)
        g.strokeEllipse(side * 22, 11, 24, 8)
      }
    } else if (type === 'hangman') {
      g.lineBetween(-26, -20, 26, -20)
      g.lineBetween(-16, -20, -16, -5).lineBetween(16, -20, 16, -5)
      g.strokeCircle(0, -2, 8)
      g.lineBetween(-16, -5, -8, 9).lineBetween(16, -5, 8, 9)
      g.lineBetween(0, 6, 0, 21).lineBetween(0, 21, -10, 30).lineBetween(0, 21, 10, 30)
    } else {
      g.strokeRoundedRect(-22, -25, 44, 50, 9)
      g.lineBetween(-13, 12, 13, 12)
      g.strokeCircle(0, -6, 8).lineBetween(0, 2, 0, 5)
    }
    return g
  }

  private startMode(mode: GameModeDefinition): void {
    if (!mode.available || !mode.sceneKey) return
    const store = getCollectionStore()
    const open = store.sessions().filter(row => !row.closed)
    if (open.some(row => !row.completed || store.status(row.request.client_session_id) !== 'Saved')) {
      window.dispatchEvent(new Event('game-collection-warning'))
      return
    }
    for (const row of open) store.close(row.request.client_session_id)
    this.scene.start(mode.sceneKey, { gameType: mode.type })
  }
}
