import { API_BASE_URL, completeQuizSession, createPreQuizSession, getQuizSessionQuestions, submitQuizAnswer } from './api'
import { PendingQuizWrites } from './pendingQuizWrites'

export function openQuizCollectionStore(): PendingQuizWrites {
  return new PendingQuizWrites(localStorage, {
    create: createPreQuizSession,
    questions: getQuizSessionQuestions,
    answer: submitQuizAnswer,
    complete: completeQuizSession,
  }, API_BASE_URL)
}
