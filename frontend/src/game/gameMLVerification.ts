import { isGameMLPrediction } from './mlPrediction.ts'
import type { GameMLPrediction } from './mlPrediction.ts'
import { demoHeaders, getDevelopmentDemo } from './developmentDemoState.ts'

export interface SavedGameAcknowledgement {
  game_session_id: string
  student_id: string
  concept_id: string
  learning_cycle_id: string
  assessment_phase: 'pre_tutor' | 'post_tutor'
  status: string
  completed_at: string | null
  development_demo?: boolean
  research_verification?: { receipt: string; expires_at: string } | null
}

export interface VerificationContext {
  game_session_id: string
  student_code: string
  concept_id: string
  learning_cycle_id: string
  assessment_phase: 'pre_tutor' | 'post_tutor'
}

// Completion acknowledgements/receipts stay only in memory, outside the durable
// recording queue. Neither submitted researcher keys nor predictions are stored.
const acknowledgements = new Map<string, SavedGameAcknowledgement>()
export function rememberMLAcknowledgement(value: SavedGameAcknowledgement): void {
  acknowledgements.delete(value.game_session_id)
  if (value.status === 'completed' && value.completed_at && value.research_verification) {
    if (acknowledgements.size >= 8) acknowledgements.delete(acknowledgements.keys().next().value!)
    acknowledgements.set(value.game_session_id, structuredClone(value))
  }
}
export function forgetMLAcknowledgement(id: string): void { acknowledgements.delete(id) }

export function verificationContext(value: SavedGameAcknowledgement): VerificationContext {
  return { game_session_id: value.game_session_id, student_code: value.student_id, concept_id: value.concept_id,
    learning_cycle_id: value.learning_cycle_id, assessment_phase: value.assessment_phase }
}

export function readyMLAcknowledgement(id: string, request: {
  student_id: string; concept_id: string; learning_cycle_id: string; assessment_phase: string
}, saved: boolean, now = Date.now()): SavedGameAcknowledgement | null {
  const value = acknowledgements.get(id)
  const demo = getDevelopmentDemo()
  const validIdentity = value && (demo ? value.development_demo === true && value.student_id === 'DEMO_TEAM' : /^STU_[0-9]{3}$/.test(value.student_id))
  if (!saved || !value || value.game_session_id !== id || !validIdentity
    || !value.research_verification || !/^[A-Za-z0-9_-]{32,128}$/.test(value.research_verification.receipt)
    || !Number.isFinite(Date.parse(value.research_verification.expires_at))
    || Date.parse(value.research_verification.expires_at) <= now
    || (['student_id', 'concept_id', 'learning_cycle_id', 'assessment_phase'] as const).some(key => value[key] !== request[key])) return null
  return structuredClone(value)
}

export class MLVerificationError extends Error {
  readonly status: number
  readonly retryAfter: number
  constructor(status: number, retryAfter = 0) {
    super(status === 401 ? 'The researcher key was not accepted. Please try again.'
      : status === 429 ? 'Too many attempts. Please wait before retrying.'
        : status === 404 ? (getDevelopmentDemo()
          ? 'This demo session is unavailable or its verification window has expired. Complete a new demo.'
          : 'The prediction window for this session has expired. Complete a new session to get a prediction.')
          : status === 409 ? 'The prediction is already running or has been shown for this session.'
            : status === 422 ? 'Saved session evidence could not be verified.'
              : status === 503 ? 'ML prediction is unavailable. Ask the researcher to check the private configuration and model runtime.'
                : 'Verification could not be completed. Check the connection and try again.')
    this.status = status
    this.retryAfter = retryAfter
  }
}

/** Dedicated 75s bound covers the existing <=60s worker plus validation overhead.
 *  The one-time completion receipt is the only credential; no researcher key. */
export async function verifyGameML(base: string, saved: SavedGameAcknowledgement,
  signal: AbortSignal, transport: typeof fetch = fetch): Promise<GameMLPrediction> {
  const demo = getDevelopmentDemo()
  const response = await transport(`${base}/game/${demo ? 'development-demo/' : ''}sessions/${encodeURIComponent(saved.game_session_id)}/research-verification`, {
    method: 'POST', cache: 'no-store', credentials: 'omit',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...demoHeaders() },
    body: JSON.stringify({ receipt: saved.research_verification?.receipt,
      context: verificationContext(saved), ...(demo ? { development_demo: true } : {}) }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(75000)]),
  })
  if (!response.ok) throw new MLVerificationError(response.status, Math.min(60, Math.max(0, Number(response.headers.get('Retry-After')) || 0)))
  const result: unknown = await response.json()
  if (!isGameMLPrediction(result)) throw new MLVerificationError(502)
  return result
}

export async function cancelGameML(base: string, saved: SavedGameAcknowledgement): Promise<void> {
  if (!saved.research_verification) return
  try {
    await fetch(`${base}/game/${getDevelopmentDemo() ? 'development-demo/' : ''}sessions/${encodeURIComponent(saved.game_session_id)}/research-verification/cancel`, {
      method: 'POST', cache: 'no-store', credentials: 'omit', headers: { 'Content-Type': 'application/json', ...demoHeaders() },
      body: JSON.stringify({ receipt: saved.research_verification.receipt }), signal: AbortSignal.timeout(5000),
    })
  } catch { /* A lost cancellation still expires on the server; never log a body. */ }
}
