import type { QuizLanguage } from './types'

const transitions = {
  easy: {
    titleEn: 'Beginner Level Completed', titleSi: 'ආරම්භක මට්ටම සම්පූර්ණයි',
    praiseEn: 'Great work!', praiseSi: 'හොඳයි!',
    nextEn: 'You are now moving to the Intermediate Level.',
    nextSi: 'දැන් ඔබ අතරමැදි මට්ටමට පිවිසෙයි.',
  },
  medium: {
    titleEn: 'Intermediate Level Completed', titleSi: 'අතරමැදි මට්ටම සම්පූර්ණයි',
    praiseEn: 'Well done!', praiseSi: 'ඉතා හොඳයි!',
    nextEn: 'You are now moving to the Advanced Level.',
    nextSi: 'දැන් ඔබ උසස් මට්ටමට පිවිසෙයි.',
  },
} as const

export function QuizLevelTransition({ completedLevel, language, onContinue }: {
  completedLevel: 'easy' | 'medium'
  language: QuizLanguage
  onContinue: () => void
}) {
  const copy = transitions[completedLevel]
  return <section className="quiz-panel quiz-level-transition" aria-labelledby="quiz-transition-title">
    <span className="quiz-kicker">{language === 'si' ? 'මට්ටම අවසන්' : 'Level complete'}</span>
    <h2 id="quiz-transition-title">{language === 'si' ? copy.titleSi : copy.titleEn}</h2>
    {language === 'bilingual' && <p lang="si">{copy.titleSi}</p>}
    {language !== 'si' && <p lang="en"><strong>{copy.praiseEn}</strong> {copy.nextEn}</p>}
    {language !== 'en' && <p lang="si"><strong>{copy.praiseSi}</strong> {copy.nextSi}</p>}
    <button className="quiz-primary" type="button" onClick={onContinue}>{language === 'si' ? 'ඉදිරියට' : 'Continue'}</button>
  </section>
}
