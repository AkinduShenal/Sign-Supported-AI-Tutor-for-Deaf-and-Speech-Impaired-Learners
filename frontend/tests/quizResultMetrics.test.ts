import assert from 'node:assert/strict'
import test from 'node:test'
import { buildQuizResultMetrics, isDynamicQuizResultSession } from '../src/quiz/resultMetrics.ts'
import type { QuizCollectionSession } from '../src/quiz/pendingQuizWrites.ts'
import type { QuizDiagnosticResult, QuizQuestion } from '../src/quiz/types.ts'

const sessionId = 'QUIZ-4f7f97d7-84d9-4fca-8bbb-20c129e4f843'
const evidence = Array.from({ length: 10 }, (_, index) => ({
  question_order: index + 1,
  question_id: `variant-${index + 1}`,
  is_correct: index !== 1 && index !== 2,
  confidence_level: (index < 4 ? 'low' : index < 8 ? 'medium' : 'high') as 'low' | 'medium' | 'high',
  response_time_sec: index + 1.25,
  difficulty_level: 'easy' as const,
  subconcept_code: 'two_step_equations',
  misconception_code: null,
}))

const result: QuizDiagnosticResult = {
  quiz_session_id: sessionId, questions_total: 10, questions_attempted: 10, correct_answers: 8,
  mastery_level: 'medium', weak_subconcept: null, recommended_focus: null,
  recommended_support_level: 'medium',
  confidence_insight: { kind: 'neutral', high_confidence_incorrect_count: 0, low_confidence_correct_count: 0 },
  diagnostic_evidence: { question_evidence: evidence },
}

const questions = evidence.map((row): QuizQuestion => ({
  id: row.question_id, question_code: `PP1-DYN-S${String(row.question_order).padStart(2, '0')}-V02`,
  concept_id: 'linear_equations', subconcept_code: row.subconcept_code,
  question_type: 'multiple_choice', question_text_en: 'Solve the equation.', question_text_si: 'සමීකරණය විසඳන්න.',
  difficulty_level: row.difficulty_level, options: [],
}))

const collection: QuizCollectionSession = {
  request: {
    student_id: 'STU_035', concept_id: 'linear_equations', assessment_phase: 'pre_tutor',
    display_language: 'bilingual', learning_cycle_id: 'e92da0b7-49fc-474b-854e-9d09a5f66741',
    client_session_id: sessionId.slice(5), bank_mode: 'dynamic_dev',
  },
  question_ids: evidence.map(row => row.question_id),
  created: true, session: null,
  responses: evidence.map((row, index) => ({
    body: {
      question_id: row.question_id, selected_option_id: `option-${index}`,
      response_time_sec: row.response_time_sec, confidence_level: row.confidence_level,
      question_order: row.question_order, client_action_at: '2026-10-22T00:00:00Z',
    },
    saved: true, response_id: `response-${index}`, is_correct: row.is_correct,
    practice_attempts: index === 1 ? ['retry'] : index === 2 ? ['retry-1', 'retry-2'] : [],
  })),
  completion_requested: true, completed: true, closed: false, error: null,
}

test('result activity uses saved first answers and counts browser practice tries separately', () => {
  const metrics = buildQuizResultMetrics(result, questions, collection)
  assert.ok(metrics)
  assert.equal(metrics.questions.length, 10)
  assert.equal(metrics.averageResponseTimeSec, 5.75)
  assert.deepEqual(metrics.confidenceCounts, { low: 4, medium: 4, high: 2 })
  assert.equal(metrics.totalAttempts, 13)
  assert.deepEqual(metrics.questions.map(row => row.attemptCount), [1, 2, 3, 1, 1, 1, 1, 1, 1, 1])
  assert.equal(metrics.questions[1].isCorrect, false)
  assert.equal(metrics.questions[1].questionCode, 'PP1-DYN-S02-V02')
})

test('unmatched browser retry evidence never becomes a claimed attempt count', () => {
  const changed = structuredClone(collection)
  changed.responses[1].body.response_time_sec += 1
  const metrics = buildQuizResultMetrics(result, questions, changed)
  assert.ok(metrics)
  assert.equal(metrics.totalAttempts, null)
  assert.ok(metrics.questions.every(row => row.attemptCount === null))
  assert.equal(metrics.questions[1].responseTimeSec, evidence[1].response_time_sec)
})

test('completed dynamic collection shows prediction when older browser metadata lacks bank version', () => {
  assert.equal(isDynamicQuizResultSession(sessionId, null, collection, questions), true)
  assert.equal(isDynamicQuizResultSession('QUIZ-other', null, collection, []), false)
  const fixed = structuredClone(collection)
  fixed.request.bank_mode = 'fixed'
  assert.equal(isDynamicQuizResultSession(sessionId, null, fixed, []), false)
  assert.equal(isDynamicQuizResultSession(sessionId, null, null, questions), true)
  assert.equal(isDynamicQuizResultSession(sessionId, null, null, questions.slice(0, 9)), false)
  assert.equal(isDynamicQuizResultSession(sessionId, 'pp1_dynamic_v1_DRAFT', null, []), true)
})
