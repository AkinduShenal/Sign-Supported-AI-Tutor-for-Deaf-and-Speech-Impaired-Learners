import Phaser from 'phaser'
import type { EquationVariant } from '../../data/equationVariants'
import type { GameSessionTracker } from '../../analytics/GameSessionTracker'
import { GameBackendSync } from '../../api/gameBackendSync'
import { getVariantUsage } from '../../api/gameApi'
import type { GameResultResponse } from '../../api/gameApi'
import { requireCollectionStudent } from '../../collectionIdentity'
import { primaryGameText } from '../../gameLanguage'
import type { Bilingual } from '../gameText'
import { GameSession } from '../../session/GameSession'
import type { GameType } from '../../types'
import { HangmanFigure } from '../HangmanFigure'
import {
  MAX_WRONG_SUBMISSIONS,
  appendDigit,
  appendMinus,
  backspace as backspaceBuffer,
  isSubmittable,
  starsForHangman,
  submitAnswer,
} from '../hangmanLogic'
import { MAX_STARS_PER_TASK } from '../stars'
import {
  FONT_FAMILY,
  GAME_TEXT,
  GAME_TYPE_TEXT,
  SINHALA_TEXT,
  bilingualHint,
  difficultyText,
  inline,
  stacked,
} from '../gameText'
import { GAME_THEME as T, cssColor } from '../theme/gameTheme'
import { RoundedPanel, backgroundTouchScroll, bilingualPair, bindLanguageText, crispSceneText, gameButton, progressStepper, watchViewportSize } from '../theme/gameUi'
import { designSize, fitCameraToDesign, isCompactScreen, prefersReducedMotion } from '../viewport'

const COLORS = {
  text: cssColor(T.color.text),
  buttonFill: T.color.surfaceSoft,
  buttonBorder: T.color.border,
  buttonBorderHover: T.color.primary,
  keyFill: T.color.surface,
  correctText: cssColor(T.color.success),
  incorrectText: cssColor(T.color.error),
}

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '0', '⌫'] as const

// Wide: maths on the left, the Hangman figure beside it on the right
// (Milestone 4 §4). Compact: the figure sits above the maths, which is
// stacked full-width underneath (Milestone 4 §20).
const LAYOUTS = {
  wide: {
    mathCenterX: 262, figureCenterX: 705, figureBaseY: 620, figureHeight: 403,
    titleY: 24, titleSecondaryY: 62, progressY: 103, equationY: 200, equationSize: 35, instructionY: 244,
    answerY: 301, answerSize: 32,
    // attemptsY sits above feedbackY (not below, as it did before) because a
    // two-line hint in the feedback/hint slot could otherwise run into it —
    // see the Hangman Tuning Lab mockup this was approved from.
    attemptsY: 342, feedbackY: 392,
    keyTopY: 444, keyW: 86, keyH: 64, keyGapX: 12, keyGapY: 8,
    submitY: 738, hintY: 807, nextY: 808,
  },
  compact: {
    mathCenterX: 210, figureCenterX: 210, figureBaseY: 374, figureHeight: 154,
    titleY: 92, titleSecondaryY: 128, progressY: 166, equationY: 402, equationSize: 34, instructionY: 449,
    answerY: 517, answerSize: 32, feedbackY: 584, attemptsY: 634,
    keyTopY: 689, keyW: 88, keyH: 68, keyGapX: 12, keyGapY: 4,
    submitY: 988, hintY: 1072, nextY: 1072,
  },
}

// Data passed when this scene starts or restarts (mirrors
// EquationGameScene's SceneInitData). From Game Selection only `gameType`
// is given, so a brand-new GameSession is created; a resize or the move to
// the summary screen hand the existing one back so progress is never lost.
interface SceneInitData {
  gameType?: GameType
  session?: GameSession
  questionIndex?: number
  showSummary?: boolean
}

// Milestone 4: Hangman. The learner solves the same Easy/Medium/Hard
// variants as Drag & Drop (data/equationVariants.ts) but submits only the
// final value of x, via a number keypad, instead of choosing an operation.
// The figure hangs from a bar by both hands; MAX_WRONG_SUBMISSIONS (10)
// wrong submissions on one question slip every finger and the figure falls,
// failing that question — the figure never advances on a correct answer or
// a hint (Milestone 4 §7-§11, revised grip-and-fall design).
export class HangmanGameScene extends Phaser.Scene {
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
  private get currentIndex(): number {
    return this.session.levelIndex
  }
  private set currentIndex(value: number) {
    this.session.levelIndex = value
  }
  private get stars(): number[] {
    return this.session.stars
  }

  // Same staleness-guard pattern as EquationGameScene.ts — see its comments
  // for the full rationale (React StrictMode double-mount + Phaser's
  // auto-RESIZE racing the variant-usage fetch).
  private sceneGeneration = 0
  private isDestroyed = false
  private loadingText: Phaser.GameObjects.Text | null = null
  private showSummary = false
  private isCompactLayout = false
  private reducedMotion = false

  // Per-question input state. Reset by displayCurrentQuestion(); never
  // carries analytics (those live in this.tracker, which survives a resize
  // because it lives on this.session, not on this scene instance).
  private answerBuffer = ''
  private locked = false
  // The hint text has its own fade-out timer (handleHintClick), independent
  // of the feedback text. Tracked here so a submission that resolves before
  // that timer fires can clear it immediately instead of leaving it to
  // visually collide with the "Correct!"/"Question Failed" feedback.
  private hintLine: Phaser.GameObjects.Text | null = null

  private figure!: HangmanFigure
  private progressItems: Phaser.GameObjects.GameObject[] = []
  private progressText!: Phaser.GameObjects.Text
  private equationText!: Phaser.GameObjects.Text
  private answerText!: Phaser.GameObjects.Text
  private feedbackText!: Phaser.GameObjects.Text
  private attemptsText!: Phaser.GameObjects.Text
  private hintButton!: Phaser.GameObjects.Container
  private submitButton!: Phaser.GameObjects.Container
  private nextButton!: Phaser.GameObjects.Container
  private keyButtons: Phaser.GameObjects.Container[] = []

  private get viewWidth(): number {
    return designSize(this.isCompactLayout).width
  }

  private get viewHeight(): number {
    return designSize(this.isCompactLayout).height
  }

  private get layout() {
    return this.isCompactLayout ? LAYOUTS.compact : LAYOUTS.wide
  }

  private get currentVariant(): EquationVariant {
    return this.levels[this.currentIndex]
  }

  constructor() {
    super({ key: 'HangmanGameScene' })
  }

  init(data: SceneInitData): void {
    this.sceneGeneration += 1
    this.session =
      data.session ??
      new GameSession({
        gameType: data.gameType ?? 'hangman',
        studentId: requireCollectionStudent(),
        backendSync: new GameBackendSync(),
      })
    this.currentIndex = data.questionIndex ?? this.currentIndex
    this.showSummary = data.showSummary ?? false
  }

  create(): void {
    this.isCompactLayout = isCompactScreen(this)
    fitCameraToDesign(this, this.isCompactLayout)
    crispSceneText(this)
    backgroundTouchScroll(this)
    this.reducedMotion = prefersReducedMotion()

    if (this.showSummary) {
      this.createSummaryScreen()
    } else if (this.levels.length > 0) {
      this.createGameplayScreen()
    } else {
      // See EquationGameScene.create() for why only a genuine fresh start
      // calls session.start() and why the load is re-kicked off on every
      // cycle regardless.
      this.session.start()
      this.createLoadingScreen()
      void this.loadAssessmentVariants()
    }

    watchViewportSize(this, () => this.handleResize())
    this.events.once(Phaser.Scenes.Events.DESTROY, () => {
      this.isDestroyed = true
    })
  }

  private handleResize(): void {
    // Preserve the answer buffer, hint state, and pending resolution timer.
    fitCameraToDesign(this, this.isCompactLayout)
  }

  // ---- Loading / variant selection ------------------------------------

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
    bindLanguageText(this.loadingText, () => stacked(GAME_TEXT.preparing))
  }

  // Same "maximum two uses" selection as Drag & Drop (Milestone 4 §2: no
  // separate Hangman question bank, same shared session/variant logic).
  private async loadAssessmentVariants(): Promise<void> {
    const generation = this.sceneGeneration

    const selected = await this.session.selectVariants((studentId, conceptId) =>
      getVariantUsage(studentId, conceptId).then((usage) => usage.usage_counts),
    )

    if (generation !== this.sceneGeneration || this.isDestroyed) return

    this.levels = selected
    this.createGameplayScreen()
  }

  // ---- Gameplay screen --------------------------------------------------

  private createGameplayScreen(): void {
    this.loadingText?.destroy()
    this.loadingText = null
    this.keyButtons = []

    const centerX = this.layout.mathCenterX

    if (!this.isCompactLayout) {
      new RoundedPanel(this, this.layout.mathCenterX, 500, 420, 660, T.color.surfaceSoft, T.color.border, T.radius.panel)
      new RoundedPanel(this, this.layout.figureCenterX, 445, 380, 470, T.color.surfaceSoft, T.color.border, T.radius.panel)
    }
    this.createMenuButton()

    bilingualPair(this, { x: this.viewWidth / 2, primaryY: this.layout.titleY, secondaryY: this.layout.titleSecondaryY,
      text: GAME_TYPE_TEXT.hangman.name, width: this.viewWidth - 40,
      primarySize: T.font.title, secondarySize: T.font.subtitle, color: COLORS.text })

    this.progressText = this.add
      .text(this.viewWidth / 2, this.layout.progressY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.caption}px`,
        color: cssColor(T.color.muted),
        align: 'center',
        wordWrap: { width: this.viewWidth - 40 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)

    this.figure = new HangmanFigure(this, {
      x: this.layout.figureCenterX,
      y: this.layout.figureBaseY,
      height: this.layout.figureHeight,
    })

    this.equationText = this.add
      .text(centerX, this.layout.equationY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: `${this.layout.equationSize}px`,
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    const instruction = this.add
      .text(centerX, this.layout.instructionY, stacked(GAME_TEXT.solveForX), {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.body}px`,
        color: cssColor(T.color.muted),
        align: 'center',
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
    bindLanguageText(instruction, () => stacked(GAME_TEXT.solveForX))

    new RoundedPanel(this, centerX, this.layout.answerY, 350, 64,
      T.color.surface, T.color.borderStrong, T.radius.tile)
    this.answerText = this.add
      .text(centerX, this.layout.answerY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: `${this.layout.answerSize}px`,
        fontStyle: 'bold',
        color: COLORS.text,
      })
      .setOrigin(0.5)

    this.feedbackText = this.add
      .text(centerX, this.layout.feedbackY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: this.isCompactLayout ? '17px' : '19px',
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.isCompactLayout ? this.viewWidth - 32 : 400 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
      .setAlpha(0)

    this.attemptsText = this.add
      .text(centerX, this.layout.attemptsY, '', {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.caption}px`,
        color: cssColor(T.color.muted),
        align: 'center',
        wordWrap: { width: this.isCompactLayout ? this.viewWidth - 32 : 400 },
      })
      .setOrigin(0.5)

    this.createKeypad()
    this.createSubmitButton()
    this.createHintButton()
    this.createNextButton()

    this.displayCurrentQuestion()
  }

  private createKeypad(): void {
    const layout = this.layout
    const cols = 3
    const totalWidth = cols * layout.keyW + (cols - 1) * layout.keyGapX
    const startX = layout.mathCenterX - totalWidth / 2 + layout.keyW / 2

    KEYS.forEach((key, index) => {
      const row = Math.floor(index / cols)
      const col = index % cols
      const x = startX + col * (layout.keyW + layout.keyGapX)
      const y = layout.keyTopY + row * (layout.keyH + layout.keyGapY)
      const button = this.createButton(
        x,
        y,
        layout.keyW,
        layout.keyH,
        key,
        () => this.handleKeyPress(key),
        COLORS.keyFill,
      )
      this.keyButtons.push(button)
    })
  }

  private createSubmitButton(): void {
    this.submitButton = this.createButton(
      this.layout.mathCenterX,
      this.layout.submitY,
      this.isCompactLayout ? 260 : 220,
      T.control.compactHeight,
      GAME_TEXT.submitAnswer.en,
      () => this.handleSubmit(),
      T.color.primary,
      GAME_TEXT.submitAnswer.si,
    )
  }

  private createHintButton(): void {
    this.hintButton = this.createButton(
      this.layout.mathCenterX,
      this.layout.hintY,
      this.isCompactLayout ? 150 : 140,
      60,
      `💡 ${GAME_TEXT.hint.en}`,
      () => this.handleHintClick(),
      COLORS.buttonFill,
      GAME_TEXT.hint.si,
    )
  }

  // A standing way out of an in-progress assessment, back to the Game
  // Selection hub — the same destination "Choose Another Game" goes to on
  // the summary screen, just reachable mid-question too. Left active
  // through every state (mid-question, falling, celebrating): leaving is
  // always allowed, unlike Submit/Hint/Next which lock while the current
  // answer is being resolved.
  private createMenuButton(): void {
    this.createButton(
      80,
      this.isCompactLayout ? 34 : 44,
      120,
      60,
      GAME_TEXT.menu.en,
      () => this.scene.start('GameSelectionScene'),
      COLORS.buttonFill,
      GAME_TEXT.menu.si,
    )
  }

  private createNextButton(): void {
    this.nextButton = this.createButton(
      this.layout.mathCenterX,
      this.layout.nextY,
      this.isCompactLayout ? 200 : 180,
      60,
      `${GAME_TEXT.next.en} ▶`,
      () => this.advanceToNextQuestion(),
      COLORS.buttonFill,
      GAME_TEXT.next.si,
    )
    this.nextButton.setAlpha(0)
    this.nextButton.disableInteractive()
  }

  // Reusable button, matching EquationGameScene.createButton(): a rectangle
  // with a label (and optional Sinhala sub-label) in one Container.
  private createButton(
    x: number, y: number, width: number, height: number, label: string,
    onClick: () => void, fill: number = COLORS.buttonFill, subLabel?: string,
  ): Phaser.GameObjects.Container {
    const kind = label === GAME_TEXT.menu.en ? 'quiet'
      : label === GAME_TEXT.submitAnswer.en || label === `${GAME_TEXT.next.en} ▶` ? 'primary' : 'secondary'
    return gameButton(this, { x, y, width, height, label, subLabel, onClick, kind,
      fill: kind === 'primary' ? T.color.primary : fill })
  }

  // ---- Per-question flow -------------------------------------------------

  private displayCurrentQuestion(): void {
    const variant = this.currentVariant
    // One Hangman question has no discrete steps, so it is tracked as a
    // single tracker "step" (index 0) representing the whole question —
    // reusing GameSessionTracker exactly as it already works, with no
    // changes to that shared class.
    this.tracker.startLevel(variant.variantId, variant.concept, ['solve_for_final_value'])
    this.tracker.beginStep()

    this.answerBuffer = ''
    this.locked = false
    this.figure.setGrip(0)
    this.clearHintLine()

    this.backendSync.sendEvent(variant.variantId, 'QUESTION_SHOWN', this.questionEvidence())

    this.updateProgressText()
    this.equationText.setText(variant.startingEquation)
    this.updateAnswerDisplay()
    bindLanguageText(this.feedbackText, () => '')
    this.feedbackText.setAlpha(0)
    bindLanguageText(this.attemptsText, () => '')
    this.setKeypadEnabled(true)
    this.submitButton.setAlpha(1)
    this.hintButton.setAlpha(1)
    this.hintButton.setInteractive()
    this.nextButton.setAlpha(0)
    this.nextButton.disableInteractive()
  }

  private questionEvidence(): Record<string, unknown> {
    return {
      variant_id: this.currentVariant.variantId,
      difficulty_level: this.currentVariant.difficulty,
      question_index: this.currentIndex,
      question_count: this.levels.length,
      game_type: this.session.gameType,
    }
  }

  private updateProgressText(): void {
    const n = this.currentIndex + 1
    const total = this.levels.length
    const difficulty = difficultyText(this.currentVariant.difficulty)
    this.progressItems.forEach(item => item.destroy())
    this.progressItems = progressStepper(this, { x: this.viewWidth / 2,
      y: this.isCompactLayout ? 212 : 146, width: this.viewWidth - 80,
      count: total, current: this.currentIndex, stars: this.stars })
    bindLanguageText(this.progressText, () => stacked({
      en: `${GAME_TEXT.level.en} ${n} of ${total} · ${difficulty.en}`,
      si: `${GAME_TEXT.level.si} ${n} / ${total} · ${difficulty.si}`,
    }))
  }

  private updateAnswerDisplay(): void {
    this.answerText.setText(`x = [ ${this.answerBuffer} ]`)
  }

  private handleKeyPress(key: string): void {
    if (this.locked) return
    if (key === '⌫') {
      this.answerBuffer = backspaceBuffer(this.answerBuffer)
    } else if (key === '-') {
      this.answerBuffer = appendMinus(this.answerBuffer)
    } else {
      this.answerBuffer = appendDigit(this.answerBuffer, key)
    }
    // Keypad entry and backspace are never attempts (Milestone 4 §6) — no
    // tracker call, no backend event, just the visible buffer updating.
    this.updateAnswerDisplay()
  }

  private handleHintClick(): void {
    if (this.locked) return
    // For a multi-step variant, the first step's hint is the entry point to
    // solving it, so it is reused here rather than concatenating every
    // step's hint — Hangman asks for only the final value, never the
    // intermediate operations (Milestone 4 §11-§12). Documented in the
    // completion report rather than introducing a duplicated hint bank.
    this.tracker.recordHintUsed(0)
    this.backendSync.sendEvent(this.currentVariant.variantId, 'HINT_REQUESTED', this.questionEvidence())
    this.clearHintLine()
    this.feedbackText.setAlpha(0)
    const hintLine = this.add
      .text(this.layout.mathCenterX, this.layout.feedbackY, bilingualHint(this.currentVariant.steps[0].hint), {
        fontFamily: FONT_FAMILY,
        fontSize: `${T.font.caption}px`,
        color: COLORS.text,
        align: 'center',
        wordWrap: { width: this.isCompactLayout ? this.viewWidth - 32 : 400 },
        ...SINHALA_TEXT,
      })
      .setOrigin(0.5)
      .setAlpha(0)
    this.hintLine = hintLine
    bindLanguageText(hintLine, () => bilingualHint(this.currentVariant.steps[0].hint))
    this.tweens.add({ targets: hintLine, alpha: 1, duration: 200 })
    // The hint shares the feedback slot's general area but must not block a
    // later submission's feedback from being readable, so it fades on its
    // own shortly after (hints never advance the figure or lock input). If
    // a submission resolves the question before this fires, clearHintLine()
    // has already destroyed it and nulled this.hintLine, so the `===` guard
    // here stops this stale timer from touching a destroyed/replaced object.
    this.time.delayedCall(2600, () => {
      if (this.hintLine !== hintLine) return
      this.tweens.add({ targets: hintLine, alpha: 0, duration: 300, onComplete: () => this.clearHintLine() })
    })
  }

  // Destroys the current hint line, if any, immediately — used whenever a
  // new state (a new question, a wrong-answer retry, or resolving the
  // question) makes the old hint stale, so it never lingers on screen to
  // overlap the feedback that replaces it.
  private clearHintLine(): void {
    this.hintLine?.destroy()
    this.hintLine = null
  }

  private handleSubmit(): void {
    if (this.locked) return
    // Do not allow an empty answer submission (Milestone 4 §6).
    if (!isSubmittable(this.answerBuffer)) return

    const variant = this.currentVariant
    const wrongSoFar = this.tracker.getStepAnalytics(0)?.wrongAttempts ?? 0
    const priorAttempts = this.tracker.getStepAnalytics(0)?.attemptsCount ?? 0
    const hintsBeforeAttempt = this.tracker.getStepAnalytics(0)?.hintCount ?? 0
    if (priorAttempts > 0) {
      this.backendSync.sendEvent(variant.variantId, 'RETRY_STARTED', this.questionEvidence())
    }
    this.tracker.recordAttempt(0)

    const submitted = this.answerBuffer
    this.backendSync.sendEvent(variant.variantId, 'ANSWER_SUBMITTED', {
      ...this.questionEvidence(),
      submitted_value: submitted,
      attempt_number: priorAttempts + 1,
      hints_before_attempt: hintsBeforeAttempt,
      question_prompt: variant.startingEquation,
      expected_response: variant.finalAnswer,
      answer_type: 'final_value',
    })

    const outcome = submitAnswer(submitted, variant.finalAnswer, wrongSoFar)

    if (outcome.correct) {
      this.backendSync.sendEvent(variant.variantId, 'ANSWER_CORRECT', {
        ...this.questionEvidence(),
        submitted_value: submitted,
        attempt_number: priorAttempts + 1,
        hints_before_attempt: hintsBeforeAttempt,
        question_prompt: variant.startingEquation,
        expected_response: variant.finalAnswer,
        answer_type: 'final_value',
      })
      this.resolveQuestion(true, wrongSoFar)
      return
    }

    this.tracker.recordWrongAttempt(0)
    this.backendSync.sendEvent(variant.variantId, 'ANSWER_INCORRECT', {
      ...this.questionEvidence(),
      submitted_value: submitted,
      wrong_count: outcome.wrongCount,
      attempt_number: priorAttempts + 1,
      hints_before_attempt: hintsBeforeAttempt,
      question_prompt: variant.startingEquation,
      expected_response: variant.finalAnswer,
      answer_type: 'final_value',
    })

    if (outcome.failed) {
      this.resolveQuestion(false, outcome.wrongCount)
      return
    }

    // Wrong, but attempts remain: one finger slips, stay on the same
    // question (Milestone 4 §8) — clear the buffer and let the learner try
    // again.
    this.figure.setGrip(outcome.wrongCount)
    this.clearHintLine()
    this.answerBuffer = ''
    this.updateAnswerDisplay()
    bindLanguageText(this.feedbackText, () => inline(GAME_TEXT.tryAgain))
    this.feedbackText.setColor(COLORS.incorrectText)
    this.feedbackText.setAlpha(0)
    this.tweens.add({ targets: this.feedbackText, alpha: 1, duration: 200 })
    bindLanguageText(this.attemptsText, () => inline({
      en: `${GAME_TEXT.attemptsLeft.en}: ${MAX_WRONG_SUBMISSIONS - outcome.wrongCount}`,
      si: `${GAME_TEXT.attemptsLeft.si}: ${MAX_WRONG_SUBMISSIONS - outcome.wrongCount}`,
    }))
  }

  // Shared setup for ending a question, whether solved or failed after the
  // maximum wrong submissions (Milestone 4 §7, §10). `wrongCount` is frozen
  // at the moment of resolution — correct answers never change it, and a
  // failed question is always exactly MAX_WRONG_SUBMISSIONS. Locks input
  // and saves the backend attempt immediately either way; the visible
  // feedback and the move to Next/the summary are handled by
  // resolveCorrect()/resolveFailed() below, since a failed question needs
  // to wait for the fall animation to finish first.
  private resolveQuestion(correct: boolean, wrongCount: number): void {
    this.locked = true
    this.setKeypadEnabled(false)
    this.submitButton.disableInteractive()
    this.submitButton.setAlpha(0)
    this.hintButton.disableInteractive()
    this.hintButton.setAlpha(0)
    bindLanguageText(this.attemptsText, () => '')
    this.clearHintLine()

    const variant = this.currentVariant
    this.tracker.completeStep(0)
    this.tracker.completeLevel()

    const stars = correct ? starsForHangman(wrongCount) : 0
    this.stars[this.currentIndex] = stars

    const totals = this.tracker.getCurrentLevelTotals()
    this.backendSync.saveTaskAttempt({
      task_id: variant.variantId,
      activity_id: variant.activityId,
      variant_id: variant.variantId,
      difficulty_level: variant.difficulty,
      attempts_count: totals?.attemptsCount ?? 0,
      wrong_attempts: totals?.wrongAttempts ?? 0,
      hints_used: totals?.hintCount ?? 0,
      time_taken_sec: totals?.timeTakenSec ?? 0,
      is_completed: true,
      is_successful: correct,
      score: correct ? 1 : 0,
    })
    this.backendSync.sendEvent(variant.variantId, 'TASK_COMPLETED', {
      ...this.questionEvidence(),
      outcome: correct ? 'solved' : 'failed',
    })

    if (correct) {
      this.resolveCorrect(variant, wrongCount)
    } else {
      this.resolveFailed(variant)
    }
  }

  // Correct answer, at any point: the grip is left exactly as it was (never
  // advances on success — Milestone 4 §7) and the figure just gets a
  // happier face plus a brief confetti burst instead.
  private resolveCorrect(variant: EquationVariant, wrongCount: number): void {
    this.figure.celebrate(wrongCount)
    bindLanguageText(this.feedbackText, () => `${inline(GAME_TEXT.correct)}\nx = ${variant.finalAnswer}`)
    this.feedbackText.setColor(COLORS.correctText)
    this.feedbackText.setAlpha(0)
    this.tweens.add({ targets: this.feedbackText, alpha: 1, duration: 300 })
    this.answerText.setText(`x = ${variant.finalAnswer}`)
    this.proceedAfterQuestion(variant)
  }

  // Failed after the maximum wrong submissions: the figure falls first
  // (Milestone 4 §10 — "complete the figure"), and the answer reveal/Next
  // wait for that to finish, so the fall actually reads as the moment the
  // question ends rather than happening underneath text that already gave
  // the outcome away.
  private resolveFailed(variant: EquationVariant): void {
    const reveal = () => {
      bindLanguageText(this.feedbackText, () =>
        `${inline(GAME_TEXT.questionFailed)}\n${inline(GAME_TEXT.correctAnswerLabel)}: x = ${variant.finalAnswer}`,
      )
      this.feedbackText.setColor(COLORS.incorrectText)
      this.feedbackText.setAlpha(0)
      this.tweens.add({ targets: this.feedbackText, alpha: 1, duration: 300 })
      this.answerText.setText(`x = ${variant.finalAnswer}`)
      this.proceedAfterQuestion(variant)
    }

    if (this.reducedMotion) {
      this.figure.setFallProgress(1)
      reveal()
      return
    }

    this.tweens.addCounter({
      from: 0,
      to: 1,
      duration: 900,
      onUpdate: (tween) => this.figure.setFallProgress(tween.getValue() ?? 1),
      onComplete: reveal,
    })
  }

  private proceedAfterQuestion(variant: EquationVariant): void {
    const isLastQuestion = this.currentIndex === this.levels.length - 1
    if (isLastQuestion) {
      this.backendSync.sendEvent(variant.variantId, 'GAME_COMPLETED')
      this.time.delayedCall(this.reducedMotion ? 800 : 1600, () => void this.finishSession())
      return
    }

    this.nextButton.setInteractive()
    this.tweens.add({ targets: this.nextButton, alpha: 1, duration: 300 })
  }

  private setKeypadEnabled(enabled: boolean): void {
    this.keyButtons.forEach((button) => {
      if (enabled) button.setInteractive()
      else button.disableInteractive()
    })
    if (enabled) this.submitButton.setInteractive()
  }

  private advanceToNextQuestion(): void {
    this.currentIndex += 1
    this.displayCurrentQuestion()
  }

  // Same reasoning as EquationGameScene.finishSession(): awaited because the
  // summary screen needs the backend's completion check and game_results
  // creation to have actually finished first.
  private async finishSession(): Promise<void> {
    const summary = await this.session.finish()
    console.log('Hangman session summary:', summary)

    if (this.isDestroyed) return

    this.scene.restart({
      session: this.session,
      questionIndex: this.currentIndex,
      showSummary: true,
    } satisfies SceneInitData)
  }

  // ---- Session summary ---------------------------------------------------

  private createSummaryScreen(): void {
    this.createLoadingScreen()
    if (this.loadingText) bindLanguageText(this.loadingText, () => stacked(GAME_TEXT.calculating))
    void this.loadAndShowResult()
  }

  private async loadAndShowResult(): Promise<void> {
    const generation = this.sceneGeneration
    const result = await this.backendSync.getGameResult()

    if (generation !== this.sceneGeneration || this.isDestroyed) return

    this.loadingText?.destroy()
    this.loadingText = null

    if (result) {
      this.renderResultSummary(result)
    } else {
      this.renderFallbackSummary()
    }
  }

  // Milestone 4 §17's fields, drawn from the backend's calculated result —
  // same "frontend never computes a rate" rule as Drag & Drop. Questions
  // Solved/Failed are derived from fields the backend already returns:
  // every Hangman question reaches tasks_completed (solved or failed), so
  // Failed = tasks_completed - successful_tasks.
  private renderResultSummary(result: GameResultResponse): void {
    const failed = result.tasks_completed - result.successful_tasks
    this.renderSummaryBody({
      solved: result.successful_tasks,
      failed,
      wrongAnswers: result.wrong_attempt_count,
      hintsUsed: result.total_hint_count,
      totalTimeSec: result.game_active_time_sec,
    })
  }

  // Used only if the backend fetch itself fails (network/server issue) —
  // the game only reaches this screen after all 6 questions resolve, so a
  // null result never means "incomplete" here, same as EquationGameScene.
  // Stars (never sent to the backend) double as the solved/failed split: a
  // Hangman question scores 0 stars exactly when, and only when, it failed
  // (see hangmanLogic.ts's starsForHangman()).
  private renderFallbackSummary(): void {
    const summary = this.tracker.getSummary()
    const failed = this.stars.filter((value) => value === 0).length
    this.renderSummaryBody({
      solved: this.levels.length - failed,
      failed,
      wrongAnswers: summary.totalWrongAttempts,
      hintsUsed: summary.totalHintsUsed,
      totalTimeSec: summary.totalTimeSec ?? 0,
    })
    const warning = this.add.text(this.viewWidth / 2, this.viewHeight / 2,
      'Save unverified. Tap to retry. / සුරැකීම තහවුරු නැත. නැවත උත්සාහ කරන්න.',
      { ...SINHALA_TEXT, fontFamily: FONT_FAMILY, fontSize: '18px', color: '#ffffff',
        backgroundColor: '#9b1c1c', align: 'center', wordWrap: { width: this.viewWidth - 48 },
        padding: { x: 12, y: 12 } })
      .setOrigin(0.5).setDepth(1000).setInteractive({ useHandCursor: true })
    bindLanguageText(warning, () => stacked(GAME_TEXT.saveUnverified))
    warning.on('pointerdown', () => {
      warning.disableInteractive()
      bindLanguageText(warning, () => stacked(GAME_TEXT.retryingSave))
      void this.backendSync.completeSession().then(() => {
        if (!this.isDestroyed) this.scene.restart({
          session: this.session, questionIndex: this.currentIndex, showSummary: true,
        } satisfies SceneInitData)
      })
    })
  }

  // One centered card (icon badge, title, banner, a 2x3 grid of icon stat
  // tiles, button) instead of a flat list of lines stacked at fixed Y
  // offsets pinned to the top with the button pinned to the screen bottom —
  // that older layout left a large dead gap on tall screens, and any line
  // that wrapped to two lines (the banner text, a combined bilingual stat
  // line) ran into the fixed-offset line below it. Approved from the
  // Hangman Tuning Lab mockup (see GAME_MODAL_FILE_STRUCTURE.md).
  private renderSummaryBody(data: {
    solved: number
    failed: number
    wrongAnswers: number
    hintsUsed: number
    totalTimeSec: number
  }): void {
    const centerX = this.viewWidth / 2
    const compact = this.isCompactLayout
    const hasBanner = data.failed === 0

    const cardW = Math.min(this.viewWidth - 64, 420)
    const pad = 24
    const badgeH = 56
    const titleH = compact ? 70 : 64
    const bannerH = 66
    const tileGap = 10
    const tileW = (cardW - pad * 2 - tileGap) / 2
    const tileH = 64
    const gridH = tileH * 3 + tileGap * 2
    const buttonGap = 18
    const buttonH = 52
    const contentH =
      pad + badgeH + 12 + titleH + (hasBanner ? bannerH : 0) + gridH + buttonGap + buttonH + pad

    const cardTop = Math.max(20, (this.viewHeight - contentH) / 2)
    new RoundedPanel(
      this, centerX, cardTop + contentH / 2, cardW, contentH,
      T.color.surface, T.color.border, T.radius.panel, true,
    )

    let y = cardTop + pad

    this.add.circle(centerX, y + badgeH / 2, badgeH / 2, T.color.primarySoft)
    this.add
      .text(centerX, y + badgeH / 2, '🏆', { fontFamily: FONT_FAMILY, fontSize: compact ? '28px' : '26px' })
      .setOrigin(0.5)
    y += badgeH + 12

    bilingualPair(this, { x: centerX, primaryY: y + titleH / 2 - 16, secondaryY: y + titleH / 2 + 16,
      text: GAME_TEXT.sessionComplete, width: cardW - pad * 2,
      primarySize: compact ? 20 : 22, secondarySize: 14, color: COLORS.text })
    y += titleH

    // "You didn't let him fall" is a claim about the whole session, so it
    // only makes sense shown once, here, and only when the figure never
    // actually fell on any of the 6 questions — never repeated per question.
    if (hasBanner) {
      new RoundedPanel(
        this, centerX, y + bannerH / 2, cardW - pad * 2, bannerH - 16,
        T.color.successSoft, T.color.success, T.radius.tile,
      )
      const banner = this.add
        .text(centerX, y + bannerH / 2, inline(GAME_TEXT.neverFell), {
          fontFamily: FONT_FAMILY,
          fontSize: compact ? '13px' : '14px',
          fontStyle: '',
          color: COLORS.correctText,
          align: 'center',
          wordWrap: { width: cardW - pad * 2 - 16 },
        })
        .setOrigin(0.5)
      bindLanguageText(banner, () => inline(GAME_TEXT.neverFell))
      y += bannerH
    }

    const earnedStars = this.stars.reduce((sum, value) => sum + value, 0)
    const possibleStars = this.levels.length * MAX_STARS_PER_TASK
    const tiles: Array<{ icon: string; value: string; label: Bilingual; color: string }> = [
      { icon: '✓', value: `${data.solved}/${this.levels.length}`, label: GAME_TEXT.questionsSolved, color: COLORS.correctText },
      {
        icon: '✕', value: `${data.failed}`, label: GAME_TEXT.questionsFailed,
        color: data.failed > 0 ? COLORS.incorrectText : cssColor(T.color.muted),
      },
      { icon: '↻', value: `${data.wrongAnswers}`, label: GAME_TEXT.wrongAnswers, color: COLORS.text },
      { icon: '💡', value: `${data.hintsUsed}`, label: GAME_TEXT.hintsUsed, color: cssColor(T.color.gold) },
      { icon: '⏱', value: formatActiveTime(data.totalTimeSec), label: GAME_TEXT.totalTime, color: COLORS.text },
      { icon: '★', value: `${earnedStars}/${possibleStars}`, label: GAME_TEXT.starsEarned, color: cssColor(T.color.gold) },
    ]
    tiles.forEach((tile, index) => {
      const col = index % 2
      const row = Math.floor(index / 2)
      const tx = centerX - cardW / 2 + pad + tileW / 2 + col * (tileW + tileGap)
      const ty = y + row * (tileH + tileGap) + tileH / 2
      new RoundedPanel(this, tx, ty, tileW, tileH, T.color.surfaceSoft, T.color.border, T.radius.tile)
      this.add
        .text(tx, ty - 9, `${tile.icon} ${tile.value}`, {
          fontFamily: FONT_FAMILY, fontSize: '16px', fontStyle: 'bold', color: tile.color,
        })
        .setOrigin(0.5)
      bindLanguageText(this.add
        .text(tx, ty + 13, '', { fontFamily: FONT_FAMILY, fontSize: '11px', color: cssColor(T.color.muted) })
        .setOrigin(0.5), () => primaryGameText(tile.label))
    })
    y += gridH + buttonGap

    this.createButton(
      centerX,
      y + buttonH / 2,
      cardW - pad * 2,
      buttonH,
      GAME_TEXT.chooseAnother.en,
      () => this.scene.start('GameSelectionScene'),
      COLORS.buttonFill,
      GAME_TEXT.chooseAnother.si,
    )
  }
}

function formatActiveTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.round(totalSeconds % 60)
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
}
