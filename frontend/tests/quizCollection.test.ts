import assert from 'node:assert/strict'
import test from 'node:test'
import { PendingQuizWrites } from '../src/quiz/pendingQuizWrites.ts'
import type { CreateQuizSessionInput } from '../src/quiz/api.ts'
import type { QuizAnswer, QuizAnswerSaved, QuizSession } from '../src/quiz/types.ts'

const learner = (student_id: string, client_session_id: string): CreateQuizSessionInput => ({
  student_id, client_session_id, concept_id: 'linear_equations', assessment_phase: 'pre_tutor',
  display_language: 'bilingual', learning_cycle_id: 'f6542e15-73e6-4e1d-a10d-601187490365',
})

function memoryStorage() {
  const data = new Map<string, string>()
  return { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, value) } }
}

function savedSession(input: CreateQuizSessionInput, status: QuizSession['status'] = 'in_progress'): QuizSession {
  return {
    quiz_session_id: `QUIZ-${input.client_session_id}`, student_id: input.student_id,
    concept_id: input.concept_id, learning_cycle_id: input.learning_cycle_id,
    assessment_phase: input.assessment_phase, quiz_attempt_number: 1,
    display_language: input.display_language, status,
    started_at: '2026-10-13T00:00:00Z', completed_at: status === 'completed' ? '2026-10-13T00:10:00Z' : null,
  }
}

test('Quiz queue preserves exact answer across response loss, refresh, and learner switch', async () => {
  const storage = memoryStorage()
  const source = learner('STU_001', '18cc7009-6990-4f53-9d99-24b7fd035ff0')
  const saved = new Map<string, QuizAnswer>()
  let loseFirstAck = true
  let answerCalls = 0
  const transport = {
    create: async (input: CreateQuizSessionInput) => savedSession(input),
    answer: async (id: string, body: QuizAnswer): Promise<QuizAnswerSaved> => {
      answerCalls++
      const existing = saved.get(body.question_id)
      if (existing) assert.deepEqual(body, existing)
      else saved.set(body.question_id, structuredClone(body))
      if (loseFirstAck) { loseFirstAck = false; throw new Error('Response lost after commit') }
      return { response_id: `source-${body.question_order}`, quiz_session_id: id,
        question_id: body.question_id, question_order: body.question_order,
        selected_option_id: body.selected_option_id, response_time_sec: body.response_time_sec,
        confidence_level: body.confidence_level, answered_at: body.client_action_at, saved: true }
    },
    complete: async (_id: string) => savedSession(source, 'completed'),
  }
  const first = new PendingQuizWrites(storage, transport, 'http://isolated.test/api/v1')
  const id = first.start(source, ['question-1', 'question-2'])
  const original: QuizAnswer = { question_id: 'question-1', selected_option_id: 'option-A',
    response_time_sec: 8.75, confidence_level: 'low', question_order: 1,
    client_action_at: '2026-10-13T08:00:00.000Z' }
  first.answer(id, original)
  assert.equal(await first.flush(id), false)
  assert.equal(first.status(id), 'Failed')
  assert.throws(() => first.start(learner('STU_002', '11b2760e-656c-40bc-9f82-2dabfafc6870'), ['question-1']))

  const reopened = new PendingQuizWrites(storage, transport, 'http://isolated.test/api/v1')
  assert.deepEqual(reopened.session(id).responses[0].body, original)
  assert.equal(await reopened.flush(id), true)
  assert.equal(reopened.session(id).responses[0].saved, true)
  reopened.answer(id, { ...original, question_id: 'question-2', question_order: 2,
    selected_option_id: 'option-B', response_time_sec: 5.25, client_action_at: '2026-10-13T08:01:00.000Z' })
  assert.equal(await reopened.flush(id), true)
  assert.equal(reopened.session(id).completed, true)
  assert.equal(reopened.status(id), 'Saved')
  assert.equal(answerCalls, 3)
  assert.equal(saved.size, 2)
  reopened.close(id)
  assert.equal(reopened.start(learner('STU_002', '11b2760e-656c-40bc-9f82-2dabfafc6870'), ['question-1']), 'QUIZ-11b2760e-656c-40bc-9f82-2dabfafc6870')
})

test('Quiz queue rejects a mismatched answer acknowledgment and retains the write', async () => {
  const storage = memoryStorage()
  const source = learner('STU_001', '74974d18-5e89-4db5-9c24-9be8654b2c3e')
  const queue = new PendingQuizWrites(storage, {
    create: async input => savedSession(input),
    answer: async (id, body) => ({ response_id: 'wrong', quiz_session_id: id,
      question_id: body.question_id, question_order: body.question_order,
      selected_option_id: 'different-option', response_time_sec: body.response_time_sec,
      confidence_level: body.confidence_level, answered_at: body.client_action_at, saved: true }),
    complete: async () => savedSession(source, 'completed'),
  }, 'http://isolated.test/api/v1')
  const id = queue.start(source, ['question-1'])
  queue.answer(id, { question_id: 'question-1', selected_option_id: 'option-A', question_order: 1,
    response_time_sec: 3, confidence_level: 'high', client_action_at: '2026-10-13T08:00:00.000Z' })
  assert.equal(await queue.flush(id), false)
  assert.equal(queue.status(id), 'Failed')
  assert.equal(queue.session(id).responses[0].saved, false)
  assert.equal(queue.session(id).completed, false)
})
