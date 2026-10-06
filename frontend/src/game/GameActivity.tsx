import { useEffect, useState } from 'react'
import type { AssessmentPhase, BalanceTask, TaskAttemptSummary } from './types'
import { useGameEvents } from './useGameEvents'
import { useLanguage } from './i18n/useLanguage'
import { BalanceScale } from './activities/BalanceScale'
import './GameActivity.css'

interface GameActivityProps {
  conceptId: string
  phase: AssessmentPhase
  tasks: BalanceTask[]
  onGameCompleted: (summaries: TaskAttemptSummary[]) => void
}

type Feedback = { kind: 'correct' | 'incorrect'; message: string } | null

type TaskResult = { isSuccessful: boolean; skipped: boolean } | null

export function GameActivity({
  conceptId,
  phase,
  tasks,
  onGameCompleted,
}: GameActivityProps) {
  const { logEvent, getEvents } = useGameEvents()
  const { language, strings } = useLanguage()
  const [taskIndex, setTaskIndex] = useState(0)
  const [feedback, setFeedback] = useState<Feedback>(null)
  const [taskResult, setTaskResult] = useState<TaskResult>(null)
  const [wobbling, setWobbling] = useState(false)
  const [hintsShown, setHintsShown] = useState(0)
  const [attempts, setAttempts] = useState(0)
  const [wrongAttempts, setWrongAttempts] = useState(0)
  const [startedAt, setStartedAt] = useState(() => Date.now())
  const [summaries, setSummaries] = useState<TaskAttemptSummary[]>([])

  const task = tasks[taskIndex]
  const isLastTask = taskIndex === tasks.length - 1

  useEffect(() => {
    logEvent('session', 'GAME_STARTED', { conceptId, phase, taskCount: tasks.length })
    // Fires once when the activity mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    setStartedAt(Date.now())
    logEvent(task.id, 'TASK_STARTED', {})
    logEvent(task.id, 'QUESTION_SHOWN', {
      variableLabel: task.variableLabel,
      leftSign: task.leftSign,
      leftConstant: task.leftConstant,
      rightValue: task.rightValue,
    })
    // Fires whenever the visible task changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task.id])

  function recordTaskResult(
    isSuccessful: boolean,
    skipped: boolean,
    attemptsCount: number,
  ) {
    const summary: TaskAttemptSummary = {
      taskId: task.id,
      attemptsCount,
      wrongAttempts,
      hintsUsed: hintsShown,
      skipped,
      isCompleted: true,
      isSuccessful,
      timeTakenSec: Math.round((Date.now() - startedAt) / 1000),
    }
    logEvent(task.id, 'TASK_COMPLETED', { ...summary })
    setSummaries((previous) => [...previous, summary])
    setTaskResult({ isSuccessful, skipped })
  }

  function handleContinue() {
    if (isLastTask) {
      logEvent('session', 'GAME_COMPLETED', { taskCount: tasks.length })
      logEvent('session', 'SESSION_ENDED', { totalEvents: getEvents().length })
      onGameCompleted(summaries)
      return
    }

    setTaskIndex((index) => index + 1)
    setFeedback(null)
    setTaskResult(null)
    setHintsShown(0)
    setAttempts(0)
    setWrongAttempts(0)
  }

  function handleChooseOperation(choiceId: string, isCorrect: boolean) {
    if (taskResult) return

    if (feedback?.kind === 'incorrect') {
      logEvent(task.id, 'RETRY_STARTED', { attemptNumber: attempts + 1 })
    }

    const attemptNumber = attempts + 1
    setAttempts(attemptNumber)
    logEvent(task.id, 'ANSWER_SUBMITTED', { attemptNumber, choiceId })

    if (isCorrect) {
      logEvent(task.id, 'ANSWER_CORRECT', { attemptNumber })
      setFeedback({
        kind: 'correct',
        message: strings.correctFeedback(task.variableLabel, task.correctAnswer),
      })
      recordTaskResult(true, false, attemptNumber)
    } else {
      setWrongAttempts((count) => count + 1)
      logEvent(task.id, 'ANSWER_INCORRECT', { attemptNumber, choiceId })
      setFeedback({ kind: 'incorrect', message: strings.incorrectFeedback })
      setWobbling(true)
      setTimeout(() => setWobbling(false), 500)
    }
  }

  function handleHint() {
    if (hintsShown >= task.hints.length) return
    logEvent(task.id, 'HINT_REQUESTED', { hintNumber: hintsShown + 1 })
    setHintsShown((count) => count + 1)
  }

  function handleSkip() {
    logEvent(task.id, 'STEP_SKIPPED', { attemptsSoFar: attempts })
    recordTaskResult(false, true, attempts)
  }

  return (
    <section className="game-activity" aria-labelledby="game-activity-heading">
      <p className="game-progress">{strings.taskProgress(taskIndex + 1, tasks.length)}</p>
      <h1 id="game-activity-heading" className="game-prompt">
        {task.variableLabel} {task.leftSign} {task.leftConstant} = {task.rightValue}
      </h1>

      <BalanceScale
        variableLabel={task.variableLabel}
        leftSign={task.leftSign}
        leftConstant={task.leftConstant}
        rightValue={taskResult?.isSuccessful ? task.correctAnswer : task.rightValue}
        solved={Boolean(taskResult?.isSuccessful)}
        wobbling={wobbling}
      />

      {!taskResult && (
        <>
          <p className="game-choose-prompt">{strings.chooseOperationPrompt}</p>
          <div className="game-chip-grid" role="group" aria-label={strings.chooseOperationPrompt}>
            {task.operationChoices.map((choice) => (
              <button
                key={choice.id}
                type="button"
                className="game-button chip"
                onClick={() => handleChooseOperation(choice.id, choice.isCorrect)}
              >
                {choice.label[language]}
              </button>
            ))}
          </div>
        </>
      )}

      {feedback && (
        <p role="status" className={`game-feedback ${feedback.kind}`}>
          <span aria-hidden="true">{feedback.kind === 'correct' ? '✓' : '✗'}</span>{' '}
          {feedback.message}
        </p>
      )}

      {!taskResult && (
        <div className="game-actions">
          <button
            type="button"
            className="game-button"
            onClick={handleHint}
            disabled={hintsShown >= task.hints.length}
          >
            {strings.hintButton(hintsShown, task.hints.length)}
          </button>
          <button type="button" className="game-button subtle" onClick={handleSkip}>
            {strings.skipButton}
          </button>
        </div>
      )}

      {hintsShown > 0 && (
        <ul className="game-hints" aria-label="Hints shown so far">
          {task.hints.slice(0, hintsShown).map((hint) => (
            <li key={hint[language]}>
              <span aria-hidden="true">💡</span> {hint[language]}
            </li>
          ))}
        </ul>
      )}

      {taskResult && (
        <button type="button" className="game-button primary" onClick={handleContinue}>
          {isLastTask ? strings.finishButton : strings.continueButton}
        </button>
      )}
    </section>
  )
}
