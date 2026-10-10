import type { ConfidenceLevel, QuizLanguage } from './types'

const levels: Array<{ value: ConfidenceLevel; en: string; si: string }> = [
  { value: 'low', en: 'Low', si: 'අඩු' },
  { value: 'medium', en: 'Medium', si: 'මධ්‍යම' },
  { value: 'high', en: 'High', si: 'ඉහළ' },
]

interface ConfidenceSelectorProps {
  language: QuizLanguage
  value: ConfidenceLevel | null
  disabled: boolean
  onChange: (level: ConfidenceLevel) => void
}

export function ConfidenceSelector({ language, value, disabled, onChange }: ConfidenceSelectorProps) {
  return (
    <fieldset className="quiz-confidence" disabled={disabled}>
      <legend>
        {language !== 'si' && <span lang="en">How confident are you about your answer?</span>}
        {language !== 'en' && <span lang="si">ඔබගේ පිළිතුර ගැන ඔබට කොපමණ විශ්වාසද?</span>}
      </legend>
      <div className="quiz-confidence-options">
        {levels.map(level => (
          <label key={level.value} className={value === level.value ? 'is-selected' : ''}>
            <input
              type="radio"
              name="quiz-confidence"
              value={level.value}
              checked={value === level.value}
              onChange={() => onChange(level.value)}
            />
            {language !== 'si' && <span lang="en">{level.en}</span>}
            {language !== 'en' && <span lang="si">{level.si}</span>}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
