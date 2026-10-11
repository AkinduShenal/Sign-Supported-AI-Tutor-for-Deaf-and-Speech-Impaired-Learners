import Phaser from 'phaser'
import type { LevelStep, OperationChoice } from '../../data/equationLevels'
import type { EquationVariant } from '../../data/equationVariants'
import { selectAssessmentVariants } from '../../data/variantSelection'
import { GameSessionTracker } from '../../analytics/GameSessionTracker'
import { GameBackendSync } from '../../api/gameBackendSync'
import { getVariantUsage } from '../../api/gameApi'
import type { GameResultResponse } from '../../api/gameApi'
import { getOrCreateStudentId } from '../../identity'
import { BalanceScale } from '../BalanceScale'
import { MAX_STARS_PER_TASK, formatStars, starsForTask } from '../stars'
import { GAME_TEXT, bilingualHint, difficultyText, inline, stacked } from '../gameText'

// Every task in an assessment is one of the 18 Easy/Medium/Hard variants
// (Milestone 3 Steps 10-13) under this same overall concept.
const CONCEPT_ID = 'linear_equations'

const COLORS = {
  text: '#1a1a1a',
  buttonFill: 0xf4f3ec,
  buttonBorder: 0x6b6375,
  buttonBorderHover: 0xaa3bff,
  correctText: '#0a7a3d',
  incorrectText: '#b3261e',
}

const DESIGN = {
  wide: { width: 800, height: 640 },
  compact: { width: 420, height: 770 },
}

// Vertical positions for the two layouts (wide desktop / compact phone).
// The balance scale sits between the progress path and the drop zone.
const LAYOUTS = {
  wide: {
    titleY: 18, titleSize: '24px', subtitleY: 55, indicatorY: 91, pathY: 117,
    scaleY: 151, equationY: 262, equationSize: 30, dropY: 306, dropH: 56,
    cardsY: 377, cardH: 70, hintY: 439, hintTextY: 507, feedbackY: 507,
    doneFeedbackY: 439, rewardY: 479, nextY: 527, nextH: 44,
  },
  compact: {
    titleY: 20, titleSize: '26px', subtitleY: 78, indicatorY: 152, pathY: 186,
    scaleY: 230, equationY: 348, equationSize: 26, dropY: 392, dropH: 64,
    cardsY: 464, cardH: 72, hintY: 622, hintTextY: 700, feedbackY: 688,
    doneFeedbackY: 622, rewardY: 664, nextY: 712, nextH: 56,
  },
}

// Phaser's default text font is "Courier" if you don't set one — this
// matches the rest of the site instead of looking like a typewriter.
// Extra room for Sinhala glyphs (tall marks above and below the line).
const SINHALA_TEXT = {
  lineSpacing: 8,
  padding: { top: 4, bottom: 4 },
}

// The Sinhala fonts come before the generic fallback so canvas text that
// mixes English and Sinhala renders on Windows, Android and macOS.
const FONT_FAMILY =
  'system-ui, "Segoe UI", Roboto, "Nirmala UI", "Noto Sans Sinhala", "Iskoola Pota", "Sinhala MN", sans-serif'

// Data carried through scene.restart() so a window-resize (or finishing the
// session) can rebuild the scene without losing progress or analytics.
interface SceneInitData {
  tracker?: GameSessionTracker
  backendSync?: GameBackendSync
  studentId?: string
  learningCycleId?: string
  // The 6 Easy/Medium/Hard tasks chosen for this assessment (Milestone 3
  // Steps 10-13). Only a genuine fresh start leaves this undefined — a
  // resize or the move to the summary screen always carries it through, so
  // the task list never gets re-rolled mid-assessment.
  levels?: EquationVariant[]
  levelIndex?: number
  stepIndex?: number
  showSummary?: boolean
  // Stars earned per finished task (index = task position). Local reward
  // only — never sent to the backend.
  stars?: number[]
}

// A Phaser "Scene" is one self-contained screen of the game: it has its own
// create() (build everything once) and can react to input, timers and
// tweens (animations) after that. This scene is the whole equation game —
// level progression and analytics are plain data/logic layered on top of
// the same rendering and drag-and-drop built for Milestone 1/1.5.
export class EquationGameScene extends Phaser.Scene {
  private tracker!: GameSessionTracker
  private backendSync!: GameBackendSync
  private studentId = ''
  private learningCycleId = ''
  private isFreshStart = false
  private hasAttemptedCurrentStep = false
  private levels: EquationVariant[] = []
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
  private currentLevelIndex = 0
  private currentStepIndex = 0
  private showSummary = false
  private isCompactLayout = false
  private reducedMotion = false
  private stars: number[] = []
  private balanceScale!: BalanceScale
  private progressItems: Phaser.GameObjects.GameObject[] = []
  private rewardText!: Phaser.GameObjects.Text

  // The layout is drawn in a fixed design space (800x600 wide, 420x760
  // compact) and the camera zooms to fit whatever size the canvas is, so
  // the whole game — including the Next button and stars — is always
  // visible and grows on large screens.
  private get viewWidth(): number {
    return this.isCompactLayout ? DESIGN.compact.width : DESIGN.wide.width
  }

  private get viewHeight(): number {
    return this.isCompactLayout ? DESIGN.compact.height : DESIGN.wide.height
  }

  private fitCamera(): void {
    const zoom = Math.min(this.scale.width / this.viewWidth, this.scale.height / this.viewHeight)
    const camera = this.cameras.main
    camera.setZoom(this.isCompactLayout ? Math.min(zoom, 1.3) : zoom)
    camera.centerOn(this.viewWidth / 2, this.viewHeight / 2)
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
  private dropZoneOutline!: Phaser.GameObjects.Rectangle
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
    this.tracker = data.tracker ?? new GameSessionTracker()
    // A resize rebuild always passes backendSync through; only a genuine
    // first load leaves it undefined, which is how we know not to start a
    // second backend session or re-send GAME_STARTED on every resize.
    this.isFreshStart = data.backendSync === undefined
    this.backendSync = data.backendSync ?? new GameBackendSync()
    this.studentId = data.studentId ?? getOrCreateStudentId()
    this.learningCycleId = data.learningCycleId ?? crypto.randomUUID()
    this.levels = data.levels ?? []
    this.currentLevelIndex = data.levelIndex ?? 0
    this.currentStepIndex = data.stepIndex ?? 0
    this.showSummary = data.showSummary ?? false
    this.stars = data.stars ?? []
  }

  create(): void {
    this.isCompactLayout = this.scale.width < 620
    this.fitCamera()
    this.reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true

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
      // can't create a second backend session. The display list was just
      // cleared by this restart, so always repaint the loading screen and
      // start a fresh load for *this* cycle — loadAssessmentVariants()
      // checks sceneGeneration before acting, so an earlier cycle's load
      // that resolves late is a safe no-op rather than a second render.
      if (this.isFreshStart) {
        this.backendSync.startSession({
          studentId: this.studentId,
          conceptId: CONCEPT_ID,
          learningCycleId: this.learningCycleId,
          assessmentPhase: 'pre_tutor',
        })
      }
      this.createLoadingScreen()
      void this.loadAssessmentVariants()
    }

    // Recreate this scene after an orientation or browser-size change, so
    // the layout can switch cleanly between desktop and mobile. Progress
    // and analytics are passed back in through init(), above.
    this.scale.on(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.scale.off(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    })
    this.events.once(Phaser.Scenes.Events.DESTROY, () => {
      this.isDestroyed = true
    })
  }

  private handleResize(): void {
    this.scene.restart({
      tracker: this.tracker,
      backendSync: this.backendSync,
      studentId: this.studentId,
      learningCycleId: this.learningCycleId,
      levels: this.levels,
      levelIndex: this.currentLevelIndex,
      stepIndex: this.currentStepIndex,
      showSummary: this.showSummary,
      stars: this.stars,
    } satisfies SceneInitData)
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

    let usageCounts: Record<string, number> = {}
    try {
      const usage = await getVariantUsage(this.studentId, CONCEPT_ID)
      usageCounts = usage.usage_counts
    } catch (error) {
      console.warn('[game] failed to load variant usage, assuming none yet', error)
    }

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

    this.levels = selectAssessmentVariants(usageCounts)
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
        fontSize: this.isCompactLayout ? '14px' : '15px',
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
        fontSize: '14px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.viewWidth - 24 },
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
    this.progressItems = []

    const count = this.levels.length
    const spacing = Math.min(64, (this.viewWidth - 48) / Math.max(1, count - 1))
    const startX = this.viewWidth / 2 - (spacing * (count - 1)) / 2
    const y = this.layout.pathY

    for (let i = 0; i < count; i += 1) {
      const x = startX + i * spacing
      const done = this.stars[i] !== undefined
      const current = i === this.currentLevelIndex && !done

      if (i > 0) {
        this.progressItems.push(
          this.add.rectangle(x - spacing / 2, y, spacing - 22, 4, done ? 0xf5b301 : 0xd0ccd6),
        )
      }
      const node = this.add
        .circle(x, y, 13, done ? 0xf5b301 : 0xf4f3ec)
        .setStrokeStyle(current ? 4 : 2, current ? COLORS.buttonBorderHover : COLORS.buttonBorder)
      const label = this.add
        .text(x, y, String(i + 1), {
          fontFamily: FONT_FAMILY,
          fontSize: '14px',
          fontStyle: 'bold',
          color: COLORS.text,
        })
        .setOrigin(0.5)
      this.progressItems.push(node, label)
      if (done) {
        this.progressItems.push(
          this.add
            .text(x, y + 20, formatStars(this.stars[i]), {
              fontFamily: FONT_FAMILY,
              fontSize: '10px',
              color: '#b07d00',
            })
            .setOrigin(0.5),
        )
      }
    }
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
        color: '#b07d00',
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
    const width = Math.min(240, this.viewWidth - 48)
    const height = this.layout.dropH
    this.dropZoneX = this.viewWidth / 2
    this.dropZoneY = this.layout.dropY

    this.dropZoneOutline = this.add
      .rectangle(this.dropZoneX, this.dropZoneY, width, height, 0xffffff, 0)
      .setStrokeStyle(3, COLORS.buttonBorder)

    this.dropZoneLabel = this.add
      .text(this.dropZoneX, this.dropZoneY, stacked(GAME_TEXT.dropHere), {
        fontFamily: FONT_FAMILY,
        fontSize: '13px',
        color: COLORS.text,
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

    const choices = this.currentStep.choices
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

    const buttonWidth = 140
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
    x: number,
    y: number,
    width: number,
    height: number,
    label: string,
    onClick: () => void,
    fill: number = COLORS.buttonFill,
    // Optional second line under the label (the Sinhala wording).
    subLabel?: string,
  ): Phaser.GameObjects.Container {
    const background = this.add
      .rectangle(0, 0, width, height, fill)
      .setStrokeStyle(3, COLORS.buttonBorder)

    const text = this.add
      .text(0, subLabel ? -9 : 0, label, {
        fontFamily: FONT_FAMILY,
        fontSize: subLabel ? '20px' : '26px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    const children: Phaser.GameObjects.GameObject[] = [background, text]
    if (subLabel) {
      children.push(
        this.add
          .text(0, 14, subLabel, {
            fontFamily: FONT_FAMILY,
            fontSize: '14px',
            color: COLORS.text,
            padding: { top: 3, bottom: 3 },
          })
          .setOrigin(0.5),
      )
    }

    const container = this.add.container(x, y, children)

    // The hit area has to be centered on the container's own (0, 0), the
    // same way the rectangle and text above are, otherwise clicks land on
    // the wrong spot relative to what is drawn on screen.
    container.setInteractive({
      hitArea: new Phaser.Geom.Rectangle(-width / 2, -height / 2, width, height),
      hitAreaCallback: Phaser.Geom.Rectangle.Contains,
      useHandCursor: true,
    })

    // Hovering swaps the border color so there's a visible response to the
    // mouse that doesn't rely on anything but outline/shape.
    container.on('pointerover', () => background.setStrokeStyle(3, COLORS.buttonBorderHover))
    container.on('pointerout', () => background.setStrokeStyle(3, COLORS.buttonBorder))

    // Clicking/tapping fires on release, not on press. This matters for the
    // operation cards: a drag also starts with a press, so if we answered on
    // press, picking a card up to drag it would immediately count as a
    // click. Checking the "dragging" flag (set in createDragListeners) tells
    // a genuine tap apart from the end of a drag — a tap never sets it.
    container.on('pointerdown', () => container.setData('dragging', false))
    container.on('pointerup', () => {
      if (!container.getData('dragging')) onClick()
    })

    return container
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
      44,
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
        (step: LevelStep) => step.choices.find((choice) => choice.isCorrect)?.label ?? '',
      ),
    )
    this.tracker.beginStep()

    this.hasAnsweredStepCorrectly = false
    this.hasAttemptedCurrentStep = false
    this.balanceScale.setTaskComplete(false)
    this.rewardText.setAlpha(0)
    this.updateProgressPath()
    const equationBeforeThisStep =
      this.currentStepIndex === 0
        ? this.currentLevel.startingEquation
        : this.currentLevel.steps[this.currentStepIndex - 1].resultText
    this.backendSync.sendEvent(this.currentLevel.variantId, 'QUESTION_SHOWN', {
      ...this.stepEvidence(),
      equation_shown: equationBeforeThisStep,
      choices_offered: this.currentStep.choices.map((c) => c.label),
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
    if (this.hasAttemptedCurrentStep) {
      this.backendSync.sendEvent(taskId, 'RETRY_STARTED')
    }
    this.hasAttemptedCurrentStep = true
    this.tracker.recordAttempt(this.currentStepIndex)
    const answerEvidence = {
      ...this.stepEvidence(),
      selected_choice: choice.label,
      is_correct: choice.isCorrect,
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
    this.tracker.completeSession()
    const summary = this.tracker.getSummary()
    // Still logged locally for development visibility — the backend now
    // also has the same session via gameplay_events/game_task_attempts.
    console.log('Game session summary:', summary)

    this.backendSync.sendEvent(null, 'SESSION_ENDED')
    await this.backendSync.completeSession()

    this.scene.restart({
      tracker: this.tracker,
      backendSync: this.backendSync,
      studentId: this.studentId,
      learningCycleId: this.learningCycleId,
      levels: this.levels,
      levelIndex: this.currentLevelIndex,
      stepIndex: this.currentStepIndex,
      showSummary: true,
      stars: this.stars,
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
        color: '#b07d00',
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
    const lineHeight = this.isCompactLayout ? 24 : 17
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
      this.add.rectangle(0, 0, 210, 46, COLORS.buttonFill).setStrokeStyle(2, COLORS.buttonBorder),
      toggleLabel,
    ])
    toggle.setInteractive({
      hitArea: new Phaser.Geom.Rectangle(-105, -23, 210, 46),
      hitAreaCallback: Phaser.Geom.Rectangle.Contains,
      useHandCursor: true,
    })
    toggle.on('pointerup', () => {
      open = !open
      toggleLabel.setText(stacked(open ? GAME_TEXT.hideDetails : GAME_TEXT.showDetails))
      detailsTexts.forEach((text) => text.setVisible(open))
    })
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
  }
}

// A soft tint per operation type. Colour only supplements the symbol on the
// card, which always stays visible.
function operationFill(label: string): number {
  switch (label.trim().charAt(0)) {
    case '+':
      return 0xdff5e6
    case '-':
    case '−':
      return 0xffe8d1
    case '×':
      return 0xdbeafe
    case '÷':
      return 0xfce1f0
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
