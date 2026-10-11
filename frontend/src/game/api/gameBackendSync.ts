import type { AssessmentPhase, GameType, GameplayEventType } from '../types'
import {
  completeGameSession,
  createGameSession,
  fetchGameResult,
  saveTaskAttempt,
  sendGameplayEvent,
} from './gameApi'
import type { GameResultResponse, SaveTaskAttemptInput } from './gameApi'

interface StartSessionInput {
  studentId: string
  conceptId: string
  learningCycleId: string
  assessmentPhase: AssessmentPhase
  gameType?: GameType
}

// Sends gameplay to the backend alongside the existing local analytics
// (GameSessionTracker), without the two knowing about each other. Every
// call here is fire-and-forget: the game never waits on the network, and a
// failed request is logged and swallowed rather than breaking play. This is
// what Milestone 3 Step 9 means by "do not block the UI unnecessarily" and
// "handle failed requests safely."
export class GameBackendSync {
  private sessionIdPromise: Promise<string | null> | null = null
  // Fire-and-forget requests still in flight. completeSession() waits for
  // these first, so a task attempt sent just before the end of the game
  // can't arrive after (and be missed by) the backend's completion check.
  private readonly pending = new Set<Promise<void>>()

  private track(request: Promise<void>): void {
    this.pending.add(request)
    void request.finally(() => this.pending.delete(request))
  }

  // Call once, when the game genuinely starts (not on a resize rebuild —
  // see SceneInitData in EquationGameScene.ts, which carries the same
  // GameBackendSync instance through a resize so this never re-fires).
  startSession(input: StartSessionInput): void {
    this.sessionIdPromise = createGameSession({
      student_id: input.studentId,
      concept_id: input.conceptId,
      learning_cycle_id: input.learningCycleId,
      assessment_phase: input.assessmentPhase,
    })
      .then((session) => {
        // game_type has no session column on the backend yet, so it is
        // recorded here, in the event payload, which is persisted as JSON.
        this.sendEvent(
          null,
          'GAME_STARTED',
          input.gameType ? { game_type: input.gameType } : {},
          session.game_session_id,
        )
        return session.game_session_id
      })
      .catch((error: unknown) => {
        console.warn('[game-backend] failed to create session', error)
        return null
      })
  }

  sendEvent(
    taskId: string | null,
    eventType: GameplayEventType,
    // Evidence for reconstructing what the learner saw and chose (variant,
    // step, selected card) — stored as gameplay_events.event_payload.
    payload: Record<string, unknown> = {},
    // Only passed internally by startSession(), which already has the id
    // before this.sessionIdPromise resolves to it.
    knownSessionId?: string,
  ): void {
    this.track(
      this.withSessionId(knownSessionId, (sessionId) =>
        sendGameplayEvent({
          game_session_id: sessionId,
          task_id: taskId,
          event_type: eventType,
          event_timestamp: new Date().toISOString(),
          event_payload: payload,
        }).then(() => undefined),
      ),
    )
  }

  saveTaskAttempt(input: Omit<SaveTaskAttemptInput, 'game_session_id'>): void {
    this.track(
      this.withSessionId(undefined, (sessionId) =>
        saveTaskAttempt({ ...input, game_session_id: sessionId }).then(() => undefined),
      ),
    )
  }

  // Returns a promise (unlike every other method here) because the scene
  // awaits it specifically: the summary screen it leads to needs the
  // backend's completion check (Milestone 3 Step 16) and game_results
  // creation (Step 17) to have actually finished before it asks for the
  // result — not fire-and-forget like logging an event. Still safe to
  // call without awaiting; failures are swallowed the same as everywhere
  // else in this class.
  async completeSession(): Promise<void> {
    // Let every event and task attempt already sent finish first.
    await Promise.allSettled([...this.pending])
    await this.withSessionId(undefined, (sessionId) =>
      completeGameSession(sessionId).then(() => undefined),
    )
  }

  // Also awaited rather than fire-and-forget, for the same reason as
  // completeSession() above — the summary screen has real content to show
  // only once this resolves. Returns null (rather than throwing) on any
  // failure, including "not complete yet" (404), so the scene can fall
  // back to its local-only summary instead of breaking.
  async getGameResult(): Promise<GameResultResponse | null> {
    const sessionId = await this.sessionIdPromise
    if (!sessionId) return null

    try {
      return await fetchGameResult(sessionId)
    } catch (error) {
      console.warn('[game-backend] failed to fetch game result', error)
      return null
    }
  }

  private async withSessionId(
    knownSessionId: string | undefined,
    run: (sessionId: string) => Promise<void>,
  ): Promise<void> {
    const sessionId = knownSessionId ?? (await this.sessionIdPromise)
    if (!sessionId) return

    try {
      await run(sessionId)
    } catch (error) {
      console.warn('[game-backend] request failed', error)
    }
  }
}
