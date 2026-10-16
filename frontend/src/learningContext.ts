import { validateStudentCode } from './game/collectionIdentity.ts'

export const LEARNING_CONTEXT_KEY = 'learning.context.v1'
export interface LearningContext {
  studentId: string
  learningCycleId: string
  quizSessionId?: string
}
type ContextStore = { version: 1; activeStudentId: string; learners: Record<string, LearningContext> }
type StorageAccess = Pick<Storage, 'getItem' | 'setItem'>

function readStore(storage: StorageAccess): ContextStore {
  const raw = storage.getItem(LEARNING_CONTEXT_KEY)
  if (!raw) return { version: 1, activeStudentId: '', learners: {} }
  const store = JSON.parse(raw) as ContextStore
  if (store.version !== 1 || !store.learners || typeof store.activeStudentId !== 'string'
    || Object.entries(store.learners).some(([id, value]) => value.studentId !== id
      || validateStudentCode(id) !== id || !/^[0-9a-f-]{36}$/i.test(value.learningCycleId))
    || (store.activeStudentId && !store.learners[store.activeStudentId])) {
    throw new Error('The saved learning session could not be read. Please contact your teacher.')
  }
  return store
}

function save(store: ContextStore, storage: StorageAccess) {
  storage.setItem(LEARNING_CONTEXT_KEY, JSON.stringify(store))
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('learning-context-changed'))
}

export function readLearningContext(storage: StorageAccess = localStorage): LearningContext | null {
  const store = readStore(storage)
  return store.learners[store.activeStudentId] ?? null
}

export function selectLearningStudent(code: string, storage: StorageAccess = localStorage): LearningContext {
  const studentId = validateStudentCode(code)
  const store = readStore(storage)
  store.learners[studentId] ??= { studentId, learningCycleId: crypto.randomUUID() }
  store.activeStudentId = studentId
  save(store, storage)
  return store.learners[studentId]
}

export function prepareQuizContext(code: string, storage: StorageAccess = localStorage): LearningContext {
  const current = selectLearningStudent(code, storage)
  if (!current.quizSessionId) return current // Supports Game-first, then Quiz.
  const store = readStore(storage)
  const next = { studentId: current.studentId, learningCycleId: crypto.randomUUID() }
  store.learners[current.studentId] = next
  save(store, storage)
  return next // A fresh Quiz must not reuse a previous cycle's Game evidence.
}

export function rememberQuizSession(context: LearningContext, sessionId: string, storage: StorageAccess = localStorage): void {
  const store = readStore(storage)
  const current = store.learners[context.studentId]
  if (!current || current.learningCycleId !== context.learningCycleId) {
    throw new Error('The learning cycle changed. Please reopen the assessment.')
  }
  current.quizSessionId = sessionId
  save(store, storage)
}
