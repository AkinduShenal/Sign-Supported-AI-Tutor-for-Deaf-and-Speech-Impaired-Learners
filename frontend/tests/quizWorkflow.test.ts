import test from 'node:test'
import assert from 'node:assert/strict'
import type { QuizQuestion } from '../src/quiz/types.ts'
import { elapsedQuestionSeconds, validatePreQuestionBank } from '../src/quiz/workflow.ts'

const questions: QuizQuestion[] = Array.from({ length: 10 }, (_, index) => ({
  id: `question-${index}`,
  question_code: `TEST-${index + 1}`,
  concept_id: 'linear_equations',
  subconcept_code: 'test_equations',
  question_type: 'multiple_choice',
  question_text_en: 'Solve x + 1 = 2.',
  question_text_si: 'සමීකරණය විසඳන්න: x + 1 = 2.',
  difficulty_level: index < 4 ? 'easy' : index < 8 ? 'medium' : 'hard',
  options: ['1', '2', '3', '4'].map((answer, optionIndex) => ({
    id: `option-${index}-${optionIndex}`,
    option_code: 'ABCD'[optionIndex],
    option_text_en: answer,
    option_text_si: answer,
  })),
}))

test('pre question bank requires ten complete bilingual questions and 4/4/2 difficulty', () => {
  assert.equal(validatePreQuestionBank(questions), questions)
  assert.throws(() => validatePreQuestionBank(questions.slice(0, 9)))
  assert.throws(() => validatePreQuestionBank([
    { ...questions[0], difficulty_level: 'hard' }, ...questions.slice(1),
  ]))
  assert.throws(() => validatePreQuestionBank([
    { ...questions[0], question_text_si: '' }, ...questions.slice(1),
  ]))
})

test('response time is measured per active question and cannot be negative', () => {
  assert.equal(elapsedQuestionSeconds(1000, 2456), 1.46)
  assert.equal(elapsedQuestionSeconds(3000, 2990), 0)
})
