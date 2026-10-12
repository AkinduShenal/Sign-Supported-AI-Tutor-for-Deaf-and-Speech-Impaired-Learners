import Phaser from 'phaser'
import { GAME_MODES } from '../../gameModes'
import type { GameModeDefinition } from '../../gameModes'
import type { GameType } from '../../types'
import {
  FONT_FAMILY,
  GAME_TEXT,
  GAME_TYPE_TEXT,
  SINHALA_TEXT,
  stacked,
} from '../gameText'
import {
  designSize,
  fitCameraToDesign,
  isCompactScreen,
  prefersReducedMotion,
} from '../viewport'

const COLORS = {
  text: '#1a1a1a',
  muted: '#5b5566',
  cardFill: 0xf4f3ec,
  cardFillDisabled: 0xe7e5ee,
  border: 0x6b6375,
  borderHover: 0xaa3bff,
  accent: 0xaa3bff,
  playFill: 0xaa3bff,
}

// Big symbols rather than characters or pictures, so the cards read as a
// puzzle game for older learners and need no art assets.
const ICONS: Record<GameType, string> = {
  drag_drop: '⚖',
  hangman: '_ _ _',
  mystery_reveal: '?',
}

// The first screen of the Game component: pick an interaction mode.
// Selecting an available mode starts that mode's scene with no session, so
// that scene creates a brand-new GameSession (never reusing a finished
// one). Modes that aren't built yet are shown, labelled "Coming next", and
// can't be started.
export class GameSelectionScene extends Phaser.Scene {
  private compact = false
  private reducedMotion = false

  constructor() {
    super({ key: 'GameSelectionScene' })
  }

  create(): void {
    this.compact = isCompactScreen(this)
    this.reducedMotion = prefersReducedMotion()
    fitCameraToDesign(this, this.compact)

    this.drawTitle()
    GAME_MODES.forEach((mode, index) => this.drawCard(mode, index))

    // Rebuild when the window or orientation changes so the layout can
    // switch between wide and compact.
    this.scale.on(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.scale.off(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    })
  }

  private handleResize(): void {
    this.scene.restart()
  }

  private drawTitle(): void {
    const { width } = designSize(this.compact)
    this.add
      .text(width / 2, this.compact ? 36 : 40, GAME_TEXT.chooseGame.en, {
        fontFamily: FONT_FAMILY,
        fontSize: this.compact ? '28px' : '34px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)
    this.add
      .text(width / 2, this.compact ? 72 : 80, GAME_TEXT.chooseGame.si, {
        fontFamily: FONT_FAMILY,
        fontSize: '18px',
        color: COLORS.text,
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
  }

  private drawCard(mode: GameModeDefinition, index: number): void {
    const text = GAME_TYPE_TEXT[mode.type]
    const { width: designWidth } = designSize(this.compact)

    const cardWidth = this.compact ? 380 : 232
    const cardHeight = this.compact ? 200 : 350
    const x = this.compact ? designWidth / 2 : designWidth / 2 + (index - 1) * 250
    const y = this.compact ? 214 + index * (cardHeight + 10) : 335

    const background = this.add
      .rectangle(0, 0, cardWidth, cardHeight, mode.available ? COLORS.cardFill : COLORS.cardFillDisabled)
      .setStrokeStyle(3, COLORS.border)
    const children: Phaser.GameObjects.GameObject[] = [background]

    // Icon: on top for wide cards, on the left for compact cards.
    const iconX = this.compact ? -cardWidth / 2 + 56 : 0
    const iconY = this.compact ? -4 : -118
    children.push(
      this.add
        .text(iconX, iconY, ICONS[mode.type], {
          fontFamily: FONT_FAMILY,
          fontSize: this.compact ? '44px' : '64px',
          fontStyle: 'bold',
          color: mode.available ? '#aa3bff' : COLORS.muted,
        })
        .setOrigin(0.5),
    )

    // Text column: right of the icon on compact cards, centred on wide ones.
    const textX = this.compact ? 32 : 0
    const textWidth = this.compact ? 250 : cardWidth - 28
    const nameY = this.compact ? -80 : -56
    children.push(
      this.add
        .text(textX, nameY, text.name.en, {
          fontFamily: FONT_FAMILY,
          fontSize: this.compact ? '22px' : '24px',
          fontStyle: 'bold',
          color: COLORS.text,
          align: 'center',
          wordWrap: { width: textWidth },
        })
        .setOrigin(0.5),
      this.add
        .text(textX, nameY + (this.compact ? 26 : 28), text.name.si, {
          fontFamily: FONT_FAMILY,
          fontSize: '16px',
          color: COLORS.text,
          ...SINHALA_TEXT,
        })
        .setOrigin(0.5),
      this.add
        .text(textX, this.compact ? -4 : 36, stacked(text.description), {
          fontFamily: FONT_FAMILY,
          fontSize: this.compact ? '12px' : '14px',
          color: COLORS.text,
          align: 'center',
          wordWrap: { width: textWidth },
          ...SINHALA_TEXT,
          lineSpacing: this.compact ? 3 : SINHALA_TEXT.lineSpacing,
        })
        .setOrigin(0.5),
    )

    // Visible status/action — never colour alone.
    const statusY = this.compact ? cardHeight / 2 - 28 : cardHeight / 2 - 38
    const statusWidth = 170
    const status = mode.available ? GAME_TEXT.play : GAME_TEXT.comingNext
    children.push(
      this.add
        .rectangle(textX, statusY, statusWidth, 44, mode.available ? COLORS.playFill : COLORS.cardFill)
        .setStrokeStyle(2, mode.available ? COLORS.playFill : COLORS.border),
      this.add
        .text(textX, statusY - 7, mode.available ? `${status.en} ▶` : status.en, {
          fontFamily: FONT_FAMILY,
          fontSize: '17px',
          fontStyle: 'bold',
          color: mode.available ? '#ffffff' : COLORS.muted,
        })
        .setOrigin(0.5),
      this.add
        .text(textX, statusY + 11, status.si, {
          fontFamily: FONT_FAMILY,
          fontSize: '13px',
          color: mode.available ? '#ffffff' : COLORS.muted,
          padding: { top: 3, bottom: 3 },
        })
        .setOrigin(0.5),
    )

    const card = this.add.container(x, y, children)

    if (mode.available) {
      card.setInteractive({
        hitArea: new Phaser.Geom.Rectangle(-cardWidth / 2, -cardHeight / 2, cardWidth, cardHeight),
        hitAreaCallback: Phaser.Geom.Rectangle.Contains,
        useHandCursor: true,
      })
      card.on('pointerover', () => background.setStrokeStyle(4, COLORS.borderHover))
      card.on('pointerout', () => background.setStrokeStyle(3, COLORS.border))
      card.on('pointerup', () => this.startMode(mode))
    }

    if (!this.reducedMotion) {
      card.setAlpha(0)
      card.y = y + 14
      this.tweens.add({
        targets: card,
        alpha: mode.available ? 1 : 0.8,
        y,
        duration: 260,
        delay: index * 90,
        ease: 'Quad.easeOut',
      })
    } else if (!mode.available) {
      card.setAlpha(0.8)
    }
  }

  private startMode(mode: GameModeDefinition): void {
    if (!mode.available || !mode.sceneKey) return
    // No session is passed on purpose: the mode's scene creates a new one.
    this.scene.start(mode.sceneKey, { gameType: mode.type })
  }
}
