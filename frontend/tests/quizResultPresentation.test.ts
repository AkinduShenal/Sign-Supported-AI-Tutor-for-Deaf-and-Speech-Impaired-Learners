import test from 'node:test'
import assert from 'node:assert/strict'
import { presentResult } from '../src/quiz/resultPresentation.ts'
import type { QuizDiagnosticResult } from '../src/quiz/types.ts'

const result: QuizDiagnosticResult = {
  quiz_session_id: 'QUIZ-test', questions_total: 10, questions_attempted: 10, correct_answers: 8,
  mastery_level: 'medium', weak_subconcept: 'two_step_equations',
  recommended_focus: 'Two-step Equations', recommended_support_level: 'medium',
}

test('learner result uses friendly labels in English and Sinhala', () => {
  assert.deepEqual(presentResult(result, 'en'), {
    score: '8 / 10', correctAnswers: 8, wrongAnswers: 2,
    level: 'Developing', practice: 'Two-step Equations',
    focus: 'Two-step Equations', support: 'Medium',
  })
  assert.equal(presentResult({ ...result, mastery_level: 'high' }, 'en').level, 'Strong')
  assert.equal(presentResult({ ...result, mastery_level: 'low' }, 'en').level, 'Needs Support')
  assert.equal(presentResult(result, 'si').practice, 'පියවර දෙකක සමීකරණ')
  assert.equal(presentResult(result, 'si').correctAnswers, 8)
  assert.equal(presentResult(result, 'bilingual').wrongAnswers, 2)
  assert.equal(presentResult({ ...result, weak_subconcept: null }, 'en').practice, 'No clear area identified')
})
