import Phaser from 'phaser'
import type { LevelStep, OperationChoice } from '../../data/equationLevels'
import type { EquationVariant } from '../../data/equationVariants'
import { equationBeforeStep, expectedOperationOf, orderedChoices } from '../../data/variantAccess'
import type { GameSessionTracker } from '../../analytics/GameSessionTracker'
import { GameBackendSync } from '../../api/gameBackendSync'
import { getVariantUsage } from '../../api/gameApi'
import type { GameResultResponse } from '../../api/gameApi'
import { requireCollectionStudent } from '../../collectionIdentity'
import { GameSession } from '../../session/GameSession'
import type { GameType } from '../../types'
import { BalanceScale } from '../BalanceScale'
import { MAX_STARS_PER_TASK, formatStars, starsForTask } from '../stars'
import {
  FONT_FAMILY,
  GAME_TEXT,
  SINHALA_TEXT,
  bilingualHint,
  difficultyText,
  inline,
  stacked,
} from '../gameText'
import { GAME_THEME as T, cssColor } from '../theme/gameTheme'
import { RoundedPanel, backgroundTouchScroll, crispSceneText, gameButton, progressStepper, watchViewportSize } from '../theme/gameUi'
import { designSize, fitCameraToDesign, isCompactScreen, prefersReducedMotion } from '../viewport'

const COLORS = {
  text: cssColor(T.color.text),
  buttonFill: T.color.surfaceSoft,
  buttonBorder: T.color.border,
  buttonBorderHover: T.color.primary,
  correctText: cssColor(T.color.success),
  incorrectText: cssColor(T.color.error),
}

// Vertical positions for the two layouts (wide desktop / compact phone).
// The balance scale sits between the progress path and the drop zone.
const LAYOUTS = {
  wide: {
    titleY: 44, titleSize: '32px', subtitleY: 96, indicatorY: 150, pathY: 196,
    scaleY: 250, equationY: 390, equationSize: 36, dropY: 466, dropH: 76,
    cardsY: 568, cardH: 82, hintY: 680, hintTextY: 766, feedbackY: 766,
    doneFeedbackY: 680, rewardY: 730, nextY: 790, nextH: 64,
  },
  compact: {
    titleY: 92, titleSize: '30px', subtitleY: 170, indicatorY: 254, pathY: 300,
    scaleY: 354, equationY: 484, equationSize: 34, dropY: 564, dropH: 88,
    cardsY: 674, cardH: 88, hintY: 886, hintTextY: 988, feedbackY: 988,
    doneFeedbackY: 886, rewardY: 952, nextY: 1024, nextH: 68,
  },
}

// Data passed when this scene starts or restarts. From the Game Selection
// screen only `gameType` is given, so a brand-new GameSession is created.
// Resizes and the move to the summary pass the existing `session` back in,
// so progress, analytics and the chosen tasks survive (the task list is
// never re-rolled mid-assessment).
interface SceneInitData {
  gameType?: GameType
  session?: GameSession
  stepIndex?: number
  showSummary?: boolean
}

// A Phaser "Scene" is one self-contained screen of the game: it has its own
// create() (build everything once) and can react to input, timers and
// tweens (animations) after that. This scene is the whole equation game —
// level progression and analytics are plain data/logic layered on top of
// the same rendering and drag-and-drop built for Milestone 1/1.5.
export class EquationGameScene extends Phaser.Scene {
  // The assessment state shared by every game mode. These accessors keep
  // the rest of this scene reading as before.
  private session!: GameSession
  private get tracker(): GameSessionTracker {
    return this.session.tracker
  }
  private get backendSync(): GameBackendSync {
    return this.session.backendSync
  }
  private get levels(): EquationVariant[] {
    return this.session.levels
  }
  private set levels(value: EquationVariant[]) {
    this.session.levels = value
  }
  private get currentLevelIndex(): number {
    return this.session.levelIndex
  }
  private set currentLevelIndex(value: number) {
    this.session.levelIndex = value
  }
  private get stars(): number[] {
    return this.session.stars
  }
  // Bumped on every init() (every create() cycle, including a resize
  // restart). loadAssessmentVariants() captures this before its one await
  // and checks it again after — Phaser reuses this same scene instance
  // across scene.restart(), so without this check, a load that was still
  // in flight when a later restart superseded it would resolve and call
  // this.add.text(...) against a scene instance that's mid-teardown for
  // that restart (this.add is briefly null then), or just overwrite a
  // newer, already-displayed set of tasks with a stale one.
  private sceneGeneration = 0
  // True once this whole scene (not just one cycle of it) has been torn
  // down — e.g. React 19's StrictMode intentionally mounts PhaserGame,
  // unmounts it (which calls game.destroy(true)), then mounts it again, to
  // surface exactly this kind of bug. The generation check above only
  // catches a restart *within* a still-alive scene instance; it can't
  // catch this, since nothing calls init() again afterwards to bump it.
  private isDestroyed = false
  private loadingText: Phaser.GameObjects.Text | null = null
  private currentStepIndex = 0
  private showSummary = false
  private isCompactLayout = false
  private reducedMotion = false
  private balanceScale!: BalanceScale
  private progressItems: Phaser.GameObjects.GameObject[] = []
  private rewardText!: Phaser.GameObjects.Text

  // The layout is drawn in a fixed design space and the camera zooms to
  // fit the canvas (see viewport.ts), so the whole game is always visible.
  private get viewWidth(): number {
    return designSize(this.isCompactLayout).width
  }

  private get viewHeight(): number {
    return designSize(this.isCompactLayout).height
  }

  private get layout() {
    return this.isCompactLayout ? LAYOUTS.compact : LAYOUTS.wide
  }

  private equationText!: Phaser.GameObjects.Text
  private levelIndicatorText!: Phaser.GameObjects.Text
  private feedbackText!: Phaser.GameObjects.Text
  private hintButton!: Phaser.GameObjects.Container
  private hintText!: Phaser.GameObjects.Text
  private nextButton!: Phaser.GameObjects.Container
  private operationButtons: Phaser.GameObjects.Container[] = []
  private hasAnsweredStepCorrectly = false

  // The drop zone the operation cards get dragged into.
  private dropZone!: Phaser.GameObjects.Zone
  private dropZoneOutline!: RoundedPanel
  private dropZoneLabel!: Phaser.GameObjects.Text
  private dropZoneX = 0
  private dropZoneY = 0

  constructor() {
    // The key is just an internal name Phaser uses to identify this scene.
    super({ key: 'EquationGameScene' })
  }

  private get currentLevel(): EquationVariant {
    return this.levels[this.currentLevelIndex]
  }

  private get currentStep(): LevelStep {
    return this.currentLevel.steps[this.currentStepIndex]
  }

  // Phaser calls init() right before create(), with whatever data
  // scene.restart() was called with. This is how progress and the
  // analytics tracker survive a resize or the move to the summary screen,
  // instead of a fresh EquationGameScene starting from level 1 every time.
  init(data: SceneInitData): void {
    this.sceneGeneration += 1
    // Started from Game Selection: no session yet, so create a clean one
    // (new identifiers, tracker and backend sync). A resize or the summary
    // hand the existing one back.
    this.session =
      data.session ??
      new GameSession({
        gameType: data.gameType ?? 'drag_drop',
        studentId: requireCollectionStudent(),
        backendSync: new GameBackendSync(),
      })
    this.currentStepIndex = data.stepIndex ?? 0
    this.showSummary = data.showSummary ?? false
  }

  create(): void {
    this.isCompactLayout = isCompactScreen(this)
    fitCameraToDesign(this, this.isCompactLayout)
    crispSceneText(this)
    backgroundTouchScroll(this)
    this.reducedMotion = prefersReducedMotion()

    if (this.showSummary) {
      this.createSessionSummaryScreen()
    } else if (this.levels.length > 0) {
      // Tasks were already chosen — either a resize rebuild mid-assessment,
      // or a resize that landed after loadAssessmentVariants() finished.
      this.createGameplayScreen()
    } else {
      // No tasks chosen yet: either a genuine fresh start, or a resize that
      // landed *while* loadAssessmentVariants() was still waiting on the
      // backend (Phaser's RESIZE scale mode can fire more than once right
      // after boot, before that fetch resolves — more likely the slower
      // the environment starts up, e.g. a cold Docker container). Only
      // call startSession() on a genuine fresh start, so a mid-load resize
      // can't create a second backend session (GameSession.start() only acts
      // once, so calling it from every restart is safe). The display list was just
      // cleared by this restart, so always repaint the loading screen and
      // start a fresh load for *this* cycle — loadAssessmentVariants()
      // checks sceneGeneration before acting, so an earlier cycle's load
      // that resolves late is a safe no-op rather than a second render.
      this.session.start()
      this.createLoadingScreen()
      void this.loadAssessmentVariants()
    }

    // Recreate this scene after an orientation or browser-size change, so
    // the layout can switch cleanly between desktop and mobile. Progress
    // and analytics are passed back in through init(), above.
    watchViewportSize(this, () => this.handleResize())
    this.events.once(Phaser.Scenes.Events.DESTROY, () => {
      this.isDestroyed = true
    })
  }

  private handleResize(): void {
    // Refit the existing design without restarting the scene: a restart
    // cancels answer animations and resets the current step's input guards.
    // Keeping this assessment's initial layout is safer than losing an
    // accepted answer during a tablet rotation.
    fitCameraToDesign(this, this.isCompactLayout)
  }

  // ---- Gameplay screen ----------------------------------------------

  // Shown only while loadAssessmentVariants() is waiting on the backend —
  // the one place in this scene where we deliberately make the learner
  // wait on the network, because it decides what content to show next.
  private createLoadingScreen(): void {
    this.loadingText = this.add
      .text(this.viewWidth / 2, this.viewHeight / 2, stacked(GAME_TEXT.preparing), {
        fontFamily: FONT_FAMILY,
        fontSize: '20px',
        color: COLORS.text,
        align: 'center',
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
  }

  // Milestone 3 Steps 12-13: ask the backend how many times this student
  // has already seen each variant of this concept, then pick 2 Easy + 2
  // Medium + 2 Hard tasks respecting the "maximum two uses" rule. If the
  // request fails, fall back to treating every variant as unused rather
  // than leaving the learner stuck on the loading screen.
  private async loadAssessmentVariants(): Promise<void> {
    const generation = this.sceneGeneration

    const selected = await this.session.selectVariants((studentId, conceptId) =>
      getVariantUsage(studentId, conceptId).then((usage) => usage.usage_counts),
    )

    // A restart (init() bumps sceneGeneration) may have superseded this
    // call while the request above was in flight. If so, a newer create()
    // cycle already owns the display list — possibly mid-teardown for that
    // very restart right now — so touching this.add here would be unsafe
    // and the result would be stale anyway. Let the current cycle's own
    // load (already running) be the one that renders. Likewise, if the
    // whole scene was destroyed outright (no restart follows that, so
    // sceneGeneration alone wouldn't catch it), there's nothing left to
    // render into.
    if (generation !== this.sceneGeneration || this.isDestroyed) return

    this.levels = selected
    this.createGameplayScreen()
  }

  private createGameplayScreen(): void {
    this.operationButtons = []
    this.hasAnsweredStepCorrectly = false

    // The loading screen's text is never cleared by anything else — within
    // one create() call there's no scene.restart() to clear the display
    // list for us (that only happens between separate create() calls).
    this.loadingText?.destroy()
    this.loadingText = null

    new RoundedPanel(this, this.viewWidth / 2, this.isCompactLayout ? 470 : 365,
      this.viewWidth - 40, this.isCompactLayout ? 300 : 292,
      T.color.surfaceSoft, T.color.border, T.radius.panel)
    gameButton(this, { x: 76, y: this.isCompactLayout ? 34 : 44,
      width: 120, height: 60, label: GAME_TEXT.menu.en, subLabel: GAME_TEXT.menu.si,
      kind: 'quiet', onClick: () => this.scene.start('GameSelectionScene') })
    this.createTitleAndInstructions()
    this.createLevelIndicator()
    this.createBalanceScale()
    this.createEquation()
    this.createDropZone()
    this.createFeedbackText()
    this.createRewardText()
    this.createHintArea()
    this.createNextButton()
    this.createDragListeners()

    this.displayCurrentStep()
  }

  private createTitleAndInstructions(): void {
    const centerX = this.viewWidth / 2
    const layout = this.layout

    this.add
      .text(centerX, layout.titleY, 'Balance the Equation', {
        fontFamily: FONT_FAMILY,
        fontSize: layout.titleSize,
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    this.add
      .text(centerX, layout.subtitleY, stacked(GAME_TEXT.instruction), {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.body}px`,
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: Math.max(260, this.viewWidth - 40) },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
  }

  private createLevelIndicator(): void {
    this.levelIndicatorText = this.add
      .text(this.viewWidth / 2, this.layout.indicatorY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.caption}px`,
        color: cssColor(T.color.muted),
        align: 'center',
        wordWrap: { width: this.viewWidth - 40 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
  }

  private updateLevelIndicator(): void {
    const difficulty = difficultyText(this.currentLevel.difficulty)
    const levelNumber = `${this.currentLevelIndex + 1}`
    const total = `${this.levels.length}`
    const stepCount = this.currentLevel.steps.length
    const stepNumber = `${this.currentStepIndex + 1}`

    let english = `${GAME_TEXT.level.en} ${levelNumber} of ${total} · ${difficulty.en}`
    let sinhala = `${GAME_TEXT.level.si} ${levelNumber} / ${total} · ${difficulty.si}`
    if (stepCount > 1) {
      english += ` · ${GAME_TEXT.step.en} ${stepNumber} of ${stepCount}`
      sinhala += ` · ${GAME_TEXT.step.si} ${stepNumber} / ${stepCount}`
    }
    // Wide screens have room for one line; phones stack the two languages.
    this.levelIndicatorText.setText(
      this.isCompactLayout ? `${english}\n${sinhala}` : `${english}   |   ${sinhala}`,
    )
  }

  // The row of six task nodes: filled gold when finished (with its stars
  // under it), outlined purple for the current task, grey for upcoming.
  // Numbers and stars carry the meaning, not colour alone.
  private updateProgressPath(): void {
    this.progressItems.forEach((item) => item.destroy())
    this.progressItems = progressStepper(this, {
      x: this.viewWidth / 2, y: this.layout.pathY, width: this.viewWidth - 80,
      count: this.levels.length, current: this.currentLevelIndex, stars: this.stars,
    })
  }

  private createBalanceScale(): void {
    this.balanceScale = new BalanceScale(this, {
      x: this.viewWidth / 2,
      y: this.layout.scaleY,
      width: this.viewWidth,
      fontFamily: FONT_FAMILY,
      reducedMotion: this.reducedMotion,
    })
  }

  private createEquation(): void {
    this.equationText = this.add
      .text(this.viewWidth / 2, this.layout.equationY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: `${this.layout.equationSize}px`,
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)
  }

  private createRewardText(): void {
    this.rewardText = this.add
      .text(this.viewWidth / 2, this.layout.rewardY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '20px' : '24px',
        color: cssColor(T.color.gold),
        align: 'center',
        wordWrap: { width: this.viewWidth - 20 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
      .setAlpha(0)
  }

  // Keep equations on one readable line. The balancing step text is much
  // longer than the equation itself, so compact screens need a smaller
  // font for that step. Short equations still use the normal large font.
  private setEquationDisplay(value: string): void {
    const preferredFontSize = this.layout.equationSize
    const minimumFontSize = 16
    const availableWidth = this.viewWidth - 32

    this.equationText.setFontSize(preferredFontSize)
    this.equationText.setText(value)
    this.balanceScale.setSides(value)

    if (this.equationText.width > availableWidth) {
      const fittedFontSize = Math.max(
        minimumFontSize,
        Math.floor(preferredFontSize * (availableWidth / this.equationText.width)),
      )
      this.equationText.setFontSize(fittedFontSize)
    }
  }

  // The visible target the operation cards get dragged onto. A Phaser
  // "Zone" is an invisible interactive area — we draw the outline and label
  // ourselves so it has something to look at.
  private createDropZone(): void {
    const width = Math.min(300, this.viewWidth - 48)
    const height = this.layout.dropH
    this.dropZoneX = this.viewWidth / 2
    this.dropZoneY = this.layout.dropY

    this.dropZoneOutline = new RoundedPanel(this, this.dropZoneX, this.dropZoneY,
      width, height, T.color.primarySoft, T.color.primary, T.radius.tile)

    this.dropZoneLabel = this.add
      .text(this.dropZoneX, this.dropZoneY, stacked(GAME_TEXT.dropHere), {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.body}px`,
        color: cssColor(T.color.primaryText),
        align: 'center',
        wordWrap: { width: width - 20 },
        lineSpacing: 6,
        padding: { top: 3, bottom: 3 },
      })
      .setOrigin(0.5)

    this.dropZone = this.add
      .zone(this.dropZoneX, this.dropZoneY, width, height)
      .setRectangleDropZone(width, height)
  }

  // Destroys any operation cards from the previous step and builds a fresh
  // set from the current step's choices. Called every time the visible
  // step changes (new step, new level, or a resize rebuild).
  private createOperationButtons(): void {
    this.operationButtons.forEach((button) => button.destroy())
    this.operationButtons = []

    const choices = orderedChoices(this.currentStep.choices, `${this.session.learningCycleId}:${this.currentLevel.variantId}:${this.currentStepIndex}`)
    const centerX = this.viewWidth / 2

    if (this.isCompactLayout) {
      const gap = 16
      const sidePadding = 20
      const buttonWidth = Math.min(180, (this.viewWidth - sidePadding * 2 - gap) / 2)
      const buttonHeight = this.layout.cardH
      const leftX = centerX - buttonWidth / 2 - gap / 2
      const rightX = centerX + buttonWidth / 2 + gap / 2
      const row1Y = this.layout.cardsY
      const row2Y = row1Y + buttonHeight + 14
      const positions = [
        { x: leftX, y: row1Y },
        { x: rightX, y: row1Y },
        { x: leftX, y: row2Y },
        { x: rightX, y: row2Y },
      ]

      choices.forEach((choice, index) => {
        const position = positions[index]
        const button = this.createButton(
          position.x,
          position.y,
          buttonWidth,
          buttonHeight,
          choice.label,
          () => this.handleOperationSelection(choice, button),
          operationFill(choice.label),
        )
        this.makeCardDraggable(button, choice)
        this.operationButtons.push(button)
      })
      return
    }

    const buttonWidth = 180
    const buttonHeight = this.layout.cardH
    const gap = 24
    const rowY = this.layout.cardsY

    // Wide screens have enough room to show all four choices in one row.
    const totalWidth = choices.length * buttonWidth + (choices.length - 1) * gap
    const startX = centerX - totalWidth / 2 + buttonWidth / 2

    choices.forEach((choice, index) => {
      const x = startX + index * (buttonWidth + gap)
      const button = this.createButton(
        x,
        rowY,
        buttonWidth,
        buttonHeight,
        choice.label,
        () => this.handleOperationSelection(choice, button),
        operationFill(choice.label),
      )
      this.makeCardDraggable(button, choice)
      this.operationButtons.push(button)
    })
  }

  // Turns a plain button into a draggable operation card: remembers where it
  // started (so a missed drag can snap back) and remembers which choice it
  // represents (so the drop handler knows what was dropped).
  private makeCardDraggable(card: Phaser.GameObjects.Container, choice: OperationChoice): void {
    card.setData('choice', choice)
    card.setData('originX', card.x)
    card.setData('originY', card.y)
    card.setData('dragging', false)
    this.input.setDraggable(card)
  }

  // Animates a card sliding back to the position it started at. Used both
  // when a drag misses the drop zone entirely, and after a wrong drop.
  private returnCardToOrigin(card: Phaser.GameObjects.Container): void {
    this.tweens.add({
      targets: card,
      x: card.getData('originX') as number,
      y: card.getData('originY') as number,
      duration: 250,
      ease: 'Quad.easeOut',
    })
  }

  // These listeners are what make dragging work. They live on `this.input`
  // (the scene's input plugin) rather than on each card, because Phaser
  // reports *which* card is being dragged as an argument, so one shared
  // listener is simpler than repeating the same code on every card. They
  // only need to be registered once per scene instance (not once per
  // step), since they look at whichever card triggered them.
  private createDragListeners(): void {
    this.input.on(
      'dragstart',
      (_pointer: Phaser.Input.Pointer, gameObject: Phaser.GameObjects.Container) => {
        gameObject.setData('dragging', true)
        // Bring the card in front of the others while it's being carried.
        this.children.bringToTop(gameObject)
      },
    )

    this.input.on(
      'drag',
      (
        _pointer: Phaser.Input.Pointer,
        gameObject: Phaser.GameObjects.Container,
        dragX: number,
        dragY: number,
      ) => {
        gameObject.x = dragX
        gameObject.y = dragY
      },
    )

    // Highlight the drop zone while a card is hovering over it, so it's
    // obvious where a release will count as a drop.
    this.input.on(
      'dragenter',
      (
        _pointer: Phaser.Input.Pointer,
        _gameObject: Phaser.GameObjects.Container,
        zone: Phaser.GameObjects.Zone,
      ) => {
        if (zone === this.dropZone) this.dropZoneOutline.setStrokeStyle(4, COLORS.buttonBorderHover)
      },
    )

    this.input.on(
      'dragleave',
      (
        _pointer: Phaser.Input.Pointer,
        _gameObject: Phaser.GameObjects.Container,
        zone: Phaser.GameObjects.Zone,
      ) => {
        if (zone === this.dropZone) this.dropZoneOutline.setStrokeStyle(3, COLORS.buttonBorder)
      },
    )

    // This is where a correct or incorrect DROP is detected: the card was
    // released while over the drop zone. We read back which choice it was
    // (stored in makeCardDraggable) and hand it to the exact same
    // handleOperationSelection() that the click/tap path uses. Dragging a
    // card around and releasing it somewhere else never reaches here, so it
    // is never counted as an attempt.
    this.input.on(
      'drop',
      (_pointer: Phaser.Input.Pointer, gameObject: Phaser.GameObjects.Container) => {
        this.dropZoneOutline.setStrokeStyle(3, COLORS.buttonBorder)
        const choice = gameObject.getData('choice') as OperationChoice | undefined
        if (choice) this.handleOperationSelection(choice, gameObject)
      },
    )

    // Fires after every drag, correct drop, wrong drop, or missed drop.
    // `dropped` is only true if a 'drop' event just fired for this card —
    // if the card was released somewhere that isn't the drop zone, slide it
    // back to where it started.
    this.input.on(
      'dragend',
      (
        _pointer: Phaser.Input.Pointer,
        gameObject: Phaser.GameObjects.Container,
        dropped: boolean,
      ) => {
        if (!dropped) this.returnCardToOrigin(gameObject)
      },
    )
  }

  // A reusable "button": a rectangle with a text label on top, grouped into
  // one Container so we can move/tween them as a single object and attach
  // one click handler instead of two.
  private createButton(
    x: number, y: number, width: number, height: number, label: string,
    onClick: () => void, fill: number = COLORS.buttonFill, subLabel?: string,
  ): Phaser.GameObjects.Container {
    return gameButton(this, { x, y, width, height, label, subLabel, onClick,
      kind: subLabel && label !== `💡 ${GAME_TEXT.hint.en}` ? 'primary' : 'secondary',
      fill: subLabel && label !== `💡 ${GAME_TEXT.hint.en}` ? T.color.primary : fill,
      operation: !subLabel, dragAware: true })
  }

  private createFeedbackText(): void {
    this.feedbackText = this.add
      .text(this.viewWidth / 2, this.layout.feedbackY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '18px' : '22px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.viewWidth - 24 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
      .setAlpha(0)
  }

  private createHintArea(): void {
    this.hintButton = this.createButton(
      this.viewWidth / 2,
      this.layout.hintY,
      this.isCompactLayout ? 150 : 140,
      T.control.compactHeight,
      `💡 ${GAME_TEXT.hint.en}`,
      () => this.handleHintClick(),
      COLORS.buttonFill,
      GAME_TEXT.hint.si,
    )

    this.hintText = this.add
      .text(this.viewWidth / 2, this.layout.hintTextY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '14px' : '15px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.viewWidth - 32 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
      .setAlpha(0)
  }

  private createNextButton(): void {
    this.nextButton = this.createButton(
      this.viewWidth / 2,
      this.layout.nextY,
      180,
      this.layout.nextH,
      `${GAME_TEXT.next.en} ▶`,
      () => this.advanceToNextLevel(),
      COLORS.buttonFill,
      GAME_TEXT.next.si,
    )
    this.nextButton.setAlpha(0)
    this.nextButton.disableInteractive()
  }

  // Rebuilds everything that depends on which step is currently active:
  // the equation text, the operation cards, and the level/step indicator.
  // Called when the scene first loads, when a step or level is completed,
  // and after a resize rebuild.
  private displayCurrentStep(): void {
    this.tracker.startLevel(
      this.currentLevel.variantId,
      this.currentLevel.concept,
      this.currentLevel.steps.map(
        (step: LevelStep) => expectedOperationOf(step),
      ),
    )
    this.tracker.beginStep()

    this.hasAnsweredStepCorrectly = false
    this.balanceScale.setTaskComplete(false)
    this.rewardText.setAlpha(0)
    this.updateProgressPath()
    const equationBeforeThisStep = equationBeforeStep(this.currentLevel, this.currentStepIndex)
    this.backendSync.sendEvent(this.currentLevel.variantId, 'QUESTION_SHOWN', {
      ...this.stepEvidence(),
      equation_shown: equationBeforeThisStep,
      choices_offered: orderedChoices(this.currentStep.choices, `${this.session.learningCycleId}:${this.currentLevel.variantId}:${this.currentStepIndex}`).map((c) => c.label),
    })
    this.updateLevelIndicator()
    this.setEquationDisplay(equationBeforeThisStep)

    this.createOperationButtons()

    this.feedbackText.setText('')
    this.feedbackText.setAlpha(0)
    this.feedbackText.setY(this.layout.feedbackY)

    this.hintText.setText('')
    this.hintText.setAlpha(0)
    this.hintButton.setInteractive()
    this.tweens.add({ targets: this.hintButton, alpha: 1, duration: 150 })

    this.nextButton.setAlpha(0)
    this.nextButton.disableInteractive()

    this.dropZoneLabel.setAlpha(1)
    this.dropZoneOutline.setStrokeStyle(3, COLORS.buttonBorder)
  }

  private handleOperationSelection(
    choice: OperationChoice,
    button: Phaser.GameObjects.Container,
  ): void {
    // Once this step has been answered correctly, ignore any further
    // clicks or drops (the "disable additional answer selection"
    // requirement).
    if (this.hasAnsweredStepCorrectly) return

    const taskId = this.currentLevel.variantId
    const priorAttempts = this.tracker.getStepAnalytics(this.currentStepIndex)?.attemptsCount ?? 0
    const hintsBeforeAttempt = this.tracker.getStepAnalytics(this.currentStepIndex)?.hintCount ?? 0
    if (priorAttempts > 0) {
      this.backendSync.sendEvent(taskId, 'RETRY_STARTED')
    }
    this.tracker.recordAttempt(this.currentStepIndex)
    const answerEvidence = {
      ...this.stepEvidence(),
      selected_choice: choice.label,
      is_correct: choice.isCorrect,
      attempt_number: priorAttempts + 1,
      hints_before_attempt: hintsBeforeAttempt,
      question_prompt: equationBeforeStep(this.currentLevel, this.currentStepIndex),
      expected_response: expectedOperationOf(this.currentStep),
      answer_type: 'equation_operation',
    }
    this.backendSync.sendEvent(taskId, 'ANSWER_SUBMITTED', answerEvidence)

    if (choice.isCorrect) {
      this.backendSync.sendEvent(taskId, 'ANSWER_CORRECT', answerEvidence)
      this.showCorrectFeedback(button, choice)
    } else {
      // This is where wrong attempts are recorded — only for a genuine
      // click or a card actually dropped on the zone, never for just
      // dragging a card around.
      this.tracker.recordWrongAttempt(this.currentStepIndex)
      this.backendSync.sendEvent(taskId, 'ANSWER_INCORRECT', answerEvidence)
      this.showWrongFeedback(button)
    }
  }

  // Identifies exactly which question/step an event refers to, so the
  // static variant data plus gameplay_events can reconstruct the session.
  private stepEvidence(): Record<string, unknown> {
    return {
      variant_id: this.currentLevel.variantId,
      difficulty_level: this.currentLevel.difficulty,
      step_index: this.currentStepIndex,
      step_count: this.currentLevel.steps.length,
      game_type: this.session.gameType,
    }
  }

  private handleHintClick(): void {
    // Hints can be requested more than once; every request is recorded.
    this.tracker.recordHintUsed(this.currentStepIndex)
    this.backendSync.sendEvent(this.currentLevel.variantId, 'HINT_REQUESTED', this.stepEvidence())
    // The hint shares its slot with the feedback line, so show one at a
    // time: a later answer's feedback replaces the hint (press Hint again
    // to see it).
    this.feedbackText.setAlpha(0)
    this.hintText.setText(bilingualHint(this.currentStep.hint))
    this.tweens.add({ targets: this.hintText, alpha: 1, duration: 200 })
  }

  private showCorrectFeedback(
    button: Phaser.GameObjects.Container,
    choice: OperationChoice,
  ): void {
    this.hasAnsweredStepCorrectly = true
    this.disableAllOperationButtons()
    this.hintButton.disableInteractive()
    // The hint isn't needed once the step is solved: hide it and use its
    // slot for the result, so the Correct line, stars and Next button sit
    // higher and stay on screen on phones.
    this.hintButton.setAlpha(0)
    this.feedbackText.setY(this.layout.doneFeedbackY)

    const step = this.currentStep
    const isLastStepOfLevel = this.currentStepIndex === this.currentLevel.steps.length - 1
    const isLastLevel = this.currentLevelIndex === this.levels.length - 1

    // Snap the winning card into the drop zone, whether it got there by
    // being dragged or just clicked.
    this.tweens.add({
      targets: button,
      x: this.dropZoneX,
      y: this.dropZoneY,
      // Slightly smaller once snapped in, so it doesn't cover the equation
      // caption above the drop zone.
      scale: 0.8,
      duration: 250,
      ease: 'Quad.easeOut',
    })
    this.tweens.add({ targets: this.dropZoneLabel, alpha: 0, duration: 150 })

    this.hintText.setAlpha(0)
    this.feedbackText.setText(inline(GAME_TEXT.correct))
    this.feedbackText.setColor(COLORS.correctText)
    this.tweens.add({ targets: this.feedbackText, alpha: 1, duration: 300 })

    // Step 1: show the same operation applied to both sides...
    this.time.delayedCall(600, () => {
      this.balanceScale.applyOperation(choice.label, button.x, button.y)
      this.setEquationDisplay(step.stepText)
    })

    // Step 2: ...then settle on the result, with a little "pop" tween so
    // the change is noticeable without relying on anything audible. This
    // is also when the step is marked complete for analytics, both local
    // and backend.
    const taskId = this.currentLevel.variantId
    const variant = this.currentLevel
    this.time.delayedCall(1400, () => {
      this.tweens.add({
        targets: this.equationText,
        scale: 1.15,
        duration: 200,
        yoyo: true,
        onComplete: () => this.setEquationDisplay(step.resultText),
      })
      this.tracker.completeStep(this.currentStepIndex)
      this.backendSync.sendEvent(taskId, 'TASK_COMPLETED', this.stepEvidence())

      // A variant can have several steps; the backend wants one task
      // summary per variant, so it's saved once, on the final step, with
      // the whole variant's counts.
      const totals = this.tracker.getCurrentLevelTotals()
      if (isLastStepOfLevel && totals) {
        this.backendSync.saveTaskAttempt({
          task_id: taskId,
          activity_id: variant.activityId,
          variant_id: variant.variantId,
          difficulty_level: variant.difficulty,
          attempts_count: totals.attemptsCount,
          wrong_attempts: totals.wrongAttempts,
          hints_used: totals.hintCount,
          time_taken_sec: totals.timeTakenSec,
          is_completed: true,
          is_successful: true,
        })
      }
    })

    // Step 3: decide what happens next — another step in this level, the
    // next level, or (after level 5) the session summary.
    this.time.delayedCall(2000, () => {
      if (!isLastStepOfLevel) {
        this.currentStepIndex += 1
        this.displayCurrentStep()
        return
      }

      this.tracker.completeLevel()
      this.awardStars()

      if (isLastLevel) {
        this.backendSync.sendEvent(taskId, 'GAME_COMPLETED')
        // Let the learner see the last celebration before the summary.
        this.time.delayedCall(this.reducedMotion ? 800 : 1800, () => void this.finishSession())
        return
      }

      this.nextButton.setInteractive()
      this.tweens.add({ targets: this.nextButton, alpha: 1, duration: 300 })
    })
  }

  // Stars reward correctness only (see stars.ts): wrong attempts across the
  // task's steps decide the count; hints and time never do.
  private awardStars(): void {
    const totals = this.tracker.getCurrentLevelTotals()
    const earned = starsForTask(totals?.wrongAttempts ?? 0)
    this.stars[this.currentLevelIndex] = earned

    this.balanceScale.celebrate()
    this.updateProgressPath()
    const praise = inline(earned === MAX_STARS_PER_TASK ? GAME_TEXT.perfect : GAME_TEXT.wellDone)
    this.rewardText.setText(`${formatStars(earned)}  ${praise}`)
    this.rewardText.setScale(this.reducedMotion ? 1 : 0.6)
    this.tweens.add({
      targets: this.rewardText,
      alpha: 1,
      scale: 1,
      duration: this.reducedMotion ? 0 : 350,
      ease: 'Back.easeOut',
    })
  }

  private showWrongFeedback(button: Phaser.GameObjects.Container): void {
    this.balanceScale.tipWrong()
    this.hintText.setAlpha(0)
    this.feedbackText.setY(this.layout.feedbackY)
    this.feedbackText.setText(inline(GAME_TEXT.tryAgain))
    this.feedbackText.setColor(COLORS.incorrectText)
    this.tweens.add({ targets: this.feedbackText, alpha: 1, duration: 200 })

    // A small side-to-side shake on the card that was clicked or dropped, so
    // the feedback is visually tied to the learner's choice, then it slides
    // back to its starting spot (a no-op if it was only clicked, since it
    // never left that spot). The scene itself is never reloaded — the
    // learner can just pick another card.
    this.tweens.add({
      targets: button,
      x: button.x + 8,
      duration: 60,
      yoyo: true,
      repeat: 3,
      onComplete: () => this.returnCardToOrigin(button),
    })
  }

  private disableAllOperationButtons(): void {
    this.operationButtons.forEach((button) => button.disableInteractive())
  }

  // Moves from the level just completed to the next one. Only reachable
  // from the Next button, which only appears between levels 1-4 (level 5
  // goes to the summary screen instead).
  private advanceToNextLevel(): void {
    this.currentLevelIndex += 1
    this.currentStepIndex = 0
    this.displayCurrentStep()
  }

  // Async because the summary screen it leads to needs the backend's
  // completion check (Milestone 3 Step 16) and game_results creation
  // (Step 17) to have actually finished first — unlike every other
  // backend call in this scene, this one is deliberately awaited.
  private async finishSession(): Promise<void> {
    const summary = await this.session.finish()
    // Still logged locally for development visibility — the backend now
    // also has the same session via gameplay_events/game_task_attempts.
    console.log('Game session summary:', summary)

    // The scene may have been torn down (tab switch) while completion was
    // in flight; there is nothing left to draw into.
    if (this.isDestroyed) return

    this.scene.restart({
      session: this.session,
      stepIndex: this.currentStepIndex,
      showSummary: true,
    } satisfies SceneInitData)
  }

  // ---- Session summary screen ----------------------------------------

  // Milestone 3 Step 18: shows the backend's calculated analytics, not
  // anything the frontend worked out itself. By the time this screen
  // shows, completeSession() has already resolved, so the game_results
  // row (if the 2+2+2 blueprint was reached) already exists — this is
  // just fetching it, the same brief-wait pattern as the loading screen
  // in loadAssessmentVariants().
  private createSessionSummaryScreen(): void {
    this.createLoadingScreen()
    this.loadingText?.setText(stacked(GAME_TEXT.calculating))
    void this.loadAndShowResult()
  }

  private async loadAndShowResult(): Promise<void> {
    const generation = this.sceneGeneration
    const result = await this.backendSync.getGameResult()

    // Same staleness guard as loadAssessmentVariants() — a resize (or
    // React StrictMode's double-mount) may have superseded this call
    // while the request was in flight.
    if (generation !== this.sceneGeneration || this.isDestroyed) return

    this.loadingText?.destroy()
    this.loadingText = null

    if (result) {
      this.renderResultSummary(result)
    } else {
      // The backend never calculates nothing — a null result here means
      // the fetch itself failed (network/server issue), not that the
      // assessment was somehow incomplete (the game only ever reaches
      // this screen after finishing all 6 tasks). Fall back to the local
      // tracker's raw counts rather than leaving the screen blank; these
      // are tallies, not the calculated rates the backend owns, so
      // showing them here doesn't break the "frontend never calculates a
      // rate" rule (Important Rule #9).
      this.renderFallbackSummary()
    }
  }

  // The learner-facing part of the summary: a trophy, stars per task and a
  // pointer to the next step. Returns the y just below it. The calculated
  // rates are analytics, so they sit behind a "Show details" toggle.
  private renderStarBoard(title: { en: string; si: string }): number {
    const centerX = this.viewWidth / 2
    const compact = this.isCompactLayout
    let y = compact ? 50 : 28

    this.add
      .text(centerX, y, '🏆', { fontFamily: FONT_FAMILY, fontSize: compact ? '48px' : '34px' })
      .setOrigin(0.5)
    y += compact ? 56 : 40

    this.add
      .text(centerX, y, title.en, {
        fontFamily: FONT_FAMILY,
        fontSize: compact ? '24px' : '28px',
        fontStyle: 'bold',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.viewWidth - 32 },
      })
      .setOrigin(0.5)
    y += compact ? 30 : 26
    this.add
      .text(centerX, y, title.si, {
        fontFamily: FONT_FAMILY,
        fontSize: '16px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.viewWidth - 32 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
    y += compact ? 40 : 36

    const earned = this.stars.reduce((sum, value) => sum + value, 0)
    const possible = this.levels.length * MAX_STARS_PER_TASK
    const total = this.add
      .text(centerX, y, `★ ${earned} / ${possible}`, {
        fontFamily: FONT_FAMILY,
        fontSize: compact ? '34px' : '38px',
        fontStyle: 'bold',
        color: cssColor(T.color.gold),
      })
      .setOrigin(0.5)
    if (!this.reducedMotion) {
      total.setScale(0.5)
      this.tweens.add({ targets: total, scale: 1, duration: 500, ease: 'Back.easeOut' })
    }
    y += compact ? 44 : 38

    // One row per task: its number, difficulty and stars.
    this.levels.forEach((level, index) => {
      const difficulty = difficultyText(level.difficulty)
      this.add
        .text(
          centerX,
          y,
          `${index + 1}. ${difficulty.en} · ${difficulty.si}   ${formatStars(this.stars[index] ?? 0)}`,
          { fontFamily: FONT_FAMILY, fontSize: '17px', color: COLORS.text, padding: { top: 3, bottom: 3 } },
        )
        .setOrigin(0.5)
      y += compact ? 28 : 22
    })
    y += compact ? 10 : 8

    this.add
      .text(centerX, y + 14, stacked(GAME_TEXT.nextTutor), {
        fontFamily: FONT_FAMILY,
        fontSize: '16px',
        color: COLORS.correctText,
        align: 'center',
        wordWrap: { width: this.viewWidth - 24 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
    return y + (compact ? 60 : 52)
  }

  private renderDetailsToggle(top: number, lines: string[]): void {
    const centerX = this.viewWidth / 2
    const lineHeight = this.isCompactLayout ? 21 : 17
    const detailsTexts = lines.map((line, index) =>
      this.add
        .text(centerX, top + 52 + index * lineHeight, line, {
          fontFamily: FONT_FAMILY,
          fontSize: '16px',
          color: COLORS.text,
        })
        .setOrigin(0.5)
        .setVisible(false),
    )

    let open = false
    const toggleLabel = this.add
      .text(0, 0, stacked(GAME_TEXT.showDetails), {
        fontFamily: FONT_FAMILY,
        fontSize: '14px',
        color: COLORS.text,
        align: 'center',
        lineSpacing: 4,
        padding: { top: 3, bottom: 3 },
      })
      .setOrigin(0.5)
    const toggle = this.add.container(centerX, top + 14, [
      new RoundedPanel(this, 0, 0, 240, 64, COLORS.buttonFill, COLORS.buttonBorder),
      toggleLabel,
    ])
    toggle.setInteractive({
      hitArea: new Phaser.Geom.Rectangle(-120, -32, 240, 64),
      hitAreaCallback: Phaser.Geom.Rectangle.Contains,
      useHandCursor: true,
    })
    toggle.on('pointerup', () => {
      open = !open
      toggleLabel.setText(stacked(open ? GAME_TEXT.hideDetails : GAME_TEXT.showDetails))
      detailsTexts.forEach((text) => text.setVisible(open))
    })
  }

  // Returns to the Game Selection screen. Nothing is carried over: the
  // next game creates a new session.
  private renderChooseAnotherButton(): void {
    this.createButton(
      this.viewWidth / 2,
      this.viewHeight - 40,
      this.isCompactLayout ? 300 : 280,
      52,
      GAME_TEXT.chooseAnother.en,
      () => this.scene.start('GameSelectionScene'),
      COLORS.buttonFill,
      GAME_TEXT.chooseAnother.si,
    )
  }

  private renderResultSummary(result: GameResultResponse): void {
    const top = this.renderStarBoard(GAME_TEXT.assessmentComplete)
    this.renderDetailsToggle(top, [
      `Tasks: ${result.tasks_total}`,
      `Successful: ${result.successful_tasks}`,
      `Success Rate: ${formatPercent(result.game_success_rate)}`,
      `Completion Rate: ${formatPercent(result.game_completion_rate)}`,
      `Average Attempts: ${result.game_avg_attempts_per_task.toFixed(1)}`,
      `Hint Rate: ${formatPercent(result.game_hint_rate)}`,
      `Wrong Attempts: ${result.wrong_attempt_count}`,
      `Retries: ${result.retry_count}`,
      `Hints Used: ${result.total_hint_count}`,
      `Active Time: ${formatActiveTime(result.game_active_time_sec)}`,
    ])
    this.renderChooseAnotherButton()
  }

  private renderFallbackSummary(): void {
    const summary = this.tracker.getSummary()
    const totalTime = summary.totalTimeSec !== null ? `${summary.totalTimeSec}s` : '—'

    const top = this.renderStarBoard(GAME_TEXT.sessionComplete)
    this.renderDetailsToggle(top, [
      `Levels Completed: ${summary.levelsCompleted} / ${this.levels.length}`,
      `Wrong Attempts: ${summary.totalWrongAttempts}`,
      `Hints Used: ${summary.totalHintsUsed}`,
      `Total Time: ${totalTime}`,
    ])
    this.renderChooseAnotherButton()
    const warning = this.add.text(this.viewWidth / 2, this.viewHeight / 2,
      'Save unverified. Tap to retry. / සුරැකීම තහවුරු නැත. නැවත උත්සාහ කරන්න.',
      { ...SINHALA_TEXT, fontFamily: FONT_FAMILY, fontSize: '18px', color: '#ffffff',
        backgroundColor: '#9b1c1c', align: 'center', wordWrap: { width: this.viewWidth - 48 },
        padding: { x: 12, y: 12 } })
      .setOrigin(0.5).setDepth(1000).setInteractive({ useHandCursor: true })
    warning.on('pointerdown', () => {
      warning.disableInteractive().setText('Retrying save…')
      void this.backendSync.completeSession().then(() => {
        if (!this.isDestroyed) this.scene.restart({
          session: this.session, stepIndex: this.currentStepIndex, showSummary: true,
        } satisfies SceneInitData)
      })
    })
  }
}

// A soft tint per operation type. Colour only supplements the symbol on the
// card, which always stays visible.
function operationFill(label: string): number {
  switch (label.trim().charAt(0)) {
    case '+':
      return T.color.operation.add
    case '-':
    case '−':
      return T.color.operation.subtract
    case '×':
      return T.color.operation.multiply
    case '÷':
      return T.color.operation.divide
    default:
      return COLORS.buttonFill
  }
}

function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`
}

function formatActiveTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.round(totalSeconds % 60)
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
}
