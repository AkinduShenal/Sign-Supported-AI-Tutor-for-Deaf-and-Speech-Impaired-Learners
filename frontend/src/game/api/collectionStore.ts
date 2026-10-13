import { completeGameSession, createGameSession, saveTaskAttempt, sendGameplayEvent } from './gameApi'
import { PendingGameWrites } from './pendingGameWrites'

let store: PendingGameWrites | undefined

export function openCollectionStore(): PendingGameWrites {
  store = new PendingGameWrites(localStorage, {
    create: createGameSession, event: sendGameplayEvent, attempt: saveTaskAttempt, complete: completeGameSession,
  }, (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, ''))
  return store
}

export function getCollectionStore(): PendingGameWrites {
  if (!store) throw new Error('Acquire the collection tab lock before recording.')
  return store
}
