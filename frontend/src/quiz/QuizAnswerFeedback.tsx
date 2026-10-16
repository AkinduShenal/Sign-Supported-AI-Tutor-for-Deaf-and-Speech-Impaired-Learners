import type { QuizLanguage } from './types'

export function QuizAnswerFeedback({ correct, language }: { correct: boolean; language: QuizLanguage }) {
  return <div className={`quiz-answer-feedback ${correct ? 'is-correct' : 'is-incorrect'}`} role="status" aria-live="polite">
    <span className="quiz-answer-feedback-icon" aria-hidden="true">{correct ? '✓' : '✕'}</span>
    <div>
      {language !== 'si' && <strong lang="en">{correct ? 'Correct answer!' : 'Incorrect answer.'}</strong>}
      {language !== 'en' && <strong lang="si">{correct ? 'නිවැරදි පිළිතුරක්!' : 'වැරදි පිළිතුරක්.'}</strong>}
    </div>
  </div>
}
