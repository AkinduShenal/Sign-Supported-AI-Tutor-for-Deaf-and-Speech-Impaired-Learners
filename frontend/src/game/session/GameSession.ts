import type { EquationVariant } from '../data/equationVariants.ts'
import { selectAssessmentVariants } from '../data/variantSelection.ts'
import { GameSessionTracker } from '../analytics/GameSessionTracker.ts'
import type { SessionAnalytics } from '../analytics/GameSessionTracker.ts'
import type { GameBackendSync } from '../api/gameBackendSync.ts'
import type { AssessmentPhase, GameType } from '../types.ts'
import { selectLearningStudent } from '../../learningContext.ts'

// Every task in an assessment is one of the 18 Easy/Medium/Hard variants
// (Milestone 3 Steps 10-13) under this same overall concept.
export const CONCEPT_ID = 'linear_equations'

export type FetchVariantUsage = (
  studentId: string,
  conceptId: string,
) => Promise<Record<string, number>>

interface GameSessionOptions {
  gameType: GameType
  studentId: string
  backendSync: GameBackendSync
  learningCycleId?: string
  conceptId?: string
  assessmentPhase?: AssessmentPhase
}

// The assessment state shared by every game mode (Drag & Drop today,
// Hangman and Mystery Reveal later): which mode was chosen, who is playing,
// which 6 variants were selected, how far through them the learner is, and
// the local tracker + backend sync for this one play-through.
//
// It holds no rendering. Each Phaser scene draws its own interaction and
// reads/writes this object, and it travels between scene restarts (resize,
// summary) so none of this is lost. A new game always gets a new
// GameSession, so a finished session is never reused.
export class GameSession {
  readonly gameType: GameType
  readonly studentId: string
  readonly learningCycleId: string
  readonly conceptId: string
  readonly assessmentPhase: AssessmentPhase
  readonly tracker: GameSessionTracker
  readonly backendSync: GameBackendSync

  // The 6 tasks chosen for this assessment. Empty until selectVariants()
  // has been called and its result assigned by the scene.
  levels: EquationVariant[] = []
  levelIndex = 0
  // Stars earned per finished task (index = task position). Local reward
  // only — never sent to the backend.
  stars: number[] = []

  private started = false

  constructor(options: GameSessionOptions) {
    this.gameType = options.gameType
    this.studentId = options.studentId
    this.backendSync = options.backendSync
    this.learningCycleId = options.learningCycleId ?? selectLearningStudent(options.studentId).learningCycleId
    this.conceptId = options.conceptId ?? CONCEPT_ID
    this.assessmentPhase = options.assessmentPhase ?? 'pre_tutor'
    this.tracker = new GameSessionTracker(options.gameType)
  }

  // Creates the backend session. Safe to call from every scene restart:
  // only the first call does anything, so a resize can never create a
  // second backend session or re-send GAME_STARTED.
  start(): void {
    if (this.started) return
    this.started = true
    this.backendSync.startSession({
      studentId: this.studentId,
      conceptId: this.conceptId,
      learningCycleId: this.learningCycleId,
      assessmentPhase: this.assessmentPhase,
      gameType: this.gameType,
    })
  }

  // Milestone 3 Steps 12-13: ask the backend how many times this student
  // has already seen each variant, then pick 2 Easy + 2 Medium + 2 Hard
  // respecting the "maximum two uses" rule. If the request fails, treat
  // every variant as unused rather than leaving the learner stuck.
  //
  // Returns the selection instead of assigning it: the scene assigns it
  // after checking its own restart generation, so a stale in-flight call
  // can't overwrite (re-roll) tasks a newer scene cycle already chose.
  async selectVariants(fetchUsage: FetchVariantUsage): Promise<EquationVariant[]> {
    let usageCounts: Record<string, number> = {}
    try {
      usageCounts = await fetchUsage(this.studentId, this.conceptId)
    } catch (error) {
      console.warn('[game] failed to load variant usage, assuming none yet', error)
    }
    return selectAssessmentVariants(usageCounts)
  }

  // Ends the play-through. Awaits the backend completion (which first
  // waits for any task records still in flight — see GameBackendSync) so
  // the summary screen can fetch the finished game_results row.
  async finish(): Promise<SessionAnalytics> {
    this.tracker.completeSession()
    const summary = this.tracker.getSummary()
    this.backendSync.sendEvent(null, 'SESSION_ENDED', { game_type: this.gameType })
    await this.backendSync.completeSession()
    return summary
  }
}
