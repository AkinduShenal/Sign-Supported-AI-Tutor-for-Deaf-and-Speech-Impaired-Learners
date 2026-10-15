import { QUIZ_LENGTH, QUIZ_LEVELS } from './workflow'
import type { DifficultyLevel, QuizLanguage } from './types'

interface QuizProgressProps {
  questionNumber: number
  language: QuizLanguage
  difficulty: DifficultyLevel
}

export function QuizProgress({ questionNumber, language, difficulty }: QuizProgressProps) {
  const level = QUIZ_LEVELS[difficulty]
  return (
    <div className="quiz-progress">
      <div className="quiz-level-heading">
        {language !== 'si' && <strong lang="en">{level.en}</strong>}
        {language !== 'en' && <span lang="si">{level.si}</span>}
      </div>
      <div className="quiz-progress-label">
        <strong lang={language === 'si' ? 'si' : 'en'}>{language === 'si' ? `ප්‍රශ්නය ${questionNumber} / ${QUIZ_LENGTH}` : `Question ${questionNumber} of ${QUIZ_LENGTH}`}</strong>
        {language === 'bilingual' && <span lang="si">ප්‍රශ්නය {questionNumber} / {QUIZ_LENGTH}</span>}
      </div>
      <progress value={questionNumber - 1} max={QUIZ_LENGTH} aria-label={language === 'si' ? 'සම්පූර්ණ කළ ප්‍රශ්න' : 'Questions completed'} />
    </div>
  )
}
