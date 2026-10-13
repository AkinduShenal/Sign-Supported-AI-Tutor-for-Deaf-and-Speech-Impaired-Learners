import type { AssessmentPhase, GameType, GameplayEventType } from '../types'
import { fetchGameResult } from './gameApi'
import type { GameResultResponse, SaveTaskAttemptInput } from './gameApi'
import { getCollectionStore } from './collectionStore'

interface StartSessionInput {
  studentId: string
  conceptId: string
  learningCycleId: string
  assessmentPhase: AssessmentPhase
  gameType?: GameType
}

// Preserve the scenes' API; the queue persists evidence before HTTP.
export class GameBackendSync {
  private readonly clientSessionId = crypto.randomUUID()
  private started = false

  startSession(input: StartSessionInput): void {
    const store = getCollectionStore()
    store.start({
      student_id: input.studentId, concept_id: input.conceptId,
      learning_cycle_id: input.learningCycleId, assessment_phase: input.assessmentPhase,
      client_session_id: this.clientSessionId,
    }, input.gameType ?? 'drag_drop')
    this.started = true
    void store.flush(this.clientSessionId)
  }

  sendEvent(taskId: string | null, eventType: GameplayEventType, payload: Record<string, unknown> = {}): void {
    const store = getCollectionStore()
    store.event(this.clientSessionId, { task_id: taskId, event_type: eventType,
      event_timestamp: new Date().toISOString(), event_payload: payload })
    void store.flush(this.clientSessionId)
  }

  saveTaskAttempt(input: Omit<SaveTaskAttemptInput, 'game_session_id'>): void {
    const store = getCollectionStore()
    store.attempt(this.clientSessionId, input)
    void store.flush(this.clientSessionId)
  }

  async completeSession(): Promise<boolean> {
    if (!this.started) return false
    const store = getCollectionStore()
    store.requestCompletion(this.clientSessionId)
    await store.flush(this.clientSessionId)
    if (!store.session(this.clientSessionId).completed) await store.flush(this.clientSessionId)
    return store.session(this.clientSessionId).completed
  }

  getSaveError(): string | null {
    if (!this.started) return 'Game collection has not started.'
    const store = getCollectionStore()
    return store.fatalError ?? store.session(this.clientSessionId).error
  }

  async getGameResult(): Promise<GameResultResponse | null> {
    if (!this.started || !getCollectionStore().session(this.clientSessionId).completed) return null
    try { return await fetchGameResult(this.clientSessionId) }
    catch (error) {
      console.warn('[game-backend] failed to fetch game result', error)
      return null
    }
  }
}
