import Phaser from 'phaser'
import type { EquationLevel, LevelStep, OperationChoice } from '../../data/equationLevels'
import { EQUATION_LEVELS } from '../../data/equationLevels'
import { GameSessionTracker } from '../../analytics/GameSessionTracker'

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

  private get currentLevel(): EquationLevel {
    return EQUATION_LEVELS[this.currentLevelIndex]
  }

  private get currentStep(): LevelStep {
    return this.currentLevel.steps[this.currentStepIndex]
  }

  // Phaser calls init() right before create(), with whatever data
  // scene.restart() was called with. This is how progress and the
  // analytics tracker survive a resize or the move to the summary screen,
  // instead of a fresh EquationGameScene starting from level 1 every time.
  init(data: SceneInitData): void {
    this.tracker = data.tracker ?? new GameSessionTracker()
    this.currentLevelIndex = data.levelIndex ?? 0
    this.currentStepIndex = data.stepIndex ?? 0
    this.showSummary = data.showSummary ?? false
  }

  create(): void {
    this.isCompactLayout = this.scale.width < 620

    if (this.showSummary) {
      this.createSessionSummaryScreen()
    } else {
      this.createGameplayScreen()
    }

    // Recreate this scene after an orientation or browser-size change, so
    // the layout can switch cleanly between desktop and mobile. Progress
    // and analytics are passed back in through init(), above.
    this.scale.on(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.scale.off(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    })
  }

  private handleResize(): void {
    this.scene.restart({
      tracker: this.tracker,
      levelIndex: this.currentLevelIndex,
      stepIndex: this.currentStepIndex,
      showSummary: this.showSummary,
    } satisfies SceneInitData)
  }

  // ---- Gameplay screen ----------------------------------------------

  private createGameplayScreen(): void {
    this.operationButtons = []
    this.hasAnsweredStepCorrectly = false

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
    let text = `Level ${this.currentLevelIndex + 1} of ${EQUATION_LEVELS.length}`
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
      this.currentLevel.id,
      this.currentLevel.concept,
      this.currentLevel.steps.map(
        (step) => step.choices.find((choice) => choice.isCorrect)?.label ?? '',
      ),
    )
    this.tracker.beginStep()

    this.hasAnsweredStepCorrectly = false
    this.updateLevelIndicator()

    const equationBeforeThisStep =
      this.currentStepIndex === 0
        ? this.currentLevel.startingEquation
        : this.currentLevel.steps[this.currentStepIndex - 1].resultText
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

    if (choice.isCorrect) {
      this.showCorrectFeedback(button)
    } else {
      // This is where wrong attempts are recorded — only for a genuine
      // click or a card actually dropped on the zone, never for just
      // dragging a card around.
      this.tracker.recordWrongAttempt(this.currentStepIndex)
      this.showWrongFeedback(button)
    }
  }

  private handleHintClick(): void {
    // Hints can be requested more than once; every request is recorded.
    this.tracker.recordHintUsed(this.currentStepIndex)
    this.hintText.setText(this.currentStep.hint)
    this.tweens.add({ targets: this.hintText, alpha: 1, duration: 200 })
  }

  private showCorrectFeedback(button: Phaser.GameObjects.Container): void {
    this.hasAnsweredStepCorrectly = true
    this.disableAllOperationButtons()
    this.hintButton.disableInteractive()

    const step = this.currentStep
    const isLastStepOfLevel = this.currentStepIndex === this.currentLevel.steps.length - 1
    const isLastLevel = this.currentLevelIndex === EQUATION_LEVELS.length - 1

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
    // is also when the step is marked complete for analytics.
    this.time.delayedCall(1400, () => {
      this.tweens.add({
        targets: this.equationText,
        scale: 1.15,
        duration: 200,
        yoyo: true,
        onComplete: () => this.setEquationDisplay(step.resultText),
      })
      this.tracker.completeStep(this.currentStepIndex)
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

  private finishSession(): void {
    this.tracker.completeSession()
    const summary = this.tracker.getSummary()
    // Logged so the full structured analytics can be inspected during
    // development. A later milestone sends this to the backend instead.
    console.log('Game session summary:', summary)

    this.scene.restart({
      tracker: this.tracker,
      levelIndex: this.currentLevelIndex,
      stepIndex: this.currentStepIndex,
      showSummary: true,
    } satisfies SceneInitData)
  }

  // ---- Session summary screen ----------------------------------------

  private createSessionSummaryScreen(): void {
    const centerX = this.scale.width / 2
    const summary = this.tracker.getSummary()
    const totalTime = summary.totalTimeSec !== null ? `${summary.totalTimeSec}s` : '—'

    const lines = [
      'Session Complete',
      `Levels Completed: ${summary.levelsCompleted} / ${EQUATION_LEVELS.length}`,
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
