import type { CreateGameSessionInput, SaveTaskAttemptInput, SendGameplayEventInput } from './gameApi.ts'

export const COLLECTION_STORAGE_KEY = 'game.collection.pending.v1'
const MAX_SESSIONS = 100
const MAX_WRITES = 20000
const MAX_BYTES = 4 * 1024 * 1024

type Write = { id: string; kind: 'event'; body: SendGameplayEventInput }
  | { id: string; kind: 'attempt'; body: SaveTaskAttemptInput }

export interface CollectionSession {
  request: CreateGameSessionInput & { client_session_id: string }
  mode: string
  created: boolean
  writes: Write[]
  completionRequested: boolean
  completed: boolean
  closed: boolean
  error: string | null
}

interface Snapshot {
  version: 1
  destination: string
  sessions: CollectionSession[]
}

export interface CollectionTransport {
  create(input: CreateGameSessionInput): Promise<{ game_session_id: string; student_id: string }>
  event(input: SendGameplayEventInput): Promise<unknown>
  attempt(input: SaveTaskAttemptInput): Promise<unknown>
  complete(session: string): Promise<{ game_session_id: string; status: string }>
}

export type CollectionStatus = 'Saved' | 'Pending' | 'Failed'

// Synchronous write-ahead persistence happens before any HTTP request. No
// queue entry is evicted to make room, or removed before a positive response.
export class PendingGameWrites {
  private snapshot: Snapshot
  private readonly inFlight = new Map<string, Promise<boolean>>()
  private readonly listeners = new Set<() => void>()
  private readonly storage: Pick<Storage, 'getItem' | 'setItem'>
  private readonly transport: CollectionTransport
  fatalError: string | null = null

  constructor(
    storage: Pick<Storage, 'getItem' | 'setItem'>,
    transport: CollectionTransport,
    destination: string,
  ) {
    this.storage = storage
    this.transport = transport
    const raw = storage.getItem(COLLECTION_STORAGE_KEY)
    this.snapshot = raw ? JSON.parse(raw) as Snapshot : { version: 1, destination, sessions: [] }
    if (this.snapshot.version !== 1 || this.snapshot.destination !== destination || !Array.isArray(this.snapshot.sessions)) {
      throw new Error('Stored Game evidence has an incompatible version or API destination. Preserve this browser profile and contact the researcher.')
    }
    const ids = new Set<string>()
    for (const row of this.snapshot.sessions) {
      const id = row.request?.client_session_id
      if (!id || ids.has(id) || !row.request.student_id || !Array.isArray(row.writes)
        || typeof row.created !== 'boolean' || typeof row.completed !== 'boolean'
        || typeof row.completionRequested !== 'boolean' || typeof row.closed !== 'boolean'
        || row.writes.some(w => !w.id || !['event', 'attempt'].includes(w.kind) || w.body?.game_session_id !== id)) {
        throw new Error('Stored Game evidence is invalid. Do not clear browser storage; contact the researcher.')
      }
      ids.add(id)
    }
    // Verify browser storage is writable before accepting a learner action.
    storage.setItem(COLLECTION_STORAGE_KEY, JSON.stringify(this.snapshot))
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener)
    return () => { this.listeners.delete(listener) }
  }

  private changed(): void { this.listeners.forEach(listener => listener()) }

  private update(change: (next: Snapshot) => void): void {
    if (this.fatalError) throw new Error(this.fatalError)
    const next = structuredClone(this.snapshot)
    change(next)
    const serialized = JSON.stringify(next)
    try {
      if (next.sessions.length > MAX_SESSIONS
        || next.sessions.reduce((n, row) => n + row.writes.length, 0) > MAX_WRITES
        || new TextEncoder().encode(serialized).length > MAX_BYTES) {
        throw new Error('The bounded collection store is full.')
      }
      this.storage.setItem(COLLECTION_STORAGE_KEY, serialized)
    } catch {
      this.fatalError = 'Collection stopped: browser storage is unavailable or full. Preserve this profile and all existing evidence; do not continue playing.'
      this.changed()
      throw new Error(this.fatalError)
    }
    this.snapshot = next
    this.changed()
  }

  sessions(): CollectionSession[] { return structuredClone(this.snapshot.sessions) }
  session(id: string): CollectionSession {
    const row = this.snapshot.sessions.find(s => s.request.client_session_id === id)
    if (!row) throw new Error('Unknown collection session')
    return structuredClone(row)
  }

  status(id: string): CollectionStatus {
    const row = this.session(id)
    if (row.error || this.fatalError) return 'Failed'
    return !row.created || row.writes.length || (row.completionRequested && !row.completed) ? 'Pending' : 'Saved'
  }

  start(request: CreateGameSessionInput & { client_session_id: string }, mode: string): void {
    if (this.snapshot.sessions.some(row => !row.closed)) {
      throw new Error('Close the previous collection explicitly before starting another session.')
    }
    const id = request.client_session_id
    this.update(next => next.sessions.push({ request, mode, created: false,
      writes: [{ id: crypto.randomUUID(), kind: 'event', body: {
        game_session_id: id, task_id: null, event_type: 'GAME_STARTED',
        event_timestamp: new Date().toISOString(), event_payload: {
          game_type: mode, recording_protocol: 'game-evidence-v1',
          identity_source: 'researcher_assigned_code', client_event_id: crypto.randomUUID(),
        },
      } }], completionRequested: false, completed: false, closed: false, error: null }))
  }

  event(id: string, body: Omit<SendGameplayEventInput, 'game_session_id'>): void {
    this.append(id, { id: crypto.randomUUID(), kind: 'event', body: {
      ...body, game_session_id: id, event_payload: { ...body.event_payload, client_event_id: crypto.randomUUID() },
    } })
  }

  attempt(id: string, body: Omit<SaveTaskAttemptInput, 'game_session_id'>): void {
    this.append(id, { id: crypto.randomUUID(), kind: 'attempt', body: { ...body, attempt_number: body.attempt_number ?? 1, game_session_id: id } })
  }

  private append(id: string, write: Write): void {
    const row = this.session(id)
    if (row.completed || row.closed || row.completionRequested) throw new Error('This collection no longer accepts new evidence.')
    this.update(next => next.sessions.find(s => s.request.client_session_id === id)!.writes.push(write))
  }

  requestCompletion(id: string): void {
    this.update(next => { next.sessions.find(s => s.request.client_session_id === id)!.completionRequested = true })
  }

  close(id: string): void {
    if (this.status(id) !== 'Saved') throw new Error('Recover unsaved evidence before closing or switching learners.')
    this.update(next => { next.sessions.find(s => s.request.client_session_id === id)!.closed = true })
  }

  flush(id: string): Promise<boolean> {
    const running = this.inFlight.get(id)
    if (running) return running
    const run = this.drain(id).finally(() => { this.inFlight.delete(id); this.changed() })
    this.inFlight.set(id, run)
    return run
  }

  private async drain(id: string): Promise<boolean> {
    try {
      if (!this.session(id).created) {
        const request = this.session(id).request
        const saved = await this.transport.create(request)
        if (saved.game_session_id !== id || saved.student_id !== request.student_id) throw new Error('Session acknowledgment does not match the stored learner/session.')
        this.update(next => { next.sessions.find(s => s.request.client_session_id === id)!.created = true })
      }
      while (this.session(id).writes.length) {
        const write = this.session(id).writes[0]
        await (write.kind === 'event' ? this.transport.event(write.body) : this.transport.attempt(write.body))
        this.update(next => {
          const row = next.sessions.find(s => s.request.client_session_id === id)!
          row.writes = row.writes.filter(w => w.id !== write.id)
        })
      }
      if (this.session(id).completionRequested && !this.session(id).completed) {
        const saved = await this.transport.complete(id)
        if (saved.game_session_id !== id || saved.status !== 'completed') throw new Error('Backend did not confirm assessment completion.')
        this.update(next => { next.sessions.find(s => s.request.client_session_id === id)!.completed = true })
      }
      this.update(next => { next.sessions.find(s => s.request.client_session_id === id)!.error = null })
      return true
    } catch (error) {
      if (!this.fatalError) this.update(next => {
        next.sessions.find(s => s.request.client_session_id === id)!.error = error instanceof Error ? error.message : 'Recording failed'
      })
      return false
    }
  }
}
