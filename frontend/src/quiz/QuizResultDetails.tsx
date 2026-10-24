import { buildQuizResultMetrics } from './resultMetrics'
import type { QuizCollectionSession } from './pendingQuizWrites'
import type { QuizDiagnosticResult, QuizLanguage, QuizQuestion } from './types'

interface Props {
  result: QuizDiagnosticResult
  language: QuizLanguage
  questions: QuizQuestion[]
  collection: QuizCollectionSession | null
}

function Localized({ en, si, language }: { en: string; si: string; language: QuizLanguage }) {
  if (language === 'en') return <>{en}</>
  if (language === 'si') return <span lang="si">{si}</span>
  return <>{en}<small lang="si">{si}</small></>
}

const confidenceLabels = {
  low: { en: 'Low', si: 'අඩු' },
  medium: { en: 'Medium', si: 'මධ්‍යම' },
  high: { en: 'High', si: 'ඉහළ' },
} as const

export function QuizResultDetails({ result, language, questions, collection }: Props) {
  const metrics = buildQuizResultMetrics(result, questions, collection)
  if (!metrics) return null

  return <section className="quiz-result-details" aria-labelledby="quiz-result-details-title">
    <header className="quiz-result-details-heading">
      <span className="quiz-result-details-eyebrow"><Localized en="QUIZ ACTIVITY" si="ප්‍රශ්නාවලි ක්‍රියාකාරකම්" language={language} /></span>
      <h3 id="quiz-result-details-title"><Localized en="How you answered" si="ඔබ පිළිතුරු දුන් ආකාරය" language={language} /></h3>
    </header>

    <dl className="quiz-result-activity-summary">
      <div className="quiz-result-activity-summary-card quiz-result-activity-summary-card--time">
        <dt><Localized en="Average response time" si="සාමාන්‍ය පිළිතුරු කාලය" language={language} /></dt>
        <dd><strong>{metrics.averageResponseTimeSec.toFixed(2)}</strong><span>{language === 'si' ? 'තත්.' : 'sec'}</span></dd>
      </div>
      <div className="quiz-result-activity-summary-card quiz-result-activity-summary-card--confidence">
        <dt><Localized en="Confidence choices" si="විශ්වාස මට්ටම්" language={language} /></dt>
        <dd className="quiz-result-confidence-counts">
          {(['low', 'medium', 'high'] as const).map(level => <span key={level} className={`quiz-result-confidence-pill quiz-result-confidence-pill--${level}`}>
            <span><Localized {...confidenceLabels[level]} language={language} /></span>
            <strong>{metrics.confidenceCounts[level]}</strong>
          </span>)}
        </dd>
      </div>
      <div className="quiz-result-activity-summary-card quiz-result-activity-summary-card--attempts">
        <dt><Localized en="Total attempts" si="මුළු උත්සාහ ගණන" language={language} /></dt>
        <dd><strong>{metrics.totalAttempts ?? '—'}</strong></dd>
        <span className="quiz-result-activity-source"><Localized en="Including practice tries in this browser" si="මෙම බ්‍රවුසරයේ පුහුණු උත්සාහ සමඟ" language={language} /></span>
      </div>
    </dl>

    <details className="quiz-result-question-details">
      <summary className="quiz-result-activity-subheading">
        <span className="quiz-result-question-label"><Localized en="Question by question" si="එක් එක් ප්‍රශ්නය" language={language} /></span>
        <span className="quiz-result-question-count">{metrics.questions.length} / {result.questions_total}</span>
        <span className="quiz-result-question-chevron" aria-hidden="true" />
      </summary>
      <ol className="quiz-result-question-grid">
      {metrics.questions.map(row => <li key={row.questionOrder} className={`quiz-result-question-card ${row.isCorrect ? 'is-correct' : 'is-incorrect'}`}>
        <div className="quiz-result-question-top">
          <span className="quiz-result-question-number">{String(row.questionOrder).padStart(2, '0')}</span>
          <div className="quiz-result-question-name">
            <strong><Localized en={`Question ${row.questionOrder}`} si={`ප්‍රශ්නය ${row.questionOrder}`} language={language} /></strong>
            {row.questionCode && <code>{row.questionCode}</code>}
          </div>
          <span className="quiz-result-question-status"><Localized en={row.isCorrect ? 'Correct' : 'Incorrect'} si={row.isCorrect ? 'නිවැරදි' : 'වැරදි'} language={language} /></span>
        </div>
        <dl className="quiz-result-question-metrics">
          <div>
            <dt><Localized en="Confidence" si="විශ්වාසය" language={language} /></dt>
            <dd><Localized {...confidenceLabels[row.confidence]} language={language} /></dd>
          </div>
          <div>
            <dt><Localized en="Response time" si="පිළිතුරු කාලය" language={language} /></dt>
            <dd>{row.responseTimeSec.toFixed(2)} <span>{language === 'si' ? 'තත්.' : 'sec'}</span></dd>
          </div>
          <div>
            <dt><Localized en="Attempts" si="උත්සාහ" language={language} /></dt>
            <dd>{row.attemptCount ?? '—'}</dd>
          </div>
        </dl>
      </li>)}
      </ol>
    </details>
  </section>
}
