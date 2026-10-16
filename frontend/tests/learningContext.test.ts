import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareQuizContext, readLearningContext, rememberQuizSession, restoreQuizContext, selectLearningStudent } from '../src/learningContext.ts'

function storage() {
  const values = new Map<string, string>()
  return { getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value) } }
}

test('Quiz-first and Game-first assessments share the same learner cycle across reloads', () => {
  for (const first of ['quiz', 'game']) {
    const saved = storage()
    const context = first === 'quiz' ? prepareQuizContext('STU_001', saved) : selectLearningStudent('STU_001', saved)
    const other = first === 'quiz' ? selectLearningStudent('STU_001', saved) : prepareQuizContext('STU_001', saved)
    assert.equal(context.learningCycleId, other.learningCycleId)
    assert.deepEqual(readLearningContext(saved), other)
  }
})

test('a fresh Quiz cannot use Game evidence from a previous quiz cycle', () => {
  const saved = storage()
  const old = prepareQuizContext('STU_001', saved)
  rememberQuizSession(old, 'QUIZ-old', saved)
  assert.equal(selectLearningStudent('STU_001', saved).learningCycleId, old.learningCycleId)
  const fresh = prepareQuizContext('STU_001', saved)
  assert.notEqual(fresh.learningCycleId, old.learningCycleId)
  assert.equal(selectLearningStudent('STU_001', saved).learningCycleId, fresh.learningCycleId)
})

test('switching students preserves separate cycles and rejects invalid identities', () => {
  const saved = storage()
  const first = selectLearningStudent('STU_001', saved)
  const second = selectLearningStudent('STU_002', saved)
  assert.notEqual(first.learningCycleId, second.learningCycleId)
  assert.deepEqual(selectLearningStudent('STU_001', saved), first)
  assert.throws(() => selectLearningStudent('Jane Smith', saved))
})

test('stale Quiz responses and storage failures cannot silently create disconnected cycles', () => {
  const saved = storage()
  const old = prepareQuizContext('STU_001', saved)
  rememberQuizSession(old, 'QUIZ-old', saved)
  prepareQuizContext('STU_001', saved)
  assert.throws(() => rememberQuizSession(old, 'QUIZ-stale', saved))
  assert.throws(() => selectLearningStudent('STU_001', { getItem: () => null, setItem: () => { throw Error('Full') } }))
})

test('recovering a queued Quiz restores its original learner cycle for Game and Tutor', () => {
  const saved = storage()
  const original = prepareQuizContext('STU_001', saved)
  rememberQuizSession(original, 'QUIZ-durable', saved)
  const durable = readLearningContext(saved)!
  prepareQuizContext('STU_001', saved)
  selectLearningStudent('STU_002', saved)
  restoreQuizContext(durable, saved)
  assert.deepEqual(readLearningContext(saved), durable)
  assert.equal(selectLearningStudent('STU_001', saved).learningCycleId, original.learningCycleId)
})
