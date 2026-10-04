import Phaser from 'phaser'

// --- EDIT HERE to change the equation for Milestone 1 ---
const EQUATION_TEXT = 'x + 3 = 7'
const EQUATION_STEP_TEXT = 'x + 3 - 3 = 7 - 3'
const SOLVED_TEXT = 'x = 4'

// --- EDIT HERE to change the four answer choices ---
// Exactly one of these should have isCorrect: true.
interface OperationChoice {
  label: string
  isCorrect: boolean
}

const OPERATION_CHOICES: OperationChoice[] = [
  { label: '-3', isCorrect: true },
  { label: '+3', isCorrect: false },
  { label: '×3', isCorrect: false },
  { label: '÷3', isCorrect: false },
]

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

// A Phaser "Scene" is one self-contained screen of the game: it has its own
// create() (build everything once) and can react to input, timers and
// tweens (animations) after that. This scene is the whole Milestone 1 game.
export class EquationGameScene extends Phaser.Scene {
  private equationText!: Phaser.GameObjects.Text
  private feedbackText!: Phaser.GameObjects.Text
  private nextButton!: Phaser.GameObjects.Container
  private operationButtons: Phaser.GameObjects.Container[] = []
  private hasAnsweredCorrectly = false
  private isCompactLayout = false

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

  // Phaser calls create() exactly once, right after the scene starts.
  // Everything the player sees gets built here.
  create(): void {
    this.operationButtons = []
    this.hasAnsweredCorrectly = false
    this.isCompactLayout = this.scale.width < 620
    this.createTitleAndInstructions()
    this.createEquation()
    this.createDropZone()
    this.createOperationButtons()
    this.createFeedbackText()
    this.createNextButton()
    this.createDragListeners()

    // Recreate this small scene after an orientation or browser-size change.
    // This lets the buttons switch cleanly between desktop and mobile layouts.
    this.scale.on(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.scale.off(Phaser.Scale.Events.RESIZE, this.handleResize, this)
    })
  }

  private createTitleAndInstructions(): void {
    const centerX = this.scale.width / 2

    this.add
      .text(centerX, this.isCompactLayout ? 32 : 36, 'Balance the Equation', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '28px' : '32px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    this.add
      .text(
        centerX,
        this.isCompactLayout ? 76 : 78,
        'Choose the operation that keeps the equation balanced.',
        {
          fontFamily: FONT_FAMILY,
          fontSize: '18px',
          color: COLORS.text,
          align: 'center',
          wordWrap: { width: Math.max(260, this.scale.width - 40) },
        },
      )
      .setOrigin(0.5)
  }

  private createEquation(): void {
    this.equationText = this.add
      .text(this.scale.width / 2, this.isCompactLayout ? 150 : 155, EQUATION_TEXT, {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '42px' : '48px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    this.setEquationDisplay(EQUATION_TEXT)
  }

  // Keep equations on one readable line. The balancing step is much longer
  // than the original equation, so compact screens need a smaller font for
  // that step. Short equations still use the normal large font.
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
    const height = this.isCompactLayout ? 64 : 70
    this.dropZoneX = this.scale.width / 2
    this.dropZoneY = this.isCompactLayout ? 221 : 235

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

  private createOperationButtons(): void {
    const centerX = this.scale.width / 2

    if (this.isCompactLayout) {
      const gap = 16
      const sidePadding = 20
      const buttonWidth = Math.min(180, (this.scale.width - sidePadding * 2 - gap) / 2)
      const buttonHeight = 72
      const leftX = centerX - buttonWidth / 2 - gap / 2
      const rightX = centerX + buttonWidth / 2 + gap / 2
      const row1Y = 307
      const row2Y = row1Y + buttonHeight + 16
      const positions = [
        { x: leftX, y: row1Y },
        { x: rightX, y: row1Y },
        { x: leftX, y: row2Y },
        { x: rightX, y: row2Y },
      ]

      OPERATION_CHOICES.forEach((choice, index) => {
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

    // Wide screens have enough room to show all four choices in one row.
    const totalWidth = OPERATION_CHOICES.length * buttonWidth + (OPERATION_CHOICES.length - 1) * gap
    const startX = centerX - totalWidth / 2 + buttonWidth / 2

    const rowY = 330

    OPERATION_CHOICES.forEach((choice, index) => {
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

  // These four listeners are what make dragging work. They live on
  // `this.input` (the scene's input plugin) rather than on each card,
  // because Phaser reports *which* card is being dragged as an argument,
  // so one shared listener is simpler than repeating the same code on
  // every card.
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
    this.input.on('dragenter', (_pointer: Phaser.Input.Pointer, _gameObject: Phaser.GameObjects.Container, zone: Phaser.GameObjects.Zone) => {
      if (zone === this.dropZone) this.dropZoneOutline.setStrokeStyle(4, COLORS.buttonBorderHover)
    })

    this.input.on('dragleave', (_pointer: Phaser.Input.Pointer, _gameObject: Phaser.GameObjects.Container, zone: Phaser.GameObjects.Zone) => {
      if (zone === this.dropZone) this.dropZoneOutline.setStrokeStyle(3, COLORS.buttonBorder)
    })

    // This is where a correct or incorrect DROP is detected: the card was
    // released while over the drop zone. We read back which choice it was
    // (stored in makeCardDraggable) and hand it to the exact same
    // handleOperationSelection() that the click/tap path uses.
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
        fontSize: '28px',
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
      .text(this.scale.width / 2, this.isCompactLayout ? 465 : 400, '', {
        fontFamily: FONT_FAMILY,
        fontSize: '26px',
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)
      .setAlpha(0)
  }

  private createNextButton(): void {
    this.nextButton = this.createButton(
      this.scale.width / 2,
      this.isCompactLayout ? 530 : 470,
      180,
      64,
      'Next ▶',
      () => this.resetLevel(),
    )
    this.nextButton.setAlpha(0)
    this.nextButton.disableInteractive()
  }

  private handleOperationSelection(
    choice: OperationChoice,
    button: Phaser.GameObjects.Container,
  ): void {
    // Once the correct answer has been picked, ignore any further clicks
    // (this is the "disable additional answer selection" requirement).
    if (this.hasAnsweredCorrectly) return

    if (choice.isCorrect) {
      this.showCorrectFeedback(button)
    } else {
      this.showWrongFeedback(button)
    }
  }

  private showCorrectFeedback(button: Phaser.GameObjects.Container): void {
    this.hasAnsweredCorrectly = true
    this.disableAllOperationButtons()

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
      this.setEquationDisplay(EQUATION_STEP_TEXT)
    })

    // Step 2: ...then settle on the final answer, with a little "pop" tween
    // so the change is noticeable without relying on anything audible.
    this.time.delayedCall(1400, () => {
      this.tweens.add({
        targets: this.equationText,
        scale: 1.15,
        duration: 200,
        yoyo: true,
        onComplete: () => this.setEquationDisplay(SOLVED_TEXT),
      })
    })

    // Step 3: reveal the Next button.
    this.time.delayedCall(2000, () => {
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

  private handleResize(): void {
    this.scene.restart()
  }

  // Puts the scene back to its starting state so the same level can be
  // played again. A later milestone can load a different equation here
  // instead of always resetting to the same one.
  private resetLevel(): void {
    this.hasAnsweredCorrectly = false
    this.setEquationDisplay(EQUATION_TEXT)
    this.equationText.setScale(1)

    this.feedbackText.setText('')
    this.feedbackText.setAlpha(0)

    this.nextButton.setAlpha(0)
    this.nextButton.disableInteractive()

    this.dropZoneLabel.setAlpha(1)
    this.dropZoneOutline.setStrokeStyle(3, COLORS.buttonBorder)

    // Move every card back to where it started (only the winning one will
    // have actually moved, but resetting all of them is simplest) and
    // re-enable both the click and the drag path.
    this.operationButtons.forEach((button) => {
      button.setPosition(button.getData('originX') as number, button.getData('originY') as number)
      button.setData('dragging', false)
      // Calling setInteractive() with no arguments re-enables a button using
      // the hit area it was already given in createButton().
      button.setInteractive()
    })
  }
}
