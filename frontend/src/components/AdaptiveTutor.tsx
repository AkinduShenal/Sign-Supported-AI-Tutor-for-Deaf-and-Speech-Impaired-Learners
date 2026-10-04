import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { checkPractice, getAdaptiveLesson, getGrade10Preview } from '../api/tutor'
import type { AdaptiveLesson, LearningLevel } from '../types/tutor'
import { AvatarSignPlayer } from './AvatarSignPlayer'
import './TutorWorkspace.css'

const LEVELS: LearningLevel[] = ['foundation', 'one_step', 'two_step', 'extended']
const label = (value: string) => value.replaceAll('_', ' ')
type Interaction = { at: string; type: string; item?: string; correct?: boolean; hints?: number; elapsed_ms?: number; answer?: string }

/** Read-only diagnostic preview. No automatic writes to the shared student DB. */
export function AdaptiveTutor() {
  const [level, setLevel] = useState<LearningLevel>('foundation')
  const [payload, setPayload] = useState<unknown>()
  const [lesson, setLesson] = useState<AdaptiveLesson>()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)
  const [session, setSession] = useState(0)
  const [requestMs, setRequestMs] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    const requestStarted = performance.now()
    const request = payload === undefined ? getGrade10Preview(level, controller.signal) : getAdaptiveLesson(payload, controller.signal)
    request.then((data) => {
      if (controller.signal.aborted) return
      setLesson(data)
      setRequestMs(Math.round(performance.now() - requestStarted))
      setSession(value => value + 1)
    }).catch((e: unknown) => {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load lesson.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [level, payload, retry])

  async function importDiagnostics(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > 100_000) { setError('Choose a diagnostic JSON file smaller than 100 KB.'); return }
    try {
      const data: unknown = JSON.parse(await file.text())
      if (!data || typeof data !== 'object' || !('quiz' in data) || !('game' in data) || !('learner' in data)) {
        throw new Error('Expected a /tutor/strategy JSON payload with quiz, game and learner fields.')
      }
      setPayload(data)
    } catch (e) { setError(e instanceof Error ? e.message : 'Invalid diagnostic file.') }
  }

  return <main className="lesson-page student-workspace">
    <a className="skip-lesson" href="#lesson-content">Skip to lesson</a>
    <nav className="workspace-bar" aria-label="Learning space">
      <span className="workspace-brand"><span className="brand-mark" aria-hidden="true">s<span>+</span></span> Sign & learn</span>
      <span className="course-label">Mathematics <span aria-hidden="true">/</span> Grade 10</span>
      <span className="workspace-tag">Your learning space</span>
    </nav>
    <header className="lesson-header">
      <div className="header-copy"><span className="eyebrow">A little practice. A little more confidence.</span><h1>Find your balance.</h1><p>Explore linear equations, one clear step at a time.</p></div>
      <div className="header-equation" aria-hidden="true"><span>x + 3</span><b>=</b><span>7</span><small>Small steps. Equal sides.</small></div>
    </header>
    <details className="lesson-card tutor-setup">
      <summary>Lesson settings <span className="summary-hint">Choose a level or import Quiz + Game results</span></summary>
      <p>Import the Quiz + Game <code>/tutor/strategy</code> JSON payload to select support. Use student codes, not names. Importing plans a lesson; it does not save records to Supabase.</p>
      <label>Diagnostic JSON <input type="file" accept=".json,application/json" onChange={importDiagnostics} /></label>
      <div className="lesson-actions">{LEVELS.map(item => <button type="button" className="secondary-button" key={item}
        aria-pressed={payload === undefined && item === level}
        onClick={() => { setPayload(undefined); setLevel(item) }}>Preview: {label(item)}</button>)}</div>
      <p className="settings-note">Preview levels are manually chosen, not ML predictions. Starting a new plan clears current browser-session practice evidence; export it first.</p>
    </details>
    {loading ? <p role="status">Preparing your lesson…</p> : error ? <div className="lesson-card" role="alert"><h2>Lesson unavailable</h2><p>{error}</p><button className="primary-button" onClick={() => setRetry(n => n + 1)}>Try again</button></div> : lesson &&
      <LearningSession key={session} lesson={lesson} requestMs={requestMs} onNextTopic={() => {
        setPayload(undefined)
        setLevel(LEVELS[Math.min(LEVELS.indexOf(lesson.plan.level) + 1, LEVELS.length - 1)])
      }} />}
  </main>
}

function LearningSession({ lesson, requestMs, onNextTopic }: { lesson: AdaptiveLesson; requestMs: number; onNextTopic: () => void }) {
  const [exampleIndex, setExampleIndex] = useState(0)
  const [stepIndex, setStepIndex] = useState(0)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [hintCounts, setHintCounts] = useState<Record<string, number>>({})
  const [attempts, setAttempts] = useState<Record<string, { count: number; independent: boolean }>>({})
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<{ correct: boolean; feedback: string }>()
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState('')
  const [allowPrototype, setAllowPrototype] = useState(false)
  const [showAvatar, setShowAvatar] = useState(lesson.plan.sign_support_required)
  const [focusHint, setFocusHint] = useState(false)
  const [events, setEvents] = useState<Interaction[]>([])
  const sessionId = useRef(crypto.randomUUID())
  const started = useRef(Date.now())
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const example = lesson.worked_examples[exampleIndex]
  const steps = useMemo(() => [{ instruction: lesson.simple_explanation.text, expression: example.problem, sign_actions: lesson.simple_explanation.sign_actions }, ...example.steps], [example, lesson])
  const step = steps[stepIndex]
  const question = lesson.practice_questions[questionIndex]
  const hintCount = hintCounts[question.question_id] ?? 0
  const hint = question.progressive_hints[Math.max(0, hintCount - 1)]
  const independent = Object.values(attempts).filter(attempt => attempt.independent).length
  const validated = useMemo(() => lesson.sign_glossary.filter(sign => sign.validation_status === 'validated').map(sign => sign.sign_id), [lesson])
  const prototypes = useMemo(() => lesson.sign_glossary.filter(sign => sign.prototype_ready).map(sign => sign.sign_id), [lesson])
  const strategy = lesson.plan.primary_strategy
  const challengeFirst = strategy === 'advanced_challenge' || strategy === 'progressive_hints'

  function record(type: string, detail: Omit<Interaction, 'at' | 'type'> = {}) {
    setEvents(current => [...current, { at: new Date().toISOString(), type, ...detail }].slice(-1000))
  }

  function navigate(index: number) {
    setStepIndex(index)
    setFocusHint(false)
    record('lesson_step', { item: `${exampleIndex}:${index}` })
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (checking || !answer.trim()) return
    setChecking(true)
    setCheckError('')
    try {
      const result = await checkPractice(question.question_id, answer)
      if (!mounted.current) return
      setFeedback(result)
      const prior = attempts[question.question_id]
      setAttempts(current => ({ ...current, [question.question_id]: { count: (prior?.count ?? 0) + 1, independent: prior?.independent ?? (result.correct && hintCount === 0) } }))
      const numericAnswer = answer.replaceAll(' ', '').replaceAll('−', '-')
      record('practice_answer', { item: question.question_id, correct: result.correct, hints: hintCount, elapsed_ms: Date.now() - started.current,
        ...(/^(x=)?[+\-\d./]+$/i.test(numericAnswer) ? { answer: numericAnswer } : {}) })
    } catch (e) {
      if (mounted.current) setCheckError(e instanceof Error ? e.message : 'Answer could not be checked. Try again.')
    } finally { if (mounted.current) setChecking(false) }
  }

  function exportEvidence() {
    const data = { schema_version: 1, session_id: sessionId.current, scope: 'local_preview_not_reassessment',
      plan: lesson.plan, planning_request_ms: requestMs, independent_first_attempts: independent, total_questions: lesson.practice_questions.length,
      playback_policy_at_export: allowPrototype ? 'prototype_preview' : 'validated_only',
      retention: 'Most recent 1000 events in this browser session only. Includes numeric answer attempts. No student IDs, names or diagnostic payload included.', events }
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url; link.download = `tutor-session-${sessionId.current}.json`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return <>
    <section className="lesson-card plan-summary" aria-label="Teaching plan">
      <div className="plan-overview"><div className="plan-icon" aria-hidden="true">=</div><div><span className="eyebrow">{lesson.plan.source === 'preview' ? 'Preview · no diagnostic data' : 'Diagnostic-based support'}</span><h2>Linear equations <span className="level-label">{label(lesson.plan.level)}</span></h2><p>{lesson.learning_objective}</p></div></div>
      <div className="plan-tools"><div className="avatar-playback-controls">
        <label><input type="checkbox" checked={showAvatar} onChange={event => { setShowAvatar(event.target.checked); record(event.target.checked ? 'avatar_enabled' : 'text_visual_baseline') }} /> Show avatar support</label>
      </div><details className="reviewer-settings"><summary>Teaching & review settings</summary>
      <p>{label(strategy)} · {lesson.plan.misconception_support}</p>
      <details><summary>Why this lesson?</summary><p>{lesson.plan.rationale}</p><p>Strategy engine: <code>{lesson.plan.model_version}</code>. {lesson.plan.model_version.startsWith('rule-based') && 'This is a transparent baseline, not a trained ML model.'}</p><p>Content: {lesson.plan.content_version} · teacher review required.</p><p>Additional support: {lesson.plan.supporting_strategies.map(label).join(', ') || 'none'}. Preferred format: {lesson.plan.preferred_mode}. Equations remain visible for every format.</p></details>
      <div className="avatar-playback-controls">
        <label><input type="checkbox" checked={allowPrototype} onChange={event => { setAllowPrototype(event.target.checked); record(event.target.checked ? 'prototype_opt_in' : 'validated_only') }} /> Preview unvalidated gestures (reviewers only)</label>
      </div></details></div>
    </section>
    <div className="learning-route"><span><i aria-hidden="true">01</i> Learn together</span><a href="#practice"><i aria-hidden="true">02</i> Try it yourself <span aria-hidden="true">↗</span></a></div>
    <section id="lesson-content" tabIndex={-1} className={`lesson-grid ${!showAvatar ? 'text-only-grid' : ''}`}>
      <div className="learning-column">
        {challengeFirst && <div className="hint-panel"><strong>Try the practice question first</strong><p>{strategy === 'progressive_hints' ? 'Open one hint at a time when you need it. The worked example is here if you get stuck.' : 'Solve independently, then compare with the worked solution and check by substitution.'}</p></div>}
        <article className="lesson-card worked-example">
          <div className="card-heading"><div><span className="eyebrow">Worked example {exampleIndex + 1} / {lesson.worked_examples.length}</span><h2>{stepIndex === 0 ? 'Key idea' : `Step ${stepIndex}`}</h2></div><span className="step-count">{stepIndex + 1} / {steps.length}</span></div>
          <div className="step-rail" role="progressbar" aria-label="Worked example progress" aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={stepIndex + 1}>{steps.map((_, index) => <span key={index} className={index <= stepIndex ? 'reached' : ''} />)}</div>
          <label className="example-picker">Choose an example <select value={exampleIndex} onChange={event => { setExampleIndex(Number(event.target.value)); setStepIndex(0); setFocusHint(false); record('example_selected', { item: event.target.value }) }}>{lesson.worked_examples.map((item, index) => <option key={item.problem} value={index}>{item.problem}</option>)}</select></label>
          <p className="original-equation">Original equation: <strong>{example.problem}</strong></p>
          <p className="instruction" aria-live="polite">{step.instruction}</p>
          <div className="equation adaptive-equation" aria-label={step.expression}>{step.expression}</div>
          {strategy === 'conceptual_explanation' && <p className="hint-panel">Think of a balance: changing only one side would break the equality. The operation must be the same on the left and right.</p>}
          <div className="lesson-actions"><button className="secondary-button" disabled={stepIndex === 0} onClick={() => navigate(stepIndex - 1)}>Previous</button><button className="primary-button" disabled={stepIndex === steps.length - 1} onClick={() => navigate(stepIndex + 1)}>Next step</button></div>
        </article>
        <article id="practice" className="lesson-card practice-card">
          <div className="card-heading"><div><span className="eyebrow">Your turn · {questionIndex + 1} / {lesson.practice_questions.length}</span><h2>Give it a try.</h2></div><span className="practice-badge">Practice</span></div>
          <p className="practice-prompt">{question.prompt}</p>
          <button className="hint-button" disabled={checking || hintCount === question.progressive_hints.length} onClick={() => {
            setHintCounts(current => ({ ...current, [question.question_id]: hintCount + 1 })); setFocusHint(true)
            record('hint', { item: question.question_id, hints: hintCount + 1 })
          }}>Show next hint ({hintCount}/{question.progressive_hints.length})</button>
          {hintCount > 0 && <div className="hint-panel" role="status"><strong>Hint {hintCount}</strong><p>{hint.text}</p></div>}
          <form className="answer-form" onSubmit={submit}><label htmlFor="practice-answer">Value of x (a fraction or decimal is okay)</label><div className="answer-row"><input id="practice-answer" value={answer} maxLength={80} autoComplete="off" placeholder="For example: x = 7" disabled={checking || feedback?.correct} onChange={event => { setAnswer(event.target.value); setFeedback(undefined) }} /><button className="primary-button" disabled={checking || !answer.trim() || feedback?.correct}>{checking ? 'Checking…' : 'Check answer'}</button></div></form>
          {checkError && <p role="alert">{checkError}</p>}
          {feedback && <div className={`feedback ${feedback.correct ? 'correct' : 'incorrect'}`} role="status"><strong>{feedback.correct ? 'Well done!' : 'Keep trying'}</strong><p>{feedback.feedback}</p>{!feedback.correct && <button type="button" className="secondary-button" onClick={() => navigate(0)}>Review the worked example</button>}</div>}
          <div className="lesson-actions">{lesson.practice_questions.map((item, index) => <button key={item.question_id} className="secondary-button" disabled={checking || index === questionIndex} onClick={() => { setQuestionIndex(index); setAnswer(''); setFeedback(undefined); setCheckError(''); setFocusHint(false); started.current = Date.now(); record('practice_selected', { item: item.question_id }) }}>Question {index + 1}</button>)}</div>
        </article>
        <details className="lesson-card practice-evidence"><summary>Session insights <span className="summary-hint">Practice evidence & export</span></summary><p>{independent} / {lesson.practice_questions.length} correct on the first attempt without hints. Repeated tries do not increase this count.</p><p>{lesson.plan.reassessment_note}</p>
          <p>Evidence includes numeric answer attempts, hints, replay events and timing. It stays in memory until you export it. Reloading or changing the plan clears it; nothing here automatically updates mastery or Supabase.</p>
          <div className="lesson-actions"><button className="secondary-button" onClick={exportEvidence}>Export session evidence</button>{independent === lesson.practice_questions.length && lesson.plan.level !== 'extended' && <button className="primary-button" onClick={onNextTopic}>Preview the next topic</button>}</div>
        </details>
      </div>
      {showAvatar && <AvatarSignPlayer signActions={focusHint && hintCount ? hint.sign_actions : step.sign_actions} caption={focusHint && hintCount ? hint.text : step.instruction} expression={focusHint && hintCount ? question.prompt : step.expression} validatedSignIds={validated} prototypeSignIds={prototypes} allowPrototype={allowPrototype} onInteraction={record} />}
    </section>
    <footer className="workspace-footer">Take your time. You can replay, revisit, and try again.<span>Sign-supported mathematics · Grade 10</span></footer>
  </>
}
