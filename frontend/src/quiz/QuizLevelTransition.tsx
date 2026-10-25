import type { QuizLanguage } from './types'

const transitions = {
  easy: {
    titleEn: 'Beginner Level Completed', titleSi: 'ආරම්භක මට්ටම සම්පූර්ණයි',
    praiseEn: 'Great work! You cleared the first level.', praiseSi: 'හොඳයි! ඔබ පළමු මට්ටම අවසන් කළා.',
    nextEn: 'You are now moving to the Intermediate Level.',
    nextSi: 'දැන් ඔබ අතරමැදි මට්ටමට පිවිසෙයි.',
    nextLabelEn: 'Intermediate', nextLabelSi: 'අතරමැදි',
    step: 1,
  },
  medium: {
    titleEn: 'Intermediate Level Completed', titleSi: 'අතරමැදි මට්ටම සම්පූර්ණයි',
    praiseEn: 'Amazing progress! Two levels down.', praiseSi: 'නියම ප්‍රගතියක්! මට්ටම් දෙකක් අවසන්.',
    nextEn: 'You are now moving to the Advanced Level.',
    nextSi: 'දැන් ඔබ උසස් මට්ටමට පිවිසෙයි.',
    nextLabelEn: 'Advanced', nextLabelSi: 'උසස්',
    step: 2,
  },
} as const

export function QuizLevelTransition({ completedLevel, language, onContinue }: {
  completedLevel: 'easy' | 'medium'
  language: QuizLanguage
  onContinue: () => void
}) {
  const copy = transitions[completedLevel]
  return <section className={`quiz-panel quiz-level-transition quiz-level-transition--${completedLevel}`} aria-labelledby="quiz-transition-title">
    <div className="quiz-level-confetti" aria-hidden="true">✦ <span>✧</span> ✦</div>
    <span className="quiz-level-medal" aria-hidden="true">★</span>
    <span className="quiz-kicker">{language === 'si' ? 'මට්ටම අවසන්!' : 'Level complete!'}</span>
    <h2 id="quiz-transition-title">{language === 'si' ? copy.titleSi : copy.titleEn}</h2>
    {language === 'bilingual' && <p lang="si">{copy.titleSi}</p>}
    {language !== 'si' && <p lang="en"><strong>{copy.praiseEn}</strong> {copy.nextEn}</p>}
    {language !== 'en' && <p lang="si"><strong>{copy.praiseSi}</strong> {copy.nextSi}</p>}
    <div className="quiz-level-journey" aria-hidden="true">
      <span className="is-done">✓</span><i className="is-done" />
      <span className={copy.step === 2 ? 'is-done' : ''}>{copy.step === 2 ? '✓' : '2'}</span><i className={copy.step === 2 ? 'is-done' : ''} />
      <span>3</span>
    </div>
    <div className="quiz-level-next">{language === 'si' ? 'ඊළඟ මට්ටම' : 'Up next'} <strong>{language === 'si' ? copy.nextLabelSi : copy.nextLabelEn}</strong></div>
    <button className="quiz-primary" type="button" onClick={onContinue}>{language === 'si' ? 'ඉදිරියට යමු →' : 'Let’s go →'}</button>
  </section>
}
