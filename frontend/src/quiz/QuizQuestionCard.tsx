import type { QuizLanguage, QuizQuestion } from './types'

interface QuizQuestionCardProps {
  question: QuizQuestion
  language: QuizLanguage
  selectedOptionId: string | null
  disabled: boolean
  onSelect: (optionId: string) => void
}

export function QuizQuestionCard({ question, language, selectedOptionId, disabled, onSelect }: QuizQuestionCardProps) {
  const showEnglish = language !== 'si'
  const showSinhala = language !== 'en'

  return (
    <fieldset className="quiz-question-card" disabled={disabled}>
      <legend className="quiz-field-label">
        {showEnglish && <span lang="en">Choose one answer</span>}
        {showSinhala && <span lang="si">එක් පිළිතුරක් තෝරන්න</span>}
      </legend>
      <div className="quiz-question-prompt">
        {showEnglish && <p lang="en">{question.question_text_en}</p>}
        {showSinhala && <p lang="si">{question.question_text_si}</p>}
      </div>
      <div className="quiz-options">
        {question.options.map(option => (
          <label className={`quiz-option${selectedOptionId === option.id ? ' is-selected' : ''}`} key={option.id}>
            <input
              type="radio"
              name="quiz-answer"
              value={option.id}
              checked={selectedOptionId === option.id}
              onChange={() => onSelect(option.id)}
            />
            <span className="quiz-option-code" aria-hidden="true">{option.option_code}</span>
            <span className="quiz-option-text">
              {showEnglish && <span lang="en">{option.option_text_en}</span>}
              {showSinhala && (language === 'si' || option.option_text_si !== option.option_text_en) && (
                <span lang="si">{option.option_text_si}</span>
              )}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
