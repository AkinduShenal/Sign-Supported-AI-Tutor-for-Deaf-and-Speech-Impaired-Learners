import { useEffect, useState } from 'react'
import { getDynamicMlPrediction } from './api'
import type { QuizDynamicMlPrediction as Prediction, QuizLanguage } from './types'

type LocalizedMessage = { en: string; si: string }

const disclaimer: LocalizedMessage = {
  en: 'Experimental ML Prediction — Trained on Simulated Data — Not Research Validated',
  si: 'පරීක්ෂණාත්මක ML පුරෝකථනය — අනුකරණ දත්ත මත පුහුණු කළ — පර්යේෂණ මගින් තහවුරු කර නැත',
}
const unavailableMessages: Record<Exclude<Prediction['reason'], null>, LocalizedMessage> = {
  artifact_missing: {
    en: 'The local model or manifest is missing.',
    si: 'දේශීය මාදිලිය හෝ manifest ගොනුව හමු නොවීය.',
  },
  artifact_incompatible: {
    en: 'The model or manifest does not match this Dynamic Quiz.',
    si: 'මාදිලිය හෝ manifest ගොනුව මෙම Dynamic Quiz එකට නොගැළපේ.',
  },
  prediction_failed: {
    en: 'The model could not calculate a prediction for this session.',
    si: 'මෙම සැසිය සඳහා පුරෝකථනය ගණනය කිරීමට මාදිලියට නොහැකි විය.',
  },
  session_incomplete: {
    en: 'This session is not a completed supported Dynamic Quiz.',
    si: 'මෙම සැසිය සම්පූර්ණ කළ, සහාය දක්වන Dynamic Quiz එකක් නොවේ.',
  },
}

function LocalizedText({ language, en, si }: { language: QuizLanguage } & LocalizedMessage) {
  return <>
    {language !== 'si' && <span lang="en">{en}</span>}
    {language === 'bilingual' && <br />}
    {language !== 'en' && <span lang="si">{si}</span>}
  </>
}

function localizedRequestError(error: string): LocalizedMessage {
  if (/timed out/i.test(error)) return {
    en: error,
    si: 'පුරෝකථන ඉල්ලීමේ කාලය අවසන් විය. backend සම්බන්ධතාව පරීක්ෂා කර නැවත උත්සාහ කරන්න.',
  }
  if (/not found|404/i.test(error)) return {
    en: error,
    si: 'පුරෝකථන සේවාව හමු නොවීය. backend සම්බන්ධතාව පරීක්ෂා කරන්න.',
  }
  return { en: error, si: 'පුරෝකථනය ලබාගැනීමට නොහැකි විය. නැවත උත්සාහ කරන්න.' }
}

export function QuizDynamicMlPrediction({ sessionId, language }: { sessionId: string; language: QuizLanguage }) {
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [loading, setLoading] = useState(true)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setPrediction(null)
    setRequestError(null)
    setLoading(true)
    void getDynamicMlPrediction(sessionId, controller.signal)
      .then(result => { if (!controller.signal.aborted) setPrediction(result) })
      .catch(error => {
        if (!controller.signal.aborted) {
          setRequestError(error instanceof Error ? error.message : 'The prediction request failed.')
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [sessionId, retryCount])

  const available = prediction?.status === 'available' &&
    prediction.training_data_origin === 'SYNTHETIC_ENGINEERING_DEMO_ONLY' &&
    prediction.research_validated === false &&
    prediction.predictions.length === 4 &&
    prediction.predictions.every(item => Number.isFinite(item.probability) && item.probability >= 0 && item.probability <= 1)
  const unavailableReason = requestError ? localizedRequestError(requestError) : (prediction?.reason
    ? unavailableMessages[prediction.reason]
    : { en: 'The prediction response was incomplete.', si: 'පුරෝකථන ප්‍රතිචාරය අසම්පූර්ණයි.' })

  return <section className="quiz-ml-prediction" aria-labelledby="quiz-ml-prediction-title" lang={language === 'bilingual' ? undefined : language}>
    <h3 id="quiz-ml-prediction-title"><LocalizedText language={language} {...disclaimer} /></h3>
    <p><LocalizedText language={language}
      en="These are experimental model outputs for this saved Quiz session. They are not teacher-confirmed diagnoses."
      si="මේවා සුරැකි Quiz සැසිය සඳහා ලැබුණු පරීක්ෂණාත්මක මාදිලි ප්‍රතිදාන වේ. ගුරුවරයෙකු තහවුරු කළ නිගමන නොවේ." /></p>
    {loading ? <p role="status"><LocalizedText language={language} en="Checking experimental prediction…" si="පරීක්ෂණාත්මක පුරෝකථනය පරීක්ෂා කරමින්…" /></p> : available ? <>
      <dl className="quiz-ml-prediction-list">
        {prediction.predictions.map(item => <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{(item.probability * 100).toFixed(2)}%</dd>
          <span><LocalizedText language={language}
            en={item.flagged ? 'Flagged at 0.50' : 'Below 0.50 threshold'}
            si={item.flagged ? 'සලකුණු කර ඇත (≥ 0.50)' : '0.50 සීමාවට අඩුයි'} /></span>
        </div>)}
      </dl>
      <p className="quiz-ml-prediction-meta"><LocalizedText language={language}
        en={`Model: ${prediction.model_version}. The four probabilities are independent and need not total 100%.`}
        si={`මාදිලිය: ${prediction.model_version}. සම්භාවිතා හතර එකිනෙකට ස්වාධීන බැවින් එකතුව 100% විය යුතු නැත.`} /></p>
    </> : <div className="quiz-ml-unavailable">
      <p role="status"><LocalizedText language={language} en="Prediction Unavailable. Your Quiz score is still saved." si="පුරෝකථනය ලබාගත නොහැක. ඔබේ Quiz ලකුණු සුරැකි ඇත." /></p>
      <p><LocalizedText language={language} {...unavailableReason} /></p>
      <button className="quiz-primary quiz-ml-retry" type="button" onClick={() => setRetryCount(count => count + 1)}><LocalizedText language={language} en="Try prediction again" si="පුරෝකථනය නැවත උත්සාහ කරන්න" /></button>
    </div>}
  </section>
}
