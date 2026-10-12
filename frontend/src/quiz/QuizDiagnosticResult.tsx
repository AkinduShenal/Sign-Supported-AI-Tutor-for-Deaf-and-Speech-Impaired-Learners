import { presentConfidenceInsight, presentResult } from './resultPresentation'
import type { QuizDiagnosticResult as Diagnostic, QuizLanguage } from './types'

export function QuizDiagnosticResult({ result, language }: { result: Diagnostic; language: QuizLanguage }) {
  const values = presentResult(result, language)
  const showEnglish = language !== 'si'
  return (
    <section className="quiz-panel quiz-complete" aria-labelledby="quiz-completed-title">
      <span className="quiz-complete-mark" aria-hidden="true">✓</span>
      <h2 id="quiz-completed-title">{showEnglish ? 'Assessment Complete' : 'ඇගයීම සම්පූර්ණයි'}</h2>
      {language === 'bilingual' && <p lang="si">ඇගයීම සම්පූර්ණයි</p>}
      <p>{showEnglish ? 'Here is your learning summary.' : 'මෙන්න ඔබේ ඉගෙනුම් සාරාංශය.'}</p>
      <dl className="quiz-result-list">
        <div><dt>{showEnglish ? 'Score' : 'ලකුණු'}{language === 'bilingual' && <small lang="si">ලකුණු</small>}</dt><dd>{values.score}</dd></div>
        <div><dt>{showEnglish ? 'Correct Answers' : 'නිවැරදි පිළිතුරු'}{language === 'bilingual' && <small lang="si">නිවැරදි පිළිතුරු</small>}</dt><dd>{values.correctAnswers}</dd></div>
        <div><dt>{showEnglish ? 'Wrong Answers' : 'වැරදි පිළිතුරු'}{language === 'bilingual' && <small lang="si">වැරදි පිළිතුරු</small>}</dt><dd>{values.wrongAnswers}</dd></div>
        <div><dt>{showEnglish ? 'Learning Level' : 'ඉගෙනුම් මට්ටම'}{language === 'bilingual' && <small lang="si">ඉගෙනුම් මට්ටම</small>}</dt><dd>{values.level}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').level}</small>}</dd></div>
        <div><dt>{showEnglish ? 'Needs More Practice' : 'තවත් පුහුණුව අවශ්‍ය'}{language === 'bilingual' && <small lang="si">තවත් පුහුණුව අවශ්‍ය</small>}</dt><dd>{values.practice}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').practice}</small>}</dd></div>
        <div><dt>{showEnglish ? 'Recommended Focus' : 'නිර්දේශිත අවධානය'}{language === 'bilingual' && <small lang="si">නිර්දේශිත අවධානය</small>}</dt><dd>{values.focus}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').focus}</small>}</dd></div>
        <div><dt>{showEnglish ? 'Recommended Support' : 'නිර්දේශිත සහාය'}{language === 'bilingual' && <small lang="si">නිර්දේශිත සහාය</small>}</dt><dd>{values.support}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').support}</small>}</dd></div>
      </dl>
      <div className="quiz-confidence-insight">
        <h3>{showEnglish ? 'Confidence Insight' : 'විශ්වාස මට්ටම පිළිබඳ සාරාංශය'}</h3>
        {language === 'bilingual' && <p lang="si" className="quiz-confidence-heading-si">විශ්වාස මට්ටම පිළිබඳ සාරාංශය</p>}
        {showEnglish && <p lang="en">{presentConfidenceInsight(result, 'en')}</p>}
        {language !== 'en' && <p lang="si">{presentConfidenceInsight(result, 'si')}</p>}
      </div>
    </section>
  )
}
