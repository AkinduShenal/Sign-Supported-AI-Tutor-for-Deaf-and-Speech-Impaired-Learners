import type { TaskAttemptSummary } from './types'
import { useLanguage } from './i18n/useLanguage'
import './GameActivity.css'

interface GameSummaryProps {
  summaries: TaskAttemptSummary[]
}

export function GameSummary({ summaries }: GameSummaryProps) {
  const { strings } = useLanguage()
  const successfulCount = summaries.filter((summary) => summary.isSuccessful).length

  return (
    <section className="game-summary" aria-labelledby="game-summary-heading">
      <h2 id="game-summary-heading">{strings.sessionComplete}</h2>
      <p>{strings.tasksSolved(successfulCount, summaries.length)}</p>
      <ul className="game-summary-list">
        {summaries.map((summary, index) => (
          <li key={summary.taskId}>
            <span className="game-summary-icon" aria-hidden="true">
              {summary.isSuccessful ? '✓' : summary.skipped ? '→' : '✗'}
            </span>
            <span>
              Task {index + 1}:{' '}
              {summary.skipped
                ? strings.taskStatusSkipped
                : summary.isSuccessful
                  ? strings.taskStatusSolved
                  : strings.taskStatusNotSolved}{' '}
              · {strings.attemptsLabel(summary.attemptsCount)} ·{' '}
              {strings.hintsLabel(summary.hintsUsed)} · {summary.timeTakenSec}s
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
