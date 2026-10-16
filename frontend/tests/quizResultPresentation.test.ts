import test from 'node:test'
import assert from 'node:assert/strict'
import { presentConfidenceInsight, presentResult } from '../src/quiz/resultPresentation.ts'
import type { QuizDiagnosticResult } from '../src/quiz/types.ts'

const result: QuizDiagnosticResult = {
  quiz_session_id: 'QUIZ-test', questions_total: 10, questions_attempted: 10, correct_answers: 8,
  mastery_level: 'medium', weak_subconcept: 'two_step_equations',
  recommended_focus: 'Two-step Equations', recommended_support_level: 'medium',
  confidence_insight: {
    kind: 'high_incorrect', high_confidence_incorrect_count: 2,
    low_confidence_correct_count: 0,
  },
}

test('learner result uses friendly labels in English and Sinhala', () => {
  assert.deepEqual(presentResult(result, 'en'), {
    score: '8 / 10', correctAnswers: 8, wrongAnswers: 2,
    level: 'Developing Understanding', practice: 'Two-step Equations',
    focus: 'Practising how to solve two-step equations',
  })
  assert.equal(presentResult({ ...result, mastery_level: 'high' }, 'en').level, 'Strong Understanding')
  assert.equal(presentResult({ ...result, mastery_level: 'low' }, 'en').level, 'Needs More Practice')
  assert.equal(presentResult(result, 'si').practice, 'පියවර දෙකක සමීකරණ')
  assert.equal(presentResult(result, 'si').level, 'වර්ධනය වෙමින් පවතින අවබෝධයක්')
  assert.equal(presentResult(result, 'si').correctAnswers, 8)
  assert.equal(presentResult(result, 'bilingual').wrongAnswers, 2)
  assert.equal('support' in presentResult(result, 'en'), false)
  assert.equal(presentResult({ ...result, recommended_focus: 'Equation Meaning' }, 'en').focus, 'Practising how to solve two-step equations')
  const noWeak = { ...result, weak_subconcept: null, recommended_focus: 'Equation Meaning' }
  assert.equal(presentResult(noWeak, 'en').practice, 'No single weak area identified')
  assert.equal(presentResult(noWeak, 'en').focus, 'Continue practising all Linear Equation skills.')
  assert.equal(presentResult(noWeak, 'si').practice, 'විශේෂිත දුර්වල ප්‍රදේශයක් හඳුනාගෙන නැත')
  assert.equal(presentResult(noWeak, 'si').focus, 'රේඛීය සමීකරණවල සියලුම කුසලතා දිගටම පුහුණු කරන්න.')
})

test('confidence insight follows the backend signal in both languages', () => {
  assert.match(presentConfidenceInsight(result, 'en'), /2 incorrect answers/)
  assert.match(presentConfidenceInsight(result, 'si'), /වැරදි පිළිතුරු 2කට/)
  const lowCorrect = { ...result, confidence_insight: {
    kind: 'low_correct' as const,
    high_confidence_incorrect_count: 0,
    low_confidence_correct_count: 2,
  } }
  assert.match(presentConfidenceInsight(lowCorrect, 'en'), /2 questions correctly but with low confidence/)
  assert.match(presentConfidenceInsight(lowCorrect, 'si'), /ප්‍රශ්න 2කට නිවැරදිව/)
  const neutral = { ...result, confidence_insight: {
    kind: 'neutral' as const,
    high_confidence_incorrect_count: 0,
    low_confidence_correct_count: 0,
  } }
  assert.match(presentConfidenceInsight(neutral, 'en'), /Keep practicing/)
})
