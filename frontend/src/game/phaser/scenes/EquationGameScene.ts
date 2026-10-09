import Phaser from 'phaser'
import type { LevelStep, OperationChoice } from '../../data/equationLevels'
import type { EquationVariant } from '../../data/equationVariants'
import { selectAssessmentVariants } from '../../data/variantSelection'
import { GameSessionTracker } from '../../analytics/GameSessionTracker'
import { GameBackendSync } from '../../api/gameBackendSync'
import { getVariantUsage } from '../../api/gameApi'
import type { GameResultResponse } from '../../api/gameApi'
import { getOrCreateStudentId } from '../../identity'

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

// Phaser's default text font is "Courier" if you don't set one — this
// matches the rest of the site instead of looking like a typewriter.
const FONT_FAMILY = 'system-ui, "Segoe UI", Roboto, sans-serif'

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
  }

  create(): void {
    this.isCompactLayout = this.scale.width < 620

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
    } satisfies SceneInitData)
  }

  // ---- Gameplay screen ----------------------------------------------

  // Shown only while loadAssessmentVariants() is waiting on the backend —
  // the one place in this scene where we deliberately make the learner
  // wait on the network, because it decides what content to show next.
  private createLoadingScreen(): void {
    this.loadingText = this.add
      .text(this.scale.width / 2, this.scale.height / 2, 'Preparing your assessment…', {
        fontFamily: FONT_FAMILY,
        fontSize: '20px',
        color: COLORS.text,
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
    this.createEquation()
    this.createDropZone()
    this.createFeedbackText()
    this.createHintArea()
    this.createNextButton()
    this.createDragListeners()

    this.displayCurrentStep()
  }

  private createTitleAndInstructions(): void {
    const centerX = this.scale.width / 2

    this.add
      .text(centerX, this.isCompactLayout ? 28 : 30, 'Balance the Equation', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '26px' : '30px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    this.add
      .text(
        centerX,
        this.isCompactLayout ? 62 : 64,
        'Choose the operation that keeps the equation balanced.',
        {
          fontFamily: FONT_FAMILY,
          fontSize: '16px',
          color: COLORS.text,
          align: 'center',
          wordWrap: { width: Math.max(260, this.scale.width - 40) },
        },
      )
      .setOrigin(0.5)
  }

  private createLevelIndicator(): void {
    this.levelIndicatorText = this.add
      .text(this.scale.width / 2, this.isCompactLayout ? 100 : 98, '', {
        fontFamily: FONT_FAMILY,
        fontSize: '16px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)
  }

  private updateLevelIndicator(): void {
    let text = `Level ${this.currentLevelIndex + 1} of ${this.levels.length}`
    if (this.currentLevel.steps.length > 1) {
      text += ` · Step ${this.currentStepIndex + 1} of ${this.currentLevel.steps.length}`
    }
    this.levelIndicatorText.setText(text)
  }

  private createEquation(): void {
    this.equationText = this.add
      .text(this.scale.width / 2, this.isCompactLayout ? 150 : 155, '', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '42px' : '48px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)
  }

  // Keep equations on one readable line. The balancing step text is much
  // longer than the equation itself, so compact screens need a smaller
  // font for that step. Short equations still use the normal large font.
  private setEquationDisplay(value: string): void {
    const preferredFontSize = this.isCompactLayout ? 42 : 48
    const minimumFontSize = 20
    const availableWidth = this.scale.width - 32

    this.equationText.setFontSize(preferredFontSize)
    this.equationText.setText(value)

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
    const width = Math.min(240, this.scale.width - 48)
    const height = this.isCompactLayout ? 60 : 64
    this.dropZoneX = this.scale.width / 2
    this.dropZoneY = this.isCompactLayout ? 218 : 225

    this.dropZoneOutline = this.add
      .rectangle(this.dropZoneX, this.dropZoneY, width, height, 0xffffff, 0)
      .setStrokeStyle(3, COLORS.buttonBorder)

    this.dropZoneLabel = this.add
      .text(this.dropZoneX, this.dropZoneY, 'Drop operation here', {
        fontFamily: FONT_FAMILY,
        fontSize: '16px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: width - 20 },
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
    const centerX = this.scale.width / 2

    if (this.isCompactLayout) {
      const gap = 16
      const sidePadding = 20
      const buttonWidth = Math.min(180, (this.scale.width - sidePadding * 2 - gap) / 2)
      const buttonHeight = 72
      const leftX = centerX - buttonWidth / 2 - gap / 2
      const rightX = centerX + buttonWidth / 2 + gap / 2
      const row1Y = 300
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
        )
        this.makeCardDraggable(button, choice)
        this.operationButtons.push(button)
      })
      return
    }

    const buttonWidth = 140
    const buttonHeight = 70
    const gap = 24
    const rowY = 305

    // Wide screens have enough room to show all four choices in one row.
    const totalWidth = choices.length * buttonWidth + (choices.length - 1) * gap
    const startX = centerX - totalWidth / 2 + buttonWidth / 2

    choices.forEach((choice, index) => {
      const x = startX + index * (buttonWidth + gap)
      const button = this.createButton(x, rowY, buttonWidth, buttonHeight, choice.label, () =>
        this.handleOperationSelection(choice, button),
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
  ): Phaser.GameObjects.Container {
    const background = this.add
      .rectangle(0, 0, width, height, COLORS.buttonFill)
      .setStrokeStyle(3, COLORS.buttonBorder)

    const text = this.add
      .text(0, 0, label, {
        fontFamily: FONT_FAMILY,
        fontSize: '26px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    const container = this.add.container(x, y, [background, text])

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
      .text(this.scale.width / 2, this.isCompactLayout ? 530 : 455, '', {
        fontFamily: FONT_FAMILY,
        fontSize: '22px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)
      .setAlpha(0)
  }

  private createHintArea(): void {
    this.hintButton = this.createButton(
      this.scale.width / 2,
      this.isCompactLayout ? 460 : 380,
      this.isCompactLayout ? 150 : 140,
      44,
      '💡 Hint',
      () => this.handleHintClick(),
    )

    this.hintText = this.add
      .text(this.scale.width / 2, this.isCompactLayout ? 498 : 420, '', {
        fontFamily: FONT_FAMILY,
        fontSize: '15px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: Math.max(240, this.scale.width - 60) },
      })
      .setOrigin(0.5)
      .setAlpha(0)
  }

  private createNextButton(): void {
    this.nextButton = this.createButton(
      this.scale.width / 2,
      this.isCompactLayout ? 585 : 515,
      180,
      56,
      'Next ▶',
      () => this.advanceToNextLevel(),
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
      this.showCorrectFeedback(button)
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
    this.hintText.setText(this.currentStep.hint)
    this.tweens.add({ targets: this.hintText, alpha: 1, duration: 200 })
  }

  private showCorrectFeedback(button: Phaser.GameObjects.Container): void {
    this.hasAnsweredStepCorrectly = true
    this.disableAllOperationButtons()
    this.hintButton.disableInteractive()

    const step = this.currentStep
    const isLastStepOfLevel = this.currentStepIndex === this.currentLevel.steps.length - 1
    const isLastLevel = this.currentLevelIndex === this.levels.length - 1

    // Snap the winning card into the drop zone, whether it got there by
    // being dragged or just clicked.
    this.tweens.add({
      targets: button,
      x: this.dropZoneX,
      y: this.dropZoneY,
      duration: 250,
      ease: 'Quad.easeOut',
    })
    this.tweens.add({ targets: this.dropZoneLabel, alpha: 0, duration: 150 })

    this.feedbackText.setText('✓ Correct!')
    this.feedbackText.setColor(COLORS.correctText)
    this.tweens.add({ targets: this.feedbackText, alpha: 1, duration: 300 })

    // Step 1: show the same operation applied to both sides...
    this.time.delayedCall(600, () => {
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

      if (isLastLevel) {
        this.backendSync.sendEvent(taskId, 'GAME_COMPLETED')
        this.finishSession()
        return
      }

      this.nextButton.setInteractive()
      this.tweens.add({ targets: this.nextButton, alpha: 1, duration: 300 })
    })
  }

  private showWrongFeedback(button: Phaser.GameObjects.Container): void {
    this.feedbackText.setText('✕ Try again')
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
    this.loadingText?.setText('Calculating your results…')
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

  private renderResultSummary(result: GameResultResponse): void {
    const centerX = this.scale.width / 2

    const lines = [
      'Linear Equations',
      'Pre-Tutor Assessment Complete',
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
    ]

    let y = this.isCompactLayout ? 90 : 110
    lines.forEach((line, index) => {
      const isHeading = index < 2
      this.add
        .text(centerX, y, line, {
          fontFamily: FONT_FAMILY,
          fontSize: isHeading
            ? this.isCompactLayout
              ? '22px'
              : '26px'
            : '18px',
          fontStyle: isHeading ? 'bold' : 'normal',
          color: COLORS.text,
        })
        .setOrigin(0.5)
      y += isHeading ? 36 : 32
    })
  }

  private renderFallbackSummary(): void {
    const centerX = this.scale.width / 2
    const summary = this.tracker.getSummary()
    const totalTime = summary.totalTimeSec !== null ? `${summary.totalTimeSec}s` : '—'

    const lines = [
      'Session Complete',
      `Levels Completed: ${summary.levelsCompleted} / ${this.levels.length}`,
      `Wrong Attempts: ${summary.totalWrongAttempts}`,
      `Hints Used: ${summary.totalHintsUsed}`,
      `Total Time: ${totalTime}`,
    ]

    let y = this.isCompactLayout ? 160 : 200
    lines.forEach((line, index) => {
      const isHeading = index === 0
      this.add
        .text(centerX, y, line, {
          fontFamily: FONT_FAMILY,
          fontSize: isHeading ? (this.isCompactLayout ? '28px' : '32px') : '20px',
          fontStyle: isHeading ? 'bold' : 'normal',
          color: COLORS.text,
        })
        .setOrigin(0.5)
      y += isHeading ? 64 : 40
    })
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
