import type { CSSProperties } from 'react'
import { QuizReactionBoy } from './QuizReactionBoy'
import { presentConfidenceInsight, presentResult } from './resultPresentation'
import type { QuizDiagnosticResult as Diagnostic, QuizLanguage } from './types'

type ResultIconName = 'correct' | 'incorrect' | 'level' | 'practice' | 'focus'

function ResultIcon({ name }: { name: ResultIconName }) {
  return <svg className="quiz-result-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {name === 'correct' && <path d="m5 12 4.5 4.5L19 7" />}
    {name === 'incorrect' && <path d="M6 6 18 18M18 6 6 18" />}
    {name === 'level' && <path d="m12 2 2.8 6.2L21 11l-6.2 2.8L12 20l-2.8-6.2L3 11l6.2-2.8L12 2Z" />}
    {name === 'practice' && <><path d="M12 6c-2.5-1.5-5.3-1.8-9-1v14c3.7-.8 6.5-.5 9 1 2.5-1.5 5.3-1.8 9-1V5c-3.7-.8-6.5-.5-9 1ZM12 6v14" /></>}
    {name === 'focus' && <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" /></>}
  </svg>
}

export function QuizDiagnosticResult({ result, language }: { result: Diagnostic; language: QuizLanguage }) {
  const values = presentResult(result, language)
  const sinhalaValues = language === 'bilingual' ? presentResult(result, 'si') : null
  const showEnglish = language !== 'si'
  const scorePercent = Math.min(100, Math.max(0, Math.round(result.correct_answers / Math.max(result.questions_total, 1) * 100)))
  const scoreStyle = { '--quiz-score-percent': `${scorePercent}%` } as CSSProperties

  return (
    <section className={`quiz-panel quiz-complete quiz-complete--diagnostic quiz-complete--${result.mastery_level}`} aria-labelledby="quiz-completed-title">
      <div className="quiz-complete-hero">
        <div className="quiz-complete-hero-copy">
          <span className="quiz-complete-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" focusable="false"><path d="m24 5 4.6 11.8L41 18l-9.5 8 3 12.3L24 31.6l-10.5 6.7 3-12.3L7 18l12.4-1.2L24 5Z" fill="currentColor" /></svg>
          </span>
          <span className="quiz-complete-eyebrow">{showEnglish ? 'You did it!' : 'ඔබ එය සම්පූර්ණ කළා!'}</span>
          <h2 id="quiz-completed-title">{showEnglish ? 'Assessment Complete' : 'ඇගයීම සම්පූර්ණයි'}</h2>
          {language === 'bilingual' && <p className="quiz-complete-title-si" lang="si">ඇගයීම සම්පූර්ණයි</p>}
          <p>{showEnglish ? 'You finished every question. See what you learned and where to go next.' : 'ඔබ සියලු ප්‍රශ්න සම්පූර්ණ කළා. ඔබ ඉගෙන ගත් දේ සහ ඊළඟට පුහුණු විය යුතු දේ බලන්න.'}</p>
        </div>
        <QuizReactionBoy correct />
      </div>

      <div className="quiz-result-heading">
        <div>
          <span className="quiz-result-kicker">{showEnglish ? 'YOUR RESULTS' : 'ඔබේ ප්‍රතිඵල'}</span>
          <h3>{showEnglish ? 'Your learning snapshot' : 'ඔබේ ඉගෙනුම් සාරාංශය'}</h3>
        </div>
        <span className="quiz-result-total">{showEnglish ? `${result.questions_attempted} questions completed` : `ප්‍රශ්න ${result.questions_attempted}ක් සම්පූර්ණයි`}</span>
      </div>

      <dl className="quiz-result-list">
        <div className="quiz-result-card quiz-result-card--score">
          <dt>{showEnglish ? 'Score' : 'ලකුණු'}{language === 'bilingual' && <small lang="si">ලකුණු</small>}</dt>
          <dd>
            <span className="quiz-score-number">{values.score}</span>
            <span className="quiz-score-ring" style={scoreStyle} aria-hidden="true"><span>{scorePercent}%</span></span>
          </dd>
        </div>
        <div className="quiz-result-card quiz-result-card--correct">
          <dt><ResultIcon name="correct" />{showEnglish ? 'Correct Answers' : 'නිවැරදි පිළිතුරු'}{language === 'bilingual' && <small lang="si">නිවැරදි පිළිතුරු</small>}</dt>
          <dd>{values.correctAnswers}</dd>
        </div>
        <div className="quiz-result-card quiz-result-card--incorrect">
          <dt><ResultIcon name="incorrect" />{showEnglish ? 'Incorrect Answers' : 'වැරදි පිළිතුරු'}{language === 'bilingual' && <small lang="si">වැරදි පිළිතුරු</small>}</dt>
          <dd>{values.wrongAnswers}</dd>
        </div>
        <div className="quiz-result-card quiz-result-card--level">
          <dt><ResultIcon name="level" />{showEnglish ? 'Understanding Level' : 'අවබෝධ මට්ටම'}{language === 'bilingual' && <small lang="si">අවබෝධ මට්ටම</small>}</dt>
          <dd>{values.level}{sinhalaValues && <small lang="si">{sinhalaValues.level}</small>}</dd>
        </div>
        <div className="quiz-result-card quiz-result-card--practice">
          <dt><ResultIcon name="practice" />{showEnglish ? 'Needs More Practice' : 'තවත් පුහුණුව අවශ්‍ය ප්‍රදේශය'}{language === 'bilingual' && <small lang="si">තවත් පුහුණුව අවශ්‍ය ප්‍රදේශය</small>}</dt>
          <dd>{values.practice}{sinhalaValues && <small lang="si">{sinhalaValues.practice}</small>}</dd>
        </div>
        <div className="quiz-result-card quiz-result-card--focus">
          <dt><ResultIcon name="focus" />{showEnglish ? 'Recommended Focus' : 'නිර්දේශිත පුහුණු අවධානය'}{language === 'bilingual' && <small lang="si">නිර්දේශිත පුහුණු අවධානය</small>}</dt>
          <dd>{values.focus}{sinhalaValues && <small lang="si">{sinhalaValues.focus}</small>}</dd>
        </div>
      </dl>

      <div className="quiz-confidence-insight">
        <div className="quiz-confidence-insight-heading">
          <span className="quiz-confidence-insight-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18h6M10 22h4M9 14c-1.8-1-3-3-3-5a6 6 0 0 1 12 0c0 2-1.2 4-3 5-.8.5-1 1.3-1 2h-4c0-.7-.2-1.5-1-2Z" /></svg></span>
          <div>
            <h3>{showEnglish ? 'Confidence Insight' : 'පිළිතුරු පිළිබඳ විශ්වාසයේ සාරාංශය'}</h3>
            {language === 'bilingual' && <p lang="si" className="quiz-confidence-heading-si">පිළිතුරු පිළිබඳ විශ්වාසයේ සාරාංශය</p>}
          </div>
        </div>
        {showEnglish && <p lang="en">{presentConfidenceInsight(result, 'en')}</p>}
        {language !== 'en' && <p lang="si">{presentConfidenceInsight(result, 'si')}</p>}
      </div>

      <div className="quiz-score-note">
        {language !== 'si' && <p lang="en">The score uses your first answer to each question. Practice tries do not change it.</p>}
        {language !== 'en' && <p lang="si">ලකුණු සඳහා සෑම ප්‍රශ්නයකම පළමු පිළිතුර පමණක් ගණන් කෙරේ. පුහුණු උත්සාහවලින් ලකුණු වෙනස් නොවේ.</p>}
      </div>
    </section>
  )
}
