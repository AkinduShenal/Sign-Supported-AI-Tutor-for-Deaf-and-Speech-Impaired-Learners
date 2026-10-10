import type { QuizLanguage } from './types'

export function QuizResultPlaceholder({ language }: { language: QuizLanguage }) {
  return (
    <section className="quiz-panel quiz-complete" aria-labelledby="quiz-completed-title">
      <span className="quiz-complete-mark" aria-hidden="true">✓</span>
      <h2 id="quiz-completed-title" lang={language === 'si' ? 'si' : 'en'}>{language === 'si' ? 'ඇගයීම අවසන්' : 'Assessment Completed'}</h2>
      {language === 'bilingual' && <p lang="si">ඇගයීම අවසන්</p>}
      {language !== 'si' && <p lang="en">Your responses have been recorded.</p>}
      {language !== 'en' && <p lang="si">ඔබගේ පිළිතුරු සටහන් කර ඇත.</p>}
    </section>
  )
}
