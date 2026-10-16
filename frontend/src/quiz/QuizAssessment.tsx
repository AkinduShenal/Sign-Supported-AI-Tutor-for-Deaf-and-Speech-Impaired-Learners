import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { showSprinkles } from '../components/sprinkleEvent'
import { BodmasReference } from './BodmasReference'
import {
  analyzeQuizSession,
  getPreQuizQuestions,
} from './api'
import { ConfidenceSelector } from './ConfidenceSelector'
import { QuizAnswerFeedback } from './QuizAnswerFeedback'
import { QuizProgress } from './QuizProgress'
import { QuizDiagnosticResult } from './QuizDiagnosticResult'
import { QuizLevelTransition } from './QuizLevelTransition'
import { QuizQuestionCard } from './QuizQuestionCard'
import { QuizResultPlaceholder } from './QuizResultPlaceholder'
import type { ConfidenceLevel, QuizDiagnosticResult as DiagnosticResult, QuizLanguage, QuizQuestion, QuizSession } from './types'
import { quizAttemptState, type PendingQuizWrites } from './pendingQuizWrites'
import { elapsedQuestionSeconds, QUIZ_LENGTH, transitionAfterAnswers, validatePreQuestionBank } from './workflow'
import './quiz.css'

type QuizPhase = 'loading' | 'load-error' | 'ready' | 'starting' | 'active' | 'saving' | 'feedback' | 'transition' | 'finalizing' | 'analyzing' | 'complete' | 'recovery'

export function QuizExperience({ studentCode, store }: { studentCode: string; store: PendingQuizWrites }) {
  const [phase, setPhase] = useState<QuizPhase>('loading')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [session, setSession] = useState<QuizSession | null>(null)
  const [diagnostic, setDiagnostic] = useState<DiagnosticResult | null>(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [language, setLanguage] = useState<QuizLanguage>('bilingual')
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null)
  const [confidence, setConfidence] = useState<ConfidenceLevel | null>(null)
  const [error, setError] = useState<string | null>(null)
  const questionStartedAt = useRef(0)
  const busy = useRef(false)
  const finishing = useRef(false)
  const [completionBusy, setCompletionBusy] = useState(false)

  async function loadResult(sessionId: string, celebrate = false) {
    setPhase('analyzing')
    setError(null)
    try {
      const result = await analyzeQuizSession(sessionId)
      setDiagnostic(result)
      if (celebrate) showSprinkles('win', sessionId)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Your result could not be loaded. Please try again.')
    } finally {
      setPhase('complete')
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    getPreQuizQuestions(controller.signal)
      .then(validatePreQuestionBank)
      .then(bank => {
        if (controller.signal.aborted) return
        setQuestions(bank)
        const open = store.openSessions().find(row => row.request.student_id === studentCode)
        if (!open) { setPhase('ready'); return }
        const id = `QUIZ-${open.request.client_session_id}`
        if (open.question_ids.join('|') !== bank.map(question => question.id).join('|')) {
          setError('The question bank changed. Recover saved evidence and end this incomplete collection before starting a new Quiz.')
          setPhase('recovery'); return
        }
        void store.flush(id).then(saved => {
          if (controller.signal.aborted) return
          const row = store.session(id)
          if (!row.session) {
            setError(row.error || 'Quiz evidence is pending. Use Retry / Recover Quiz evidence.')
            setPhase('recovery'); return
          }
          setSession(row.session)
          setLanguage(row.request.display_language)
          const lastWrite = row.responses.at(-1)
          if (lastWrite?.saved && lastWrite.feedback_viewed === false && typeof lastWrite.is_correct === 'boolean') {
            const attempt = quizAttemptState(lastWrite)
            if (!attempt) {
              setError(row.error || 'Quiz answer feedback is pending. Use Retry / Recover Quiz evidence.')
              setPhase('recovery'); return
            }
            setQuestionIndex(row.responses.length - 1)
            setSelectedOptionId(attempt.selectedOptionId)
            setConfidence(lastWrite.body.confidence_level)
            setPhase('feedback')
            if (attempt.correct) showSprinkles('answer')
            return
          }
          if (!saved) {
            setError(row.error || 'Quiz evidence is pending. Use Retry / Recover Quiz evidence.')
            setPhase('recovery'); return
          }
          if (row.completed) { setQuestionIndex(QUIZ_LENGTH); void loadResult(id); return }
          if (row.responses.length === QUIZ_LENGTH) {
            setError('All answers are queued. Confirm completion with Retry / Recover Quiz evidence.')
            setPhase('recovery'); return
          }
          setQuestionIndex(row.responses.length)
          setPhase(transitionAfterAnswers(row.responses.length) ? 'transition' : 'active')
        })
      })
      .catch(cause => {
        if (controller.signal.aborted) return
        setError(cause instanceof Error ? cause.message : 'Questions could not be loaded.')
        setPhase('load-error')
      })
    return () => controller.abort()
  }, [studentCode, store])

  useEffect(() => {
    if (session && phase === 'active' && questionIndex < QUIZ_LENGTH) questionStartedAt.current = performance.now()
  }, [session, questionIndex, phase])

  async function startQuiz() {
    if (busy.current || questions.length !== QUIZ_LENGTH) return
    busy.current = true
    setError(null)
    setPhase('starting')
    try {
      const id = store.start({
        student_id: studentCode, concept_id: 'linear_equations', assessment_phase: 'pre_tutor',
        display_language: language, learning_cycle_id: crypto.randomUUID(), client_session_id: crypto.randomUUID(),
      }, questions.map(question => question.id))
      if (!await store.flush(id)) throw new Error(store.session(id).error || 'Quiz session is pending. Use Retry / Recover Quiz evidence.')
      const created = store.session(id).session
      if (!created) throw new Error('Quiz session was not confirmed by the backend.')
      setSession(created)
      setDiagnostic(null)
      setQuestionIndex(0)
      setSelectedOptionId(null)
      setConfidence(null)
      setPhase('active')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The session could not be started.')
      setPhase(store.openSessions().length ? 'recovery' : 'ready')
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
    let completed = false
    try {
      if (!await store.flush(sessionId) || !store.session(sessionId).completed) {
        throw new Error(store.session(sessionId).error || 'Quiz completion is pending.')
      }
      completed = true
    } catch {
      try {
        const saved = store.session(sessionId)
        if (saved.completed) {
          completed = true
        }
      } catch { /* Keep the last answer locked until completion is confirmed. */ }
      if (!completed) {
        setError(store.session(sessionId).error || 'Quiz completion is pending. Use Retry / Recover Quiz evidence.')
        setPhase('recovery')
      }
    } finally {
      finishing.current = false
      setCompletionBusy(false)
    }
    if (completed) await loadResult(sessionId, true)
  }

  function showSavedFeedback(sessionId: string) {
    const write = store.session(sessionId).responses[questionIndex]
    const attempt = quizAttemptState(write)
    if (!attempt) {
      throw new Error('The saved answer feedback is not available. Recover Quiz evidence before continuing.')
    }
    setSelectedOptionId(attempt.selectedOptionId)
    setConfidence(write.body.confidence_level)
    setPhase('feedback')
    if (attempt.correct) showSprinkles('answer')
  }

  async function continueAfterFeedback() {
    if (phase !== 'feedback' || !session) return
    try {
      const attempt = quizAttemptState(store.session(session.quiz_session_id).responses[questionIndex])
      if (attempt?.canRetry) {
        setError(null)
        setSelectedOptionId(null)
        setPhase('active')
        return
      }
      store.acknowledgeFeedback(session.quiz_session_id, questionIndex)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Feedback could not be confirmed.')
      return
    }
    setError(null)
    setSelectedOptionId(null)
    setConfidence(null)
    if (questionIndex + 1 === QUIZ_LENGTH) {
      setQuestionIndex(QUIZ_LENGTH)
      await finishSession(session.quiz_session_id)
    } else {
      setQuestionIndex(questionIndex + 1)
      setPhase(transitionAfterAnswers(questionIndex + 1) ? 'transition' : 'active')
    }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current || phase !== 'active' || !session) return
    const sessionId = session.quiz_session_id
    const question = questions[questionIndex]
    const previousWrite = store.session(sessionId).responses[questionIndex]
    const retrying = !!previousWrite?.saved && previousWrite.is_correct === false && previousWrite.feedback_viewed === false
    if (!selectedOptionId || (!retrying && !confidence)) {
      setError('Select an answer and a confidence level before continuing.')
      return
    }
    if (retrying) {
      try {
        const attempt = store.practiceAnswer(sessionId, questionIndex, selectedOptionId, question.options.map(option => option.id))
        setError(null)
        setPhase('feedback')
        if (attempt.correct) showSprinkles('answer')
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'The practice attempt could not be recorded.')
      }
      return
    }
    busy.current = true
    setPhase('saving')
    setError(null)
    try {
      store.answer(sessionId, {
        question_id: question.id,
        selected_option_id: selectedOptionId,
        response_time_sec: elapsedQuestionSeconds(questionStartedAt.current, performance.now()),
        confidence_level: confidence!,
        question_order: questionIndex + 1,
        client_action_at: new Date().toISOString(),
      })
      const flushed = await store.flush(sessionId)
      if (!store.session(sessionId).responses[questionIndex]?.saved) {
        throw new Error(store.session(sessionId).error || 'Quiz answer is pending. Use Retry / Recover Quiz evidence.')
      }
      if (!flushed) setError(store.session(sessionId).error || 'Quiz completion is pending. Continue to retry.')
      showSavedFeedback(sessionId)
    } catch (cause) {
      // The queue preserves the exact answer across a lost response.
      try {
        const saved = store.session(sessionId)
        if (saved.responses[questionIndex]?.saved && typeof saved.responses[questionIndex].is_correct === 'boolean') {
          showSavedFeedback(sessionId)
          return
        }
      } catch { /* Show the current question and retain its selection. */ }
      setError(cause instanceof Error ? cause.message : 'The answer could not be saved. Please try again.')
      setPhase(store.session(sessionId).responses.length > questionIndex ? 'recovery' : 'active')
    } finally {
      busy.current = false
    }
  }

  const question = questions[questionIndex]
  const locked = phase !== 'active'
  const currentWrite = session && questionIndex < QUIZ_LENGTH
    ? store.session(session.quiz_session_id).responses[questionIndex] : undefined
  const retrying = phase === 'active' && !!currentWrite?.saved && currentWrite.is_correct === false && currentWrite.feedback_viewed === false
  const feedbackWrite = phase === 'feedback' && session ? currentWrite : undefined
  const feedbackAttempt = quizAttemptState(feedbackWrite)
  const feedbackCorrect = feedbackAttempt?.correct
  const feedbackCorrectOption = feedbackAttempt && !feedbackAttempt.correct && !feedbackAttempt.canRetry
    ? feedbackWrite?.correct_option ?? null : null
  const transition = transitionAfterAnswers(questionIndex)

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

      {(phase === 'active' || phase === 'saving' || phase === 'feedback') && <BodmasReference language={language} />}

      {phase === 'loading' && <section className="quiz-panel" role="status">{language === 'si' ? 'ප්‍රශ්න පූරණය වෙමින්…' : 'Loading assessment questions…'}</section>}
      {phase === 'load-error' && <section className="quiz-panel" role="alert"><p>{error}</p><button type="button" onClick={() => window.location.reload()}>{language === 'si' ? 'ප්‍රශ්න නැවත පූරණය කරන්න' : 'Reload questions'}</button></section>}
      {phase === 'recovery' && <section className="quiz-panel" role="alert">
        <h2>Quiz evidence needs recovery</h2>
        <p>{error || 'Use Retry / Recover Quiz evidence above. Keep this browser profile and learner code.'}</p>
      </section>}
      {(phase === 'ready' || phase === 'starting') && (
        <section className="quiz-panel quiz-intro" aria-labelledby="quiz-intro-title">
          <span className="quiz-kicker">{language === 'si' ? 'ප්‍රශ්න 10 · ආරම්භක 4 · අතරමැදි 4 · උසස් 2' : '10 Questions · 4 Beginner · 4 Intermediate · 2 Advanced'}</span>
          <h2 id="quiz-intro-title" lang={language === 'si' ? 'si' : 'en'}>{language === 'si' ? 'ඔබ සූදානම්ද?' : 'Ready to begin?'}</h2>
          {language !== 'si' && <p lang="en">Choose one answer and tell us how confident you feel. You have up to three tries per question. The correct option appears after a third incorrect try. Only your first answer counts toward the score; later tries are practice.</p>}
          {language !== 'en' && <p lang="si">සෑම ප්‍රශ්නයකටම උත්සාහ තුනක් දක්වා ඇත. තුන්වන උත්සාහයත් වැරදුණොත් නිවැරදි පිළිතුර පෙන්වයි. පළමු පිළිතුර පමණක් ලකුණු සඳහා ගණන් කෙරේ. පසුව කරන උත්සාහ පුහුණුව සඳහාය.</p>}
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

      {phase === 'transition' && transition && <QuizLevelTransition
        completedLevel={transition}
        language={language}
        onContinue={() => setPhase('active')}
      />}

      {(phase === 'active' || phase === 'saving' || phase === 'feedback') && question && (
        <section className="quiz-panel" aria-labelledby="quiz-question-title">
          <QuizProgress questionNumber={questionIndex + 1} language={language} difficulty={question.difficulty_level} />
          <h2 id="quiz-question-title" className="quiz-section-title">{phase === 'feedback' ? (language === 'si' ? 'ඔබේ පිළිතුර' : 'Your answer') : (language === 'si' ? 'පිළිතුර තෝරන්න' : 'Choose your answer')}</h2>
          <form onSubmit={submitAnswer}>
            <QuizQuestionCard
              question={question}
              language={language}
              selectedOptionId={selectedOptionId}
              disabled={locked}
              feedback={phase === 'feedback' ? feedbackCorrect : undefined}
              correctOptionId={phase === 'feedback' ? feedbackCorrectOption?.id : undefined}
              onSelect={setSelectedOptionId}
            />
            {!retrying && (!feedbackAttempt || feedbackAttempt.attemptNumber === 1) && <ConfidenceSelector language={language} value={confidence} disabled={locked} onChange={setConfidence} />}
            {feedbackAttempt && <QuizAnswerFeedback correct={feedbackAttempt.correct} correctOption={feedbackCorrectOption} language={language} attemptNumber={feedbackAttempt.attemptNumber} canRetry={feedbackAttempt.canRetry} />}
            {error && <p className="quiz-error" role="alert">{error}</p>}
            {phase === 'feedback' ? <button className="quiz-primary quiz-feedback-continue" type="button" onClick={() => void continueAfterFeedback()}>
              {feedbackAttempt?.canRetry ? (language === 'si' ? 'නැවත උත්සාහ කරන්න' : 'Try again') : questionIndex + 1 === QUIZ_LENGTH ? (language === 'si' ? 'ප්‍රතිඵලය බලන්න' : 'See your result') : transitionAfterAnswers(questionIndex + 1) ? (language === 'si' ? 'ඉදිරියට යන්න' : 'Continue') : (language === 'si' ? 'ඊළඟ ප්‍රශ්නය' : 'Next question')}
            </button> : <button className="quiz-primary quiz-submit" type="submit" disabled={locked || !selectedOptionId || (!retrying && !confidence)}>
              {locked ? (language === 'si' ? 'පිළිතුර සුරකිමින්…' : 'Saving answer…') : (language === 'si' ? 'පිළිතුර යවන්න' : 'Submit answer')}
            </button>}
          </form>
        </section>
      )}

      {phase === 'finalizing' && (
        <section className="quiz-panel quiz-finalizing" role="status">
          <h2>{language === 'si' ? 'ඇගයීම අවසන් කරමින්' : 'Recording assessment completion'}</h2>
          <p>{language === 'si' ? 'පිළිතුරු සුරැකීම තහවුරු කරමින් පවතී.' : 'Confirming saved answers and assessment completion.'}</p>
          {error ? <><p className="quiz-error" role="alert">{error}</p><button className="quiz-primary" type="button" disabled={completionBusy} onClick={() => session && finishSession(session.quiz_session_id)}>{language === 'si' ? 'සටහන් කිරීම අවසන් කරන්න' : 'Finish recording'}</button></> : <p>{language === 'si' ? 'කරුණාකර රැඳී සිටින්න…' : 'Please wait…'}</p>}
        </section>
      )}
      {phase === 'analyzing' && <section className="quiz-panel" role="status">{language === 'si' ? 'ඔබේ ප්‍රතිඵලය සකස් වෙමින් පවතී…' : 'Preparing your learning summary…'}</section>}
      {phase === 'complete' && (diagnostic ? <QuizDiagnosticResult result={diagnostic} language={language} /> : <>
        <QuizResultPlaceholder language={language} />
        <section className="quiz-panel quiz-result-retry">
          <p className="quiz-error" role="alert">{error || 'Your learning summary is not available yet.'}</p>
          <button className="quiz-primary" type="button" onClick={() => session && loadResult(session.quiz_session_id, true)}>{language === 'si' ? 'ප්‍රතිඵලය නැවත පූරණය කරන්න' : 'Load learning summary'}</button>
        </section>
      </>)}
    </main>
  )
}
