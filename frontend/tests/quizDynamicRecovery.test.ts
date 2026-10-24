import assert from 'node:assert/strict'
import test from 'node:test'
import { PendingQuizWrites } from '../src/quiz/pendingQuizWrites.ts'
import type { CreateQuizSessionInput } from '../src/quiz/api.ts'
import type { QuizQuestion, QuizSession } from '../src/quiz/types.ts'

function memoryStorage() {
  const entries = new Map<string, string>()
  return { getItem: (key: string) => entries.get(key) ?? null,
    setItem: (key: string, value: string) => { entries.set(key, value) } }
}

const request: CreateQuizSessionInput = {
  student_id: 'STU_001', concept_id: 'linear_equations', assessment_phase: 'pre_tutor',
  display_language: 'bilingual', learning_cycle_id: '4f7f97d7-84d9-4fca-8bbb-20c129e4f843',
  client_session_id: '6c089f9e-99b4-4377-81c7-68d66b2f4f2a', bank_mode: 'dynamic_dev',
}

const questions = Array.from({ length: 10 }, (_, index): QuizQuestion => ({
  id: `variant-${index}`, question_code: `PP1-DYN-S${String(index + 1).padStart(2, '0')}-V02`,
  concept_id: 'linear_equations', subconcept_code: 'two_step_equations',
  question_type: 'multiple_choice', question_text_en: 'Solve x + 1 = 2.',
  question_text_si: 'සමීකරණය විසඳන්න: x + 1 = 2.',
  difficulty_level: index < 4 ? 'easy' : index < 8 ? 'medium' : 'hard',
  options: ['1', '2', '3', '4'].map((answer, pos) => ({ id: `option-${index}-${pos}`,
    option_code: 'ABCD'[pos], option_text_en: answer, option_text_si: answer })),
}))

test('dynamic question plan survives a lost question response and browser reload', async () => {
  const storage = memoryStorage()
  let reads = 0
  const transport = {
    create: async (input: CreateQuizSessionInput): Promise<QuizSession> => ({
      quiz_session_id: `QUIZ-${input.client_session_id}`, student_id: input.student_id,
      concept_id: input.concept_id, learning_cycle_id: input.learning_cycle_id,
      assessment_phase: input.assessment_phase, quiz_attempt_number: 1,
      display_language: input.display_language, status: 'in_progress',
      started_at: '2026-10-21T00:00:00Z', completed_at: null,
      bank_version: 'pp1_dynamic_v1_DRAFT',
    }),
    questions: async () => {
      reads += 1
      if (reads === 1) throw new Error('Response lost after session creation')
      return questions
    },
    answer: async () => { throw new Error('No answer expected') },
    complete: async () => { throw new Error('No completion expected') },
  }
  const first = new PendingQuizWrites(storage, transport, 'http://local.test/api/v1')
  const id = first.start(request, [])
  assert.equal(await first.flush(id), false)
  assert.equal(first.session(id).created, true)
  assert.deepEqual(first.session(id).question_ids, [])
  const reopened = new PendingQuizWrites(storage, transport, 'http://local.test/api/v1')
  assert.equal(await reopened.flush(id), true)
  assert.deepEqual(reopened.session(id).question_ids, questions.map(question => question.id))
  assert.equal(reopened.status(id), 'Saved')
  assert.equal(await reopened.flush(id), true)
  assert.equal(reads, 2)
})
