import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { getTutorLesson } from '../api/tutor'
import type { LessonStep, TutorLesson } from '../types/tutor'
import { AvatarSignPlayer } from './AvatarSignPlayer'

interface LessonPageProps {
  conceptId: string
}

interface LessonStage {
  label: string
  instruction: string
  expression?: string
  signActions: string[]
}

function normaliseAnswer(answer: string) {
  return answer.toLowerCase().replaceAll(' ', '')
}

function isCorrectAnswer(answer: string, expectedAnswer: string) {
  const normalisedAnswer = normaliseAnswer(answer)
  const normalisedExpected = normaliseAnswer(expectedAnswer)
  const expectedValue = normalisedExpected.split('=').at(-1)

  return (
    normalisedAnswer === normalisedExpected || normalisedAnswer === expectedValue
  )
}

function toStage(step: LessonStep): LessonStage {
  return {
    label: `Step ${step.order}`,
    instruction: step.instruction,
    expression: step.expression,
    signActions: step.sign_actions,
  }
}

export function LessonPage({ conceptId }: LessonPageProps) {
  const [lesson, setLesson] = useState<TutorLesson | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [stageIndex, setStageIndex] = useState(0)
  const [isHintVisible, setIsHintVisible] = useState(false)
  const [answer, setAnswer] = useState('')
  const [answerIsCorrect, setAnswerIsCorrect] = useState<boolean | null>(null)

  const loadLesson = useCallback(() => {
    setReloadKey((key) => key + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    setIsLoading(true)
    setError(null)
    getTutorLesson(conceptId, controller.signal)
      .then((lessonData) => {
        setLesson(lessonData)
        setStageIndex(0)
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name === 'AbortError') {
          return
        }
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'The lesson could not be loaded.',
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [conceptId, reloadKey])

  const stages = useMemo<LessonStage[]>(() => {
    if (!lesson) return []

    const firstExample = lesson.worked_examples[0]
    return [
      {
        label: 'Key idea',
        instruction: lesson.simple_explanation.text,
        expression: firstExample?.problem,
        signActions: lesson.simple_explanation.sign_actions,
      },
      ...(firstExample?.steps.map(toStage) ?? []),
    ]
  }, [lesson])

  const currentStage = stages[stageIndex]
  const practiceQuestion = lesson?.practice_questions[0]
  const validatedSignIds = useMemo(
    () =>
      lesson?.sign_glossary
        .filter((sign) => sign.validation_status === 'validated')
        .map((sign) => sign.sign_id) ?? [],
    [lesson],
  )
  const avatarSignActions =
    isHintVisible && practiceQuestion
      ? practiceQuestion.hint.sign_actions
      : currentStage?.signActions ?? []

  function goToStage(nextIndex: number) {
    setStageIndex(nextIndex)
    setIsHintVisible(false)
  }

  function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!practiceQuestion || !answer.trim()) return

    setAnswerIsCorrect(
      isCorrectAnswer(answer, practiceQuestion.expected_answer),
    )
  }

  if (isLoading) {
    return (
      <main className="page-state" aria-live="polite">
        <div className="loading-mark" />
        <h1>Preparing your lesson</h1>
        <p>The AI tutor is loading the learning content.</p>
      </main>
    )
  }

  if (error || !lesson || !currentStage) {
    return (
      <main className="page-state error-state" role="alert">
        <span className="state-icon">!</span>
        <h1>Lesson unavailable</h1>
        <p>{error ?? 'The lesson does not contain any learning steps.'}</p>
        <button className="primary-button" type="button" onClick={loadLesson}>
          Try again
        </button>
      </main>
    )
  }

  return (
    <main className="lesson-page">
      <header className="lesson-header">
        <div className="brand-mark" aria-hidden="true">
          S
        </div>
        <div className="header-copy">
          <span className="eyebrow">Sign-Supported AI Tutor</span>
          <h1>{lesson.title}</h1>
          <p>{lesson.learning_objective}</p>
        </div>
        <div className="lesson-progress" aria-label="Lesson progress">
          <strong>
            {stageIndex + 1}/{stages.length}
          </strong>
          <span>lesson stages</span>
        </div>
      </header>

      <section className="lesson-grid">
        <div className="learning-column">
          <article className="lesson-card step-card">
            <div className="card-heading">
              <div>
                <span className="eyebrow">Worked example</span>
                <h2>{currentStage.label}</h2>
              </div>
              <span className="step-count">
                {stageIndex + 1} of {stages.length}
              </span>
            </div>

            <div className="progress-track" aria-hidden="true">
              <span
                style={{ width: `${((stageIndex + 1) / stages.length) * 100}%` }}
              />
            </div>

            <p className="instruction">{currentStage.instruction}</p>
            {currentStage.expression && (
              <div className="equation" aria-label={currentStage.expression}>
                {currentStage.expression}
              </div>
            )}

            <div className="lesson-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={stageIndex === 0}
                onClick={() => goToStage(stageIndex - 1)}
              >
                Previous
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={stageIndex === stages.length - 1}
                onClick={() => goToStage(stageIndex + 1)}
              >
                Next step
              </button>
            </div>
          </article>

          {practiceQuestion && (
            <article className="lesson-card practice-card">
              <div className="card-heading">
                <div>
                  <span className="eyebrow">Your turn</span>
                  <h2>Practice question</h2>
                </div>
                <span className="practice-badge">Practice</span>
              </div>

              <p className="practice-prompt">{practiceQuestion.prompt}</p>

              <button
                className="hint-button"
                type="button"
                aria-expanded={isHintVisible}
                onClick={() => setIsHintVisible((visible) => !visible)}
              >
                {isHintVisible ? 'Hide hint' : 'Show hint'}
              </button>

              {isHintVisible && (
                <div className="hint-panel">
                  <strong>Hint</strong>
                  <p>{practiceQuestion.hint.text}</p>
                </div>
              )}

              <form className="answer-form" onSubmit={submitAnswer}>
                <label htmlFor="practice-answer">Your answer</label>
                <div className="answer-row">
                  <input
                    id="practice-answer"
                    value={answer}
                    placeholder="Example: x = 7"
                    autoComplete="off"
                    onChange={(event) => {
                      setAnswer(event.target.value)
                      setAnswerIsCorrect(null)
                    }}
                  />
                  <button
                    className="primary-button"
                    type="submit"
                    disabled={!answer.trim()}
                  >
                    Check answer
                  </button>
                </div>
              </form>

              {answerIsCorrect !== null && (
                <div
                  className={`feedback ${answerIsCorrect ? 'correct' : 'incorrect'}`}
                  role="status"
                >
                  <strong>{answerIsCorrect ? 'Well done!' : 'Keep trying'}</strong>
                  <p>
                    {answerIsCorrect
                      ? practiceQuestion.feedback.correct
                      : practiceQuestion.feedback.incorrect}
                  </p>
                </div>
              )}
            </article>
          )}
        </div>

        <AvatarSignPlayer
          signActions={avatarSignActions}
          validatedSignIds={validatedSignIds}
        />
      </section>
    </main>
  )
}
