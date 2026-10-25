import test from 'node:test'
import assert from 'node:assert/strict'
import { buildMlFeatures, ML_FEATURE_COLUMNS } from '../src/quiz/mlFeatures.ts'
import type { QuizCollectionSession } from '../src/quiz/pendingQuizWrites.ts'
import type { QuizDiagnosticResult, QuizQuestion, QuizQuestionEvidence } from '../src/quiz/types.ts'

function fixture(correctPositions: number[]) {
  const questions: QuizQuestion[] = Array.from({ length: 10 }, (_, index) => ({
    id: `q${index + 1}`, question_code: `DEV-PRE-LE-${String(index + 1).padStart(2, '0')}`,
    concept_id: 'linear_equations', subconcept_code: 'one_step_addition', question_type: 'multiple_choice',
    question_text_en: 'Question', question_text_si: 'Question',
    difficulty_level: index < 4 ? 'easy' : index < 8 ? 'medium' : 'hard',
    options: ['A', 'B', 'C', 'D'].map(code => ({
      id: `q${index + 1}-${code}`, option_code: code, option_text_en: code, option_text_si: code,
    })),
  }))
  const evidence: QuizQuestionEvidence[] = questions.map((question, index) => {
    const isCorrect = correctPositions.includes(index + 1)
    return {
      question_order: index + 1, question_id: question.id, is_correct: isCorrect,
      confidence_level: index % 3 === 0 ? 'low' : index % 3 === 1 ? 'medium' : 'high',
      response_time_sec: index + 1, difficulty_level: question.difficulty_level,
      subconcept_code: question.subconcept_code,
      misconception_code: isCorrect ? null : ['inverse_operation', 'sign_error', 'inverse_operation', 'arithmetic_error', 'inverse_operation', 'sign_error', 'concept_confusion', 'inverse_operation', 'sign_error', 'arithmetic_error'][index],
    }
  })
  const collection: QuizCollectionSession = {
    request: {
      student_id: 'STU_TEST', concept_id: 'linear_equations', assessment_phase: 'pre_tutor',
      display_language: 'en', learning_cycle_id: 'cycle', client_session_id: 'test',
    },
    question_ids: questions.map(question => question.id), created: true,
    session: {
      quiz_session_id: 'QUIZ-test', student_id: 'STU_TEST', concept_id: 'linear_equations',
      learning_cycle_id: 'cycle', assessment_phase: 'pre_tutor', quiz_attempt_number: 1,
      display_language: 'en', status: 'completed', started_at: '2026-01-01T00:00:00Z',
      completed_at: '2026-01-01T00:01:00Z',
    },
    responses: evidence.map((row, index) => ({
      body: {
        question_id: row.question_id, selected_option_id: `q${index + 1}-${row.is_correct ? 'A' : 'B'}`,
        response_time_sec: row.response_time_sec, confidence_level: row.confidence_level,
        question_order: row.question_order, client_action_at: '2026-01-01T00:00:00Z',
      },
      saved: true, response_id: `r${index + 1}`, is_correct: row.is_correct,
      correct_option: row.is_correct ? null : questions[index].options[0],
    })),
    completion_requested: true, completed: true, closed: false, error: null,
  }
  const diagnostic: QuizDiagnosticResult = {
    quiz_session_id: 'QUIZ-test', questions_total: 10, questions_attempted: 10,
    correct_answers: correctPositions.length, mastery_level: 'medium', weak_subconcept: null,
    recommended_focus: null, recommended_support_level: 'medium',
    confidence_insight: { kind: 'neutral', high_confidence_incorrect_count: 0, low_confidence_correct_count: 0 },
    diagnostic_evidence: { question_evidence: evidence },
  }
  return { collection, questions, diagnostic }
}

test('the experimental JSON follows the 45 training columns and uses first answers', () => {
  const { collection, questions, diagnostic } = fixture([1, 4, 5, 9])
  collection.responses[1].practice_attempts = ['q2-A']
  const features = buildMlFeatures(collection, questions, diagnostic)
  assert.deepEqual(Object.keys(features), [...ML_FEATURE_COLUMNS])
  assert.equal(Object.keys(features).length, 45)
  assert.equal(features.correct_answers, 4)
  assert.equal(features.wrong_answers, 6)
  assert.equal(features.accuracy, 0.4)
  assert.equal(features.beginner_accuracy, 0.5)
  assert.equal(features.intermediate_accuracy, 0.25)
  assert.equal(features.advanced_accuracy, 0.5)
  assert.equal(features.q02_option_code, 'B')
  assert.equal(features.q02_correct, 0)
  assert.equal(features.avg_response_time_sec, 5.5)
  assert.equal(features.median_response_time_sec, 5.5)
  assert.equal(features.avg_correct_response_time_sec, 4.75)
  assert.equal(features.avg_wrong_response_time_sec, 6)
  assert.equal(features.max_consecutive_wrong, 3)
  assert.equal(features.correct_first5_count, 3)
  assert.equal(features.correct_last5_count, 1)
  assert.equal('student_code' in features, false)
  assert.equal('student_id' in features, false)
})

test('missing subgroup averages are null and missing tag evidence blocks copying', () => {
  const allCorrect = fixture([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  assert.equal(buildMlFeatures(allCorrect.collection, allCorrect.questions, allCorrect.diagnostic).avg_wrong_response_time_sec, null)
  const allWrong = fixture([])
  assert.equal(buildMlFeatures(allWrong.collection, allWrong.questions, allWrong.diagnostic).avg_correct_response_time_sec, null)
  allWrong.diagnostic.diagnostic_evidence!.question_evidence![0].misconception_code = null
  assert.throws(() => buildMlFeatures(allWrong.collection, allWrong.questions, allWrong.diagnostic))
})

test('response-time subgroup means reproduce both workbook rounding ties', () => {
  const data = fixture([1, 2, 3, 4, 5, 6, 7, 8])
  for (const [index, seconds] of [21.21, 8.47, 10.86, 5.86, 5.05, 4.44, 11.06, 4.1].entries()) {
    data.collection.responses[index].body.response_time_sec = seconds
    data.diagnostic.diagnostic_evidence!.question_evidence![index].response_time_sec = seconds
  }
  assert.equal(buildMlFeatures(data.collection, data.questions, data.diagnostic).avg_correct_response_time_sec, 8.8812)
  for (const [index, seconds] of [43.35, 9.19, 4.93, 5.16, 11.31, 8.47, 4.3, 8.38].entries()) {
    data.collection.responses[index].body.response_time_sec = seconds
    data.diagnostic.diagnostic_evidence!.question_evidence![index].response_time_sec = seconds
  }
  assert.equal(buildMlFeatures(data.collection, data.questions, data.diagnostic).avg_correct_response_time_sec, 11.8863)
})

test('a changed question bank or contradictory analysis blocks copying', () => {
  const data = fixture([1])
  data.questions[0].question_code = 'NEW-BANK-01'
  assert.throws(() => buildMlFeatures(data.collection, data.questions, data.diagnostic))
  data.questions[0].question_code = 'DEV-PRE-LE-01'
  data.diagnostic.diagnostic_evidence!.question_evidence![0].response_time_sec += 1
  assert.throws(() => buildMlFeatures(data.collection, data.questions, data.diagnostic))
})

test('dynamic draft sessions cannot produce fixed-bank ML features', () => {
  const data = fixture([1, 4, 5, 9])
  data.collection.session!.bank_version = 'pp1_dynamic_v1_DRAFT'
  data.questions[0].question_code = 'PP1-DYN-S01-V01'
  assert.throws(() => buildMlFeatures(data.collection, data.questions, data.diagnostic))
})
