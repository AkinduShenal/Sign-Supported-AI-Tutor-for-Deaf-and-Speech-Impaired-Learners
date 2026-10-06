import { useCallback, useRef } from 'react'
import type { GameplayEvent, GameplayEventType } from './types'

// Stubbed event sink: logs to the console for now. Swap the body of
// `logEvent` for a POST to /api/v1/game/sessions/{id}/events once that
// endpoint exists — callers do not need to change.
export function useGameEvents() {
  const eventsRef = useRef<GameplayEvent[]>([])

  const logEvent = useCallback(
    (
      taskId: string,
      eventType: GameplayEventType,
      payload: Record<string, unknown> = {},
    ) => {
      const event: GameplayEvent = {
        taskId,
        eventType,
        timestamp: new Date().toISOString(),
        payload,
      }
      eventsRef.current = [...eventsRef.current, event]
      console.info('[gameplay-event]', event)
    },
    [],
  )

  const getEvents = useCallback(() => eventsRef.current, [])

  return { logEvent, getEvents }
}
