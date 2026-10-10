import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { getOrCreateStudentId } from '../game/identity'
import {
  completeQuizSession,
  createPreQuizSession,
  getPreQuizQuestions,
  getQuizSession,
  submitQuizAnswer,
} from './api'
import { ConfidenceSelector } from './ConfidenceSelector'
import { QuizProgress } from './QuizProgress'
import { QuizQuestionCard } from './QuizQuestionCard'
import { QuizResultPlaceholder } from './QuizResultPlaceholder'
import type { ConfidenceLevel, QuizLanguage, QuizQuestion, QuizSession } from './types'
import { elapsedQuestionSeconds, QUIZ_LENGTH, validatePreQuestionBank } from './workflow'
import './quiz.css'

type QuizPhase = 'loading' | 'load-error' | 'ready' | 'starting' | 'active' | 'saving' | 'finalizing' | 'complete'

export function QuizAssessment() {
  const [phase, setPhase] = useState<QuizPhase>('loading')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [session, setSession] = useState<QuizSession | null>(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [language, setLanguage] = useState<QuizLanguage>('bilingual')
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null)
  const [confidence, setConfidence] = useState<ConfidenceLevel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const questionStartedAt = useRef(0)
  const busy = useRef(false)
  const finishing = useRef(false)
  const [completionBusy, setCompletionBusy] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    getPreQuizQuestions(controller.signal)
      .then(validatePreQuestionBank)
      .then(bank => {
        if (controller.signal.aborted) return
        setQuestions(bank)
        setPhase('ready')
      })
      .catch(cause => {
        if (controller.signal.aborted) return
        setError(cause instanceof Error ? cause.message : 'Questions could not be loaded.')
        setPhase('load-error')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (session && questionIndex < QUIZ_LENGTH) questionStartedAt.current = performance.now()
  }, [session, questionIndex])

  async function startQuiz() {
    if (busy.current || questions.length !== QUIZ_LENGTH) return
    busy.current = true
    setError(null)
    setPhase('starting')
    try {
      const created = await createPreQuizSession(getOrCreateStudentId())
      setSession(created)
      setQuestionIndex(0)
      setSelectedOptionId(null)
      setConfidence(null)
      setPhase('active')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The session could not be started.')
      setPhase('ready')
    } finally {
      busy.current = false
    }
  }

  async function finishSession(sessionId: string) {
    if (finishing.current) return
    finishing.current = true
    setCompletionBusy(true)
    setPhase('finalizing')
    setError(null)
    try {
      await completeQuizSession(sessionId)
      setPhase('complete')
    } catch {
      try {
        const saved = await getQuizSession(sessionId)
        if (saved.status === 'completed') {
          setPhase('complete')
          return
        }
      } catch { /* Keep the last answer locked until completion is confirmed. */ }
      setError('All ten answers are saved. Please use “Finish recording” to confirm completion.')
    } finally {
      finishing.current = false
      setCompletionBusy(false)
    }
  }

  async function moveAfterSave(sessionId: string) {
    setError(null)
    setSelectedOptionId(null)
    setConfidence(null)
    if (questionIndex + 1 === QUIZ_LENGTH) {
      setQuestionIndex(QUIZ_LENGTH)
      await finishSession(sessionId)
    } else {
      setQuestionIndex(questionIndex + 1)
      setPhase('active')
    }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current || phase !== 'active' || !session) return
    if (!selectedOptionId || !confidence) {
      setError('Select an answer and a confidence level before continuing.')
      return
    }
    busy.current = true
    setPhase('saving')
    setError(null)
    const sessionId = session.quiz_session_id
    const question = questions[questionIndex]
    try {
      await submitQuizAnswer(sessionId, {
        question_id: question.id,
        selected_option_id: selectedOptionId,
        response_time_sec: elapsedQuestionSeconds(questionStartedAt.current, performance.now()),
        confidence_level: confidence,
        question_order: questionIndex + 1,
      })
      await moveAfterSave(sessionId)
    } catch (cause) {
      // A lost response can follow a successful save. Check the server before offering the same question again.
      try {
        const saved = await getQuizSession(sessionId)
        if (saved.responses_saved >= questionIndex + 1) {
          if (saved.status === 'completed' && questionIndex + 1 === QUIZ_LENGTH) {
            setPhase('complete')
          } else {
            await moveAfterSave(sessionId)
          }
          return
        }
      } catch { /* Show the current question and retain its selection. */ }
      setError(cause instanceof Error ? cause.message : 'The answer could not be saved. Please try again.')
      setPhase('active')
    } finally {
      busy.current = false
    }
  }

  const question = questions[questionIndex]
  const locked = phase === 'saving'

  return (
    <main className="quiz-page">
      <header className="quiz-header">
        <div>
          <span className="quiz-eyebrow">{language === 'si' ? '10 ශ්‍රේණිය ගණිතය · රේඛීය සමීකරණ' : 'Grade 10 Mathematics · Linear Equations'}</span>
          <h1 lang={language === 'si' ? 'si' : 'en'}>{language === 'si' ? 'ප්‍රශ්න ඇගයීම' : 'Quiz Assessment'}</h1>
          <p>{language !== 'si' && 'Pre-tutor diagnostic assessment'}{language === 'bilingual' && ' · '}{language !== 'en' && <span lang="si">පෙර ඇගයීම</span>}</p>
        </div>
        <div className="quiz-language" role="group" aria-label="Display language">
          {([
            ['en', 'English'], ['si', 'සිංහල'], ['bilingual', 'Both'],
          ] as const).map(([value, label]) => (
            <button type="button" key={value} aria-pressed={language === value} onClick={() => setLanguage(value)}>
              {label}
            </button>
          ))}
        </div>
      </header>

      {phase === 'loading' && <section className="quiz-panel" role="status">{language === 'si' ? 'ප්‍රශ්න පූරණය වෙමින්…' : 'Loading assessment questions…'}</section>}
      {phase === 'load-error' && <section className="quiz-panel" role="alert"><p>{error}</p><button type="button" onClick={() => window.location.reload()}>{language === 'si' ? 'ප්‍රශ්න නැවත පූරණය කරන්න' : 'Reload questions'}</button></section>}
      {(phase === 'ready' || phase === 'starting') && (
        <section className="quiz-panel quiz-intro" aria-labelledby="quiz-intro-title">
          <span className="quiz-kicker">{language === 'si' ? 'ප්‍රශ්න 10' : '10 questions · 4 easy · 4 medium · 2 hard'}</span>
          <h2 id="quiz-intro-title" lang={language === 'si' ? 'si' : 'en'}>{language === 'si' ? 'ඔබ සූදානම්ද?' : 'Ready to begin?'}</h2>
          {language !== 'si' && <p lang="en">Choose one answer and tell us how confident you feel for each question. Your answers are recorded once.</p>}
          {language !== 'en' && <p lang="si">සෑම ප්‍රශ්නයකටම එක් පිළිතුරක් සහ ඔබගේ විශ්වාස මට්ටම තෝරන්න.</p>}
          <p className="quiz-review-note">
            {language !== 'si' && <span lang="en">Development prototype questions · Teacher and Sinhala wording review pending</span>}
            {language === 'bilingual' && <br />}
            {language !== 'en' && <span lang="si">මෙම ආදර්ශ ප්‍රශ්න සහ සිංහල වචන ගුරු සමාලෝචනය සඳහා ඇත.</span>}
          </p>
          {error && <p className="quiz-error" role="alert">{error}</p>}
          <button className="quiz-primary" type="button" disabled={phase === 'starting'} onClick={startQuiz}>
            {phase === 'starting' ? (language === 'si' ? 'ආරම්භ වෙමින්…' : 'Starting…') : (language === 'si' ? 'ඇගයීම ආරම්භ කරන්න' : 'Start assessment')}
          </button>
        </section>
      )}

      {(phase === 'active' || phase === 'saving') && question && (
        <section className="quiz-panel" aria-labelledby="quiz-question-title">
          <QuizProgress questionNumber={questionIndex + 1} language={language} />
          <h2 id="quiz-question-title" className="quiz-section-title">{language === 'si' ? 'පිළිතුර තෝරන්න' : 'Choose your answer'}</h2>
          <form onSubmit={submitAnswer}>
            <QuizQuestionCard
              question={question}
              language={language}
              selectedOptionId={selectedOptionId}
              disabled={locked}
              onSelect={setSelectedOptionId}
            />
            <ConfidenceSelector language={language} value={confidence} disabled={locked} onChange={setConfidence} />
            {error && <p className="quiz-error" role="alert">{error}</p>}
            <button className="quiz-primary quiz-submit" type="submit" disabled={locked || !selectedOptionId || !confidence}>
              {locked ? (language === 'si' ? 'පිළිතුර සුරකිමින්…' : 'Saving answer…') : questionIndex + 1 === QUIZ_LENGTH ? (language === 'si' ? 'පිළිතුර යවා අවසන් කරන්න' : 'Submit and finish') : (language === 'si' ? 'සුරකින්න සහ ඉදිරියට යන්න' : 'Save and continue')}
            </button>
          </form>
        </section>
      )}

      {phase === 'finalizing' && (
        <section className="quiz-panel quiz-finalizing" role="status">
          <h2>{language === 'si' ? 'ඇගයීම අවසන් කරමින්' : 'Recording assessment completion'}</h2>
          <p>{language === 'si' ? 'පිළිතුරු දහයම සුරැකී ඇත.' : 'All ten answers have been saved.'}</p>
          {error ? <><p className="quiz-error" role="alert">{error}</p><button className="quiz-primary" type="button" disabled={completionBusy} onClick={() => session && finishSession(session.quiz_session_id)}>{language === 'si' ? 'සටහන් කිරීම අවසන් කරන්න' : 'Finish recording'}</button></> : <p>{language === 'si' ? 'කරුණාකර රැඳී සිටින්න…' : 'Please wait…'}</p>}
        </section>
      )}
      {phase === 'complete' && <QuizResultPlaceholder language={language} />}
    </main>
  )
}
