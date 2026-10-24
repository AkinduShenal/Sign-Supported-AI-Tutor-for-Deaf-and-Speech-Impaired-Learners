import type { CreateQuizSessionInput } from './api'
import type { QuizAnswer, QuizAnswerSaved, QuizOption, QuizQuestion, QuizSession } from './types'

export const QUIZ_STORAGE_KEY = 'quiz.collection.pending.v1'
const MAX_SESSIONS = 100
const MAX_BYTES = 4 * 1024 * 1024

export interface QuizWrite {
  body: QuizAnswer
  saved: boolean
  response_id: string | null
  is_correct?: boolean
  correct_option?: QuizOption | null
  feedback_viewed?: boolean
  practice_attempts?: string[]
}

export interface QuizAttemptState {
  attemptNumber: number
  selectedOptionId: string
  correct: boolean
  canRetry: boolean
}

export function quizAttemptState(write: QuizWrite | undefined): QuizAttemptState | null {
  if (!write?.saved || typeof write.is_correct !== 'boolean') return null
  if (!write.is_correct && !write.correct_option) return null
  const practice = write.practice_attempts ?? []
  const attemptNumber = practice.length + 1
  const selectedOptionId = practice.at(-1) ?? write.body.selected_option_id
  const correct = practice.length ? selectedOptionId === write.correct_option?.id : write.is_correct
  return { attemptNumber, selectedOptionId, correct, canRetry: !correct && attemptNumber < 3 }
}

function matchesAnswerAcknowledgment(id: string, write: QuizWrite, saved: QuizAnswerSaved): boolean {
  return saved.quiz_session_id === id
    && saved.question_id === write.body.question_id
    && saved.question_order === write.body.question_order
    && saved.selected_option_id === write.body.selected_option_id
    && saved.response_time_sec === write.body.response_time_sec
    && saved.confidence_level === write.body.confidence_level
    && Date.parse(saved.answered_at) === Date.parse(write.body.client_action_at)
    && !!saved.response_id && saved.saved === true && typeof saved.is_correct === 'boolean'
    && saved.correct_option !== undefined
    && (saved.is_correct ? saved.correct_option === null : saved.correct_option !== null && (
      !!saved.correct_option.id && !!saved.correct_option.option_code
      && !!saved.correct_option.option_text_en && !!saved.correct_option.option_text_si
      && saved.correct_option.id !== write.body.selected_option_id
    ))
}

export interface QuizCollectionSession {
  request: CreateQuizSessionInput
  question_ids: string[]
  created: boolean
  session: QuizSession | null
  responses: QuizWrite[]
  completion_requested: boolean
  completed: boolean
  closed: boolean
  error: string | null
}

interface Snapshot {
  version: 1
  destination: string
  sessions: QuizCollectionSession[]
}

export interface QuizTransport {
  create(input: CreateQuizSessionInput): Promise<QuizSession>
  questions?(id: string): Promise<QuizQuestion[]>
  answer(id: string, body: QuizAnswer): Promise<QuizAnswerSaved>
  complete(id: string): Promise<QuizSession>
}

export type QuizCollectionStatus = 'Saved' | 'Pending' | 'Failed'

export class PendingQuizWrites {
  private snapshot: Snapshot
  private readonly inFlight = new Map<string, Promise<boolean>>()
  private readonly listeners = new Set<() => void>()
  private readonly storage: Pick<Storage, 'getItem' | 'setItem'>
  private readonly transport: QuizTransport
  fatalError: string | null = null

  constructor(
    storage: Pick<Storage, 'getItem' | 'setItem'>,
    transport: QuizTransport,
    destination: string,
  ) {
    this.storage = storage
    this.transport = transport
    const raw = storage.getItem(QUIZ_STORAGE_KEY)
    this.snapshot = raw ? JSON.parse(raw) as Snapshot : { version: 1, destination, sessions: [] }
    if (this.snapshot.version !== 1 || this.snapshot.destination !== destination || !Array.isArray(this.snapshot.sessions)) {
      throw new Error('Stored Quiz evidence has a different version or API destination. Preserve this browser profile.')
    }
    const ids = new Set<string>()
    for (const row of this.snapshot.sessions) {
      const id = row.request?.client_session_id
      if (!id || ids.has(id) || !row.request.student_id || !Array.isArray(row.question_ids)
        || !Array.isArray(row.responses) || row.responses.length > row.question_ids.length
        || typeof row.created !== 'boolean' || typeof row.completed !== 'boolean'
        || typeof row.completion_requested !== 'boolean' || typeof row.closed !== 'boolean'
        || row.responses.some((write, index) => write.body?.question_id !== row.question_ids[index]
          || write.body?.question_order !== index + 1 || typeof write.saved !== 'boolean'
          || (write.practice_attempts !== undefined && (!Array.isArray(write.practice_attempts)
            || write.practice_attempts.length > 2
            || write.practice_attempts.some(optionId => typeof optionId !== 'string' || !optionId))))) {
        throw new Error('Stored Quiz evidence is invalid. Preserve this browser profile and contact the researcher.')
      }
      ids.add(id)
    }
    storage.setItem(QUIZ_STORAGE_KEY, JSON.stringify(this.snapshot))
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
      if (next.sessions.length > MAX_SESSIONS || new TextEncoder().encode(serialized).length > MAX_BYTES) {
        throw new Error('Quiz collection storage is full')
      }
      this.storage.setItem(QUIZ_STORAGE_KEY, serialized)
    } catch {
      this.fatalError = 'Quiz collection stopped: browser storage is unavailable or full. Preserve this profile.'
      this.changed()
      throw new Error(this.fatalError)
    }
    this.snapshot = next
    this.changed()
  }

  sessions(): QuizCollectionSession[] { return structuredClone(this.snapshot.sessions) }
  session(id: string): QuizCollectionSession {
    const row = this.snapshot.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)
    if (!row) throw new Error('Unknown Quiz collection session')
    return structuredClone(row)
  }
  openSessions(): QuizCollectionSession[] { return this.sessions().filter(row => !row.closed) }
  status(id: string): QuizCollectionStatus {
    const row = this.session(id)
    if (row.error || this.fatalError) return 'Failed'
    if (!row.created || (row.request.bank_mode === 'dynamic_dev' && row.question_ids.length === 0)
      || row.responses.some(response => !response.saved)
      || (row.completion_requested && !row.completed)) return 'Pending'
    return 'Saved'
  }
  start(request: CreateQuizSessionInput, questionIds: string[]): string {
    if (this.openSessions().length) throw new Error('End the previous Quiz collection before starting another.')
    if ((!questionIds.length && request.bank_mode !== 'dynamic_dev')
      || new Set(questionIds).size !== questionIds.length) throw new Error('Invalid Quiz question plan')
    const id = `QUIZ-${request.client_session_id}`
    this.update(next => next.sessions.push({ request, question_ids: questionIds, created: false,
      session: null, responses: [], completion_requested: false, completed: false, closed: false, error: null }))
    return id
  }
  answer(id: string, body: QuizAnswer): void {
    const row = this.session(id)
    const index = row.responses.length
    if (row.closed || row.completed || row.completion_requested || index >= row.question_ids.length
      || row.question_ids[index] !== body.question_id || body.question_order !== index + 1) {
      throw new Error('Question does not match the open Quiz session')
    }
    this.update(next => {
      const target = next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!
      target.responses.push({ body, saved: false, response_id: null, feedback_viewed: false })
      if (target.responses.length === target.question_ids.length) target.completion_requested = true
    })
  }
  close(id: string): void {
    if (this.status(id) !== 'Saved') throw new Error('Recover pending Quiz evidence before switching learners.')
    this.update(next => { next.sessions.find(row => `QUIZ-${row.request.client_session_id}` === id)!.closed = true })
  }
  acknowledgeFeedback(id: string, questionIndex: number): void {
    const write = this.session(id).responses[questionIndex]
    const attempt = quizAttemptState(write)
    if (!attempt || attempt.canRetry) {
      throw new Error('Saved answer feedback is not available yet.')
    }
    this.update(next => {
      const target = next.sessions.find(row => `QUIZ-${row.request.client_session_id}` === id)!
      target.responses[questionIndex].feedback_viewed = true
    })
  }
  practiceAnswer(id: string, questionIndex: number, optionId: string, validOptionIds: string[]): QuizAttemptState {
    const row = this.session(id)
    const write = row.responses[questionIndex]
    const attempt = quizAttemptState(write)
    if (row.closed || !attempt?.canRetry || write.feedback_viewed
      || !validOptionIds.includes(optionId)) {
      throw new Error('Choose an option for an available Quiz practice attempt.')
    }
    this.update(next => {
      const target = next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!
      target.responses[questionIndex].practice_attempts ??= []
      target.responses[questionIndex].practice_attempts!.push(optionId)
    })
    return quizAttemptState(this.session(id).responses[questionIndex])!
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
      let row = this.session(id)
      if (!row.created) {
        const saved = await this.transport.create(row.request)
        if (saved.quiz_session_id !== id || saved.student_id !== row.request.student_id
          || saved.learning_cycle_id !== row.request.learning_cycle_id
          || saved.concept_id !== row.request.concept_id
          || saved.assessment_phase !== row.request.assessment_phase) {
          throw new Error('Quiz session acknowledgment does not match the learner and session.')
        }
        this.update(next => {
          const target = next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!
          target.created = true; target.session = saved
        })
      }
      row = this.session(id)
      if (row.request.bank_mode === 'dynamic_dev' && row.question_ids.length === 0) {
        if (!this.transport.questions) throw new Error('Dynamic Quiz question recovery is unavailable.')
        const questions = await this.transport.questions(id)
        if (questions.length !== 10 || new Set(questions.map(question => question.id)).size !== 10) {
          throw new Error('The saved dynamic Quiz plan is incomplete.')
        }
        this.update(next => {
          next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!.question_ids = questions.map(question => question.id)
        })
      }
      while (true) {
        const index = this.session(id).responses.findIndex(write => !write.saved)
        if (index < 0) break
        const write = this.session(id).responses[index]
        const saved = await this.transport.answer(id, write.body)
        if (!matchesAnswerAcknowledgment(id, write, saved)) {
          throw new Error('Quiz answer acknowledgment does not match the stored question evidence.')
        }
        this.update(next => {
          const target = next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!
          target.responses[index].saved = true; target.responses[index].response_id = saved.response_id
          target.responses[index].is_correct = saved.is_correct
          target.responses[index].correct_option = saved.correct_option
        })
      }
      const oldFeedbackIndex = this.session(id).responses.findIndex(write =>
        write.saved && write.feedback_viewed === false && write.is_correct === false
        && write.correct_option === undefined)
      if (oldFeedbackIndex >= 0) {
        const write = this.session(id).responses[oldFeedbackIndex]
        const replayed = await this.transport.answer(id, write.body)
        if (!matchesAnswerAcknowledgment(id, write, replayed) || replayed.response_id !== write.response_id) {
          throw new Error('Quiz feedback replay did not match the saved answer.')
        }
        this.update(next => {
          const target = next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!
          target.responses[oldFeedbackIndex].correct_option = replayed.correct_option
        })
      }
      row = this.session(id)
      if (row.completion_requested && !row.completed) {
        const saved = await this.transport.complete(id)
        if (saved.quiz_session_id !== id || saved.student_id !== row.request.student_id || saved.status !== 'completed') {
          throw new Error('Backend did not confirm Quiz assessment completion.')
        }
        this.update(next => {
          const target = next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!
          target.completed = true; target.session = saved
        })
      }
      this.update(next => { next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!.error = null })
      return true
    } catch (error) {
      if (!this.fatalError) this.update(next => {
        next.sessions.find(item => `QUIZ-${item.request.client_session_id}` === id)!.error = error instanceof Error ? error.message : 'Quiz recording failed'
      })
      return false
    }
  }
}
