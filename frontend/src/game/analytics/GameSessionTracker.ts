export interface StepAnalytics {
  stepNumber: number
  expectedOperation: string
  attemptsCount: number
  wrongAttempts: number
  hintCount: number
  completed: boolean
  timeTakenSec: number | null
}

export interface LevelAnalytics {
  levelId: string
  concept: string
  startedAt: string
  completedAt: string | null
  timeTakenSec: number | null
  wrongAttempts: number
  hintCount: number
  completed: boolean
  steps: StepAnalytics[]
}

export interface SessionAnalytics {
  sessionStartedAt: string
  sessionCompletedAt: string | null
  levelsCompleted: number
  totalWrongAttempts: number
  totalHintsUsed: number
  totalTimeSec: number | null
  levels: LevelAnalytics[]
}

// A plain, local, no-persistence tracker for one play session. It knows
// nothing about Phaser or rendering — the scene just calls these methods as
// the learner plays, and reads getSummary() when it wants the full report.
// No learner-identifying information is recorded here.
export class GameSessionTracker {
  private sessionStartedAtMs = Date.now()
  private sessionCompletedAtMs: number | null = null
  private levels: LevelAnalytics[] = []
  private levelStartedAtMs = 0
  private stepStartedAtMs = 0

  // Starts tracking a level. Safe to call more than once for the same
  // level (e.g. a window-resize rebuilds the Phaser scene) — if the most
  // recent level is this same, still-incomplete level, this does nothing,
  // so progress and counts already recorded aren't lost or duplicated.
  startLevel(levelId: string, concept: string, stepOperations: string[]): void {
    const current = this.levels[this.levels.length - 1]
    if (current && current.levelId === levelId && !current.completed) {
      return
    }

    this.levels.push({
      levelId,
      concept,
      startedAt: new Date().toISOString(),
      completedAt: null,
      timeTakenSec: null,
      wrongAttempts: 0,
      hintCount: 0,
      completed: false,
      steps: stepOperations.map((expectedOperation, index) => ({
        stepNumber: index + 1,
        expectedOperation,
        attemptsCount: 0,
        wrongAttempts: 0,
        hintCount: 0,
        completed: false,
        timeTakenSec: null,
      })),
    })
    this.levelStartedAtMs = Date.now()
    this.stepStartedAtMs = Date.now()
  }

  // Call whenever a new step becomes the one the learner is working on, so
  // its duration is measured from when it actually started.
  beginStep(): void {
    this.stepStartedAtMs = Date.now()
  }

  recordAttempt(stepIndex: number): void {
    this.currentLevel().steps[stepIndex].attemptsCount += 1
  }

  recordWrongAttempt(stepIndex: number): void {
    const level = this.currentLevel()
    level.wrongAttempts += 1
    level.steps[stepIndex].wrongAttempts += 1
  }

  recordHintUsed(stepIndex: number): void {
    const level = this.currentLevel()
    level.hintCount += 1
    level.steps[stepIndex].hintCount += 1
  }

  completeStep(stepIndex: number): void {
    const level = this.currentLevel()
    level.steps[stepIndex].completed = true
    level.steps[stepIndex].timeTakenSec = this.secondsSince(this.stepStartedAtMs)
  }

  completeLevel(): void {
    const level = this.currentLevel()
    level.completed = true
    level.completedAt = new Date().toISOString()
    level.timeTakenSec = this.secondsSince(this.levelStartedAtMs)
  }

  completeSession(): void {
    this.sessionCompletedAtMs = Date.now()
  }

  getSummary(): SessionAnalytics {
    const levelsCompleted = this.levels.filter((level) => level.completed).length
    const totalWrongAttempts = this.levels.reduce((sum, level) => sum + level.wrongAttempts, 0)
    const totalHintsUsed = this.levels.reduce((sum, level) => sum + level.hintCount, 0)

    return {
      sessionStartedAt: new Date(this.sessionStartedAtMs).toISOString(),
      sessionCompletedAt: this.sessionCompletedAtMs
        ? new Date(this.sessionCompletedAtMs).toISOString()
        : null,
      levelsCompleted,
      totalWrongAttempts,
      totalHintsUsed,
      totalTimeSec: this.sessionCompletedAtMs
        ? this.secondsSince(this.sessionStartedAtMs, this.sessionCompletedAtMs)
        : null,
      levels: this.levels,
    }
  }

  // Read-only snapshot of one step's live counts, for callers that need to
  // report them elsewhere (e.g. sending a task-attempt summary to the
  // backend) without this tracker knowing anything about where that data
  // goes.
  getStepAnalytics(stepIndex: number): StepAnalytics | null {
    return this.levels[this.levels.length - 1]?.steps[stepIndex] ?? null
  }

  private currentLevel(): LevelAnalytics {
    const level = this.levels[this.levels.length - 1]
    if (!level) {
      throw new Error('GameSessionTracker: startLevel() must be called before recording events')
    }
    return level
  }

  // Rounded to one decimal place — plenty of precision for behavioural
  // analytics, without the noise of raw millisecond timestamps.
  private secondsSince(startMs: number, endMs: number = Date.now()): number {
    return Math.round(((endMs - startMs) / 1000) * 10) / 10
  }
}
