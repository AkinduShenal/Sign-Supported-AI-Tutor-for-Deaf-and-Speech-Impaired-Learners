import { useState, type CSSProperties } from 'react'
import { QuizReactionBoy } from './QuizReactionBoy'
import { QuizDynamicMlPrediction } from './QuizDynamicMlPrediction'
import { QuizResultDetails } from './QuizResultDetails'
import type { MlFeatures } from './mlFeatures'
import type { QuizCollectionSession } from './pendingQuizWrites'
import { presentResult } from './resultPresentation'
import { isDynamicQuizResultSession } from './resultMetrics'
import type { QuizDiagnosticResult as Diagnostic, QuizLanguage, QuizQuestion } from './types'

type ResultIconName = 'correct' | 'incorrect'

function ResultIcon({ name }: { name: ResultIconName }) {
  return <svg className="quiz-result-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {name === 'correct' && <path d="m5 12 4.5 4.5L19 7" />}
    {name === 'incorrect' && <path d="M6 6 18 18M18 6 6 18" />}
  </svg>
}

export function QuizDiagnosticResult({ result, language, bankVersion, mlFeatures, questions, collection, onContinueToGame }: { result: Diagnostic; language: QuizLanguage; bankVersion?: string | null; mlFeatures?: MlFeatures | null; questions: QuizQuestion[]; collection: QuizCollectionSession | null; onContinueToGame?: () => void }) {
  const [copyStatus, setCopyStatus] = useState('')
  const values = presentResult(result, language)
  const showEnglish = language !== 'si'
  const scorePercent = Math.min(100, Math.max(0, Math.round(result.correct_answers / Math.max(result.questions_total, 1) * 100)))
  const scoreStyle = { '--quiz-score-percent': `${scorePercent}%` } as CSSProperties
  const dynamicSession = isDynamicQuizResultSession(result.quiz_session_id, bankVersion, collection, questions)

  return (
    <section className="quiz-panel quiz-complete quiz-complete--diagnostic" aria-labelledby="quiz-completed-title">
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
      </dl>

      {dynamicSession && <QuizDynamicMlPrediction sessionId={result.quiz_session_id} language={language} />}

      <QuizResultDetails result={result} language={language} questions={questions} collection={collection} />

      <div className="quiz-score-note">
        {language !== 'si' && <p lang="en">The score uses your first answer to each question. Practice tries do not change it.</p>}
        {language !== 'en' && <p lang="si">ලකුණු සඳහා සෑම ප්‍රශ්නයකම පළමු පිළිතුර පමණක් ගණන් කෙරේ. පුහුණු උත්සාහවලින් ලකුණු වෙනස් නොවේ.</p>}
      </div>
      {!dynamicSession && <div className="quiz-ml-demo" lang="en">
        <h3>ML prediction</h3>
        <p>Quiz session: <code>{result.quiz_session_id}</code></p>
        {mlFeatures ? <>
          <p>No prediction has been generated in the app. Copy this fixed Quiz session’s 45 inputs for the Colab model; the JSON contains no student code or personal details.</p>
          <button className="quiz-primary" type="button" onClick={() => {
            if (!navigator.clipboard?.writeText) {
              setCopyStatus('Clipboard access is unavailable in this browser.')
              return
            }
            void navigator.clipboard.writeText(JSON.stringify(mlFeatures, null, 2))
              .then(() => setCopyStatus('ML features copied as JSON.'))
              .catch(() => setCopyStatus('Clipboard access failed. Please allow clipboard access and try again.'))
          }}>Copy ML Features</button>
        </> : <p>No prediction is available. The Quiz model is not connected to this app.</p>}
        {copyStatus && <p role="status">{copyStatus}</p>}
      </div>}
      {onContinueToGame && <div className="quiz-result-next-step">
        <button className="quiz-primary quiz-continue-game" type="button" onClick={onContinueToGame}>
          {language !== 'si' && <span>Continue to Game</span>}
          {language !== 'en' && <span lang="si">ක්‍රීඩාවට ඉදිරියට යන්න</span>}
          <span aria-hidden="true">→</span>
        </button>
      </div>}
    </section>
  )
}
