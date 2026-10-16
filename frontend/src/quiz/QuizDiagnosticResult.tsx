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
        <div><dt>{showEnglish ? 'Incorrect Answers' : 'වැරදි පිළිතුරු'}{language === 'bilingual' && <small lang="si">වැරදි පිළිතුරු</small>}</dt><dd>{values.wrongAnswers}</dd></div>
        <div><dt>{showEnglish ? 'Understanding Level' : 'අවබෝධ මට්ටම'}{language === 'bilingual' && <small lang="si">අවබෝධ මට්ටම</small>}</dt><dd>{values.level}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').level}</small>}</dd></div>
        <div><dt>{showEnglish ? 'Needs More Practice' : 'තවත් පුහුණුව අවශ්‍ය ප්‍රදේශය'}{language === 'bilingual' && <small lang="si">තවත් පුහුණුව අවශ්‍ය ප්‍රදේශය</small>}</dt><dd>{values.practice}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').practice}</small>}</dd></div>
        <div><dt>{showEnglish ? 'Recommended Focus' : 'නිර්දේශිත පුහුණු අවධානය'}{language === 'bilingual' && <small lang="si">නිර්දේශිත පුහුණු අවධානය</small>}</dt><dd>{values.focus}{language === 'bilingual' && <small lang="si">{presentResult(result, 'si').focus}</small>}</dd></div>
      </dl>
      {language !== 'si' && <p lang="en">The score uses your first answer to each question. Practice tries do not change it.</p>}
      {language !== 'en' && <p lang="si">ලකුණු සඳහා සෑම ප්‍රශ්නයකම පළමු පිළිතුර පමණක් ගණන් කෙරේ. පුහුණු උත්සාහවලින් ලකුණු වෙනස් නොවේ.</p>}
      <div className="quiz-confidence-insight">
        <h3>{showEnglish ? 'Confidence Insight' : 'පිළිතුරු පිළිබඳ විශ්වාසයේ සාරාංශය'}</h3>
        {language === 'bilingual' && <p lang="si" className="quiz-confidence-heading-si">පිළිතුරු පිළිබඳ විශ්වාසයේ සාරාංශය</p>}
        {showEnglish && <p lang="en">{presentConfidenceInsight(result, 'en')}</p>}
        {language !== 'en' && <p lang="si">{presentConfidenceInsight(result, 'si')}</p>}
      </div>
    </section>
  )
}
