import test from 'node:test'
import assert from 'node:assert/strict'
import type { QuizQuestion } from '../src/quiz/types.ts'
import { elapsedQuestionSeconds, QUIZ_LEVELS, transitionAfterAnswers, validatePreQuestionBank } from '../src/quiz/workflow.ts'

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
  assert.deepEqual(validatePreQuestionBank(questions).map(question => question.id), questions.map(question => question.id))
  assert.throws(() => validatePreQuestionBank(questions.slice(0, 9)))
  assert.throws(() => validatePreQuestionBank([
    { ...questions[0], difficulty_level: 'hard' }, ...questions.slice(1),
  ]))
  assert.throws(() => validatePreQuestionBank([
    { ...questions[0], question_text_si: '' }, ...questions.slice(1),
  ]))
})

test('official questions progress through four Beginner, four Intermediate, and two Advanced items', () => {
  const mixed = [questions[8], questions[4], questions[0], questions[9], questions[5], questions[1], questions[6], questions[2], questions[7], questions[3]]
  const ordered = validatePreQuestionBank(mixed)
  assert.deepEqual(ordered.map(question => question.difficulty_level), [
    'easy', 'easy', 'easy', 'easy', 'medium', 'medium', 'medium', 'medium', 'hard', 'hard',
  ])
  assert.deepEqual(ordered.slice(0, 4).map(question => question.id), ['question-0', 'question-1', 'question-2', 'question-3'])
  assert.equal(QUIZ_LEVELS.easy.en, 'Beginner Level')
  assert.equal(QUIZ_LEVELS.medium.en, 'Intermediate Level')
  assert.equal(QUIZ_LEVELS.hard.en, 'Advanced Level')
  assert.equal(QUIZ_LEVELS.easy.si, 'ආරම්භක මට්ටම')
  assert.equal(QUIZ_LEVELS.medium.si, 'අතරමැදි මට්ටම')
  assert.equal(QUIZ_LEVELS.hard.si, 'උසස් මට්ටම')
  assert.equal(transitionAfterAnswers(4), 'easy')
  assert.equal(transitionAfterAnswers(8), 'medium')
  assert.equal(transitionAfterAnswers(10), null)
})

test('response time is measured per active question and cannot be negative', () => {
  assert.equal(elapsedQuestionSeconds(1000, 2456), 1.46)
  assert.equal(elapsedQuestionSeconds(3000, 2990), 0)
})
