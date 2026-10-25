import { useId } from 'react'
import { GAME_ML_LEVELS, formatMLProbability, isGameMLPrediction } from './mlPrediction'
import type { GameMLPredictionState } from './mlPrediction'
import './MLProficiencyCard.css'

interface MLProficiencyCardProps {
  state?: GameMLPredictionState
  /** No longer displayed; kept so existing visual test harnesses still type-check. */
  showExperimentalLabel?: boolean
}

/** Read-only presentation. No fetching, credentials, mock fallbacks or inference. */
export function MLProficiencyCard({ state = { status: 'unavailable' } }: MLProficiencyCardProps) {
  const id = useId()
  const prediction = state.status === 'ready' && isGameMLPrediction(state.prediction) ? state.prediction : null
  const status = state.status === 'ready' && !prediction ? 'unavailable' : state.status

  return <section className={`game-ml-card game-ml-card--${status}`}
    aria-labelledby={`${id}-title`} aria-busy={status === 'loading'}>
    <header className="game-ml-card__header">
      <div className="game-ml-card__heading">
        <span className="game-ml-card__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Z" />
          </svg>
        </span>
        <div>
          <p className="game-ml-card__eyebrow">Your learning summary</p>
          <h2 id={`${id}-title`}>ML Model Estimate</h2>
        </div>
      </div>
    </header>

    {prediction ? <>
      <div className="game-ml-card__results">
        <div className="game-ml-card__estimate" role="status" aria-live="polite" aria-atomic="true">
          <p>Estimated mathematical proficiency</p>
          <h3>{prediction.predicted_level}</h3>
          <p>An estimate from this Game session.</p>
        </div>
        <div className="game-ml-card__probabilities" role="group" aria-labelledby={`${id}-probabilities`}>
          <h3 id={`${id}-probabilities`}>Model-estimated probabilities</h3>
          {GAME_ML_LEVELS.map(level => <div className="game-ml-card__probability" key={level}
            data-estimated={prediction.predicted_level === level ? 'true' : 'false'}>
            <div className="game-ml-card__probability-label">
              <label htmlFor={`${id}-${level}`}>{level}</label>
              <span>{formatMLProbability(prediction.probabilities[level])}</span>
            </div>
            <progress id={`${id}-${level}`} max={1} value={prediction.probabilities[level]}
              aria-label={`${level} model-estimated probability`}
              aria-valuetext={formatMLProbability(prediction.probabilities[level])} />
          </div>)}
        </div>
      </div>
      <p className="game-ml-card__note">Model estimates can be uncertain. Your teacher can help you understand your progress.</p>
    </> : <div className="game-ml-card__message" role={status === 'error' ? 'alert' : 'status'} aria-atomic="true">
      <span className="game-ml-card__message-icon" aria-hidden="true">{status === 'loading' ? '…' : status === 'error' ? '!' : '—'}</span>
      <div>
        <h3>{status === 'loading' ? 'Preparing your estimate…' : status === 'error' ? 'Estimate could not be loaded' : 'Prediction unavailable'}</h3>
        <p>{status === 'loading' ? 'Please wait while your Game session is checked.'
          : status === 'error' ? 'You can still view your Game results above.'
            : 'An ML estimate is not available for this Game session. Your Game results are shown above.'}</p>
      </div>
    </div>}
  </section>
}
