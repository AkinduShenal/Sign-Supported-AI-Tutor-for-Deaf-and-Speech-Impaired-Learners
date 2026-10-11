import { QUIZ_LENGTH } from './workflow'
import type { QuizLanguage } from './types'

interface QuizProgressProps {
  questionNumber: number
  language: QuizLanguage
}

export function QuizProgress({ questionNumber, language }: QuizProgressProps) {
  return (
    <div className="quiz-progress">
      <div className="quiz-progress-label">
        <strong lang={language === 'si' ? 'si' : 'en'}>{language === 'si' ? `ප්‍රශ්නය ${questionNumber} / ${QUIZ_LENGTH}` : `Question ${questionNumber} of ${QUIZ_LENGTH}`}</strong>
        {language === 'bilingual' && <span lang="si">ප්‍රශ්නය {questionNumber} / {QUIZ_LENGTH}</span>}
      </div>
      <progress value={questionNumber - 1} max={QUIZ_LENGTH} aria-label={language === 'si' ? 'සම්පූර්ණ කළ ප්‍රශ්න' : 'Questions completed'} />
    </div>
  )
}
