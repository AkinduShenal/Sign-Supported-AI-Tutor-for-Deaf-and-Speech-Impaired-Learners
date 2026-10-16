import type { QuizLanguage, QuizOption } from './types'

interface QuizAnswerFeedbackProps {
  correct: boolean
  correctOption: QuizOption | null
  language: QuizLanguage
  attemptNumber: number
  canRetry: boolean
}

export function QuizAnswerFeedback({ correct, correctOption, language, attemptNumber, canRetry }: QuizAnswerFeedbackProps) {
  return <div className={`quiz-answer-feedback ${correct ? 'is-correct' : 'is-incorrect'}`} role="status" aria-live="polite">
    <span className="quiz-answer-feedback-icon" aria-hidden="true">{correct ? '✓' : '✕'}</span>
    <div>
      {language !== 'si' && <strong lang="en">{correct ? 'Correct answer!' : canRetry ? 'Incorrect. Try again.' : 'Incorrect answer.'}</strong>}
      {language !== 'en' && <strong lang="si">{correct ? 'නිවැරදි පිළිතුරක්!' : canRetry ? 'වැරදියි. නැවත උත්සාහ කරන්න.' : 'වැරදි පිළිතුරක්.'}</strong>}
      {language !== 'si' && <span lang="en">Attempt {attemptNumber} of 3{canRetry ? ` · ${3 - attemptNumber} ${attemptNumber === 2 ? 'try' : 'tries'} left` : ''}</span>}
      {language !== 'en' && <span lang="si">උත්සාහය {attemptNumber}/3{canRetry ? ` · තවත් උත්සාහ ${3 - attemptNumber}ක් ඇත` : ''}</span>}
      {!correct && !canRetry && correctOption && <div className="quiz-correct-answer">
        {language !== 'si' && <span lang="en">Correct answer: {correctOption.option_code}. {correctOption.option_text_en}</span>}
        {language !== 'en' && <span lang="si">නිවැරදි පිළිතුර: {correctOption.option_code}. {correctOption.option_text_si}</span>}
      </div>}
      {!correct && !canRetry && !correctOption && <span>{language === 'si' ? 'නිවැරදි පිළිතුර ලබාගත නොහැක. පර්යේෂකයාට දන්වන්න.' : 'The correct answer is unavailable. Please tell the researcher.'}</span>}
    </div>
  </div>
}
