import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { showSprinkles } from './sprinkleEvent'
import { checkPractice, getAdaptiveLesson, getGrade10Preview } from '../api/tutor'
import type { AdaptiveLesson, LearningLevel, TeachingStrategy, TutorQuestionAnswer } from '../types/tutor'
import { AvatarSignPlayer } from './AvatarSignPlayer'
import { SinhalaText } from './SinhalaText'
import { TEACHING_APPROACHES } from './teachingApproaches'
import { TutorQuestion } from './TutorQuestion'
import './TutorWorkspace.css'

const LEVELS: LearningLevel[] = ['foundation', 'one_step', 'two_step', 'extended']
const label = (value: string) => value.replaceAll('_', ' ')
type Interaction = { at: string; type: string; item?: string; correct?: boolean; hints?: number; elapsed_ms?: number; answer?: string; solution_viewed?: boolean }

/** Read-only diagnostic preview. No automatic writes to the shared student DB. */
export function AdaptiveTutor() {
  const [level, setLevel] = useState<LearningLevel>('foundation')
  const [strategy, setStrategy] = useState<TeachingStrategy | null>('step_by_step')
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
    const request = payload !== undefined && strategy === null
      ? getAdaptiveLesson(payload, controller.signal)
      : getGrade10Preview(level, controller.signal, strategy ?? 'step_by_step')
    request.then((data) => {
      if (controller.signal.aborted) return
      setLesson(data)
      setRequestMs(Math.round(performance.now() - requestStarted))
      setSession(value => value + 1)
    }).catch((e: unknown) => {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load lesson.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [level, payload, retry, strategy])

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
      setStrategy(null)
    } catch (e) { setError(e instanceof Error ? e.message : 'Invalid diagnostic file.') }
  }

  return <main className="lesson-page student-workspace">
    <a className="skip-lesson" href="#lesson-content">Skip to lesson</a>
    <nav className="workspace-bar" aria-label="Learning space">
      <span className="workspace-brand"><img className="brand-mark" src="/connected-learning-emblem.png" alt="" width="48" height="48" /> Sign & learn</span>
      <span className="course-label"><span>Mathematics</span><span>Grade 10</span></span>
    </nav>
    <header className="lesson-header">
      <div className="topic-mark" aria-hidden="true">x</div>
      <div className="header-copy">
        <span className="lesson-kicker">Today&apos;s maths mission</span>
        <h1>Linear equations</h1>
        <p className="lesson-title-si" lang="si">රේඛීය සමීකරණ</p>
      </div>
    </header>
    <section className="teaching-selector" aria-labelledby="teaching-selector-title">
      <div>
        <h2 id="teaching-selector-title">Choose a teaching approach <span lang="si">ඉගෙන ගන්නා ක්‍රමය තෝරන්න</span></h2>
        <p id="teaching-selector-note">{strategy === null ? 'Using the imported Quiz + Game recommendation.' : 'Manual preview · choose how you want the lesson explained.'}</p>
      </div>
      <label htmlFor="teaching-strategy">Teaching approach / <span lang="si">ඉගෙනීමේ ක්‍රමය</span>
        <select id="teaching-strategy" value={strategy ?? 'diagnostic'} aria-describedby="teaching-selector-note" onChange={event => {
          const selected = event.target.value
          if (selected === 'diagnostic') { setStrategy(null); return }
          setStrategy(selected as TeachingStrategy)
          setLevel(selected === 'advanced_challenge' ? 'extended' : lesson?.plan.level ?? level)
        }}>
          {payload !== undefined && <option value="diagnostic">Use Quiz + Game recommendation</option>}
          {Object.entries(TEACHING_APPROACHES).map(([value, approach]) => <option key={value} value={value}>{approach.title} — {approach.titleSi}</option>)}
        </select>
      </label>
    </section>
    {loading ? <p role="status">Preparing your lesson…</p> : error ? <div className="lesson-card" role="alert"><h2>Lesson unavailable</h2><p>{error}</p><button className="primary-button" onClick={() => setRetry(n => n + 1)}>Try again</button></div> : lesson &&
      <LearningSession key={session} lesson={lesson} requestMs={requestMs} onNextTopic={() => {
        setPayload(undefined)
        if (strategy === null) setStrategy('step_by_step')
        setLevel(LEVELS[Math.min(LEVELS.indexOf(lesson.plan.level) + 1, LEVELS.length - 1)])
      }} />}
    <details className="lesson-card tutor-setup">
      <summary>Lesson settings</summary>
      <p>Import the Quiz + Game <code>/tutor/strategy</code> JSON payload to select support. Use student codes, not names. Importing plans a lesson; it does not save records to Supabase.</p>
      <label>Diagnostic JSON <input type="file" accept=".json,application/json" onChange={importDiagnostics} /></label>
      <div className="lesson-actions">{LEVELS.map(item => <button type="button" className="secondary-button" key={item}
        aria-pressed={strategy !== null && item === level}
        onClick={() => { setPayload(undefined); if (strategy === null) setStrategy('step_by_step'); setLevel(item) }}>Preview: {label(item)}</button>)}</div>
      <p className="settings-note">Preview levels are manually chosen, not ML predictions. Starting a new plan clears current browser-session practice evidence; export it first.</p>
    </details>
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
  const [stepCheck, setStepCheck] = useState<'both' | 'one' | null>(null)
  const [solutionsShown, setSolutionsShown] = useState<Record<string, boolean>>({})
  const [solutionsViewed, setSolutionsViewed] = useState<Record<string, boolean>>({})
  const tutorHelpUsed = useRef<Record<string, boolean>>({})
  const practiceSectionRef = useRef<HTMLDetailsElement>(null)
  const [ragAvatar, setRagAvatar] = useState<{ id: string; answer: TutorQuestionAnswer }>()
  const sessionId = useRef(crypto.randomUUID())
  const started = useRef(Date.now())
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const example = lesson.worked_examples[exampleIndex]
  const steps = useMemo(() => [{ instruction: lesson.simple_explanation.text, expression: example.problem, sign_actions: lesson.simple_explanation.sign_actions, avatar_segments: lesson.simple_explanation.avatar_segments, knowledge_notes: lesson.simple_explanation.knowledge_notes }, ...example.steps], [example, lesson])
  const step = steps[stepIndex]
  const question = lesson.practice_questions[questionIndex]
  const hintCount = hintCounts[question.question_id] ?? 0
  const hint = question.progressive_hints[Math.max(0, hintCount - 1)]
  const independent = Object.values(attempts).filter(attempt => attempt.independent).length
  const validated = useMemo(() => lesson.sign_glossary.filter(sign => sign.validation_status === 'validated').map(sign => sign.sign_id), [lesson])
  const prototypes = useMemo(() => lesson.sign_glossary.filter(sign => sign.prototype_ready).map(sign => sign.sign_id), [lesson])
  const reviewAnimations = useMemo(() => lesson.sign_glossary.filter(sign => sign.animation_type === 'composite_prototype_educational_gesture').map(sign => sign.sign_id), [lesson])
  const strategy = lesson.plan.primary_strategy
  const approach = TEACHING_APPROACHES[strategy]
  const solutionShown = solutionsShown[question.question_id] ?? false
  const operationStep = /^(Subtract|Add|Divide|Multiply BOTH)/.test(step.instruction)
  const [leftSide, rightSide] = example.problem.split('=')
  const solutionSegments = useMemo(() => question.worked_solution.steps.flatMap(solutionStep =>
    solutionStep.avatar_segments?.length ? solutionStep.avatar_segments : [{ text: solutionStep.instruction, expression: solutionStep.expression, sign_actions: solutionStep.sign_actions }]
  ), [question])
  const lessonAvatarContent = focusHint
    ? solutionShown
      ? { sign_actions: solutionSegments.flatMap(segment => segment.sign_actions), instruction: question.prompt, expression: question.worked_solution.problem, avatar_segments: solutionSegments }
      : hintCount > 0
        ? { sign_actions: hint.sign_actions, instruction: hint.text, expression: question.worked_solution.problem, avatar_segments: hint.avatar_segments }
        : { sign_actions: lesson.simple_explanation.sign_actions, instruction: lesson.simple_explanation.text, expression: question.worked_solution.problem, avatar_segments: lesson.simple_explanation.avatar_segments }
    : step
  const avatarContent = ragAvatar ? {
    sign_actions: ragAvatar.answer.avatar_segments.flatMap(segment => segment.sign_actions),
    instruction: ragAvatar.answer.avatar_segments[0]?.text ?? step.instruction,
    expression: step.expression, avatar_segments: ragAvatar.answer.avatar_segments,
  } : lessonAvatarContent
  const avatarTeachingKey = ragAvatar ? `rag:${ragAvatar.id}` : `${strategy}:${focusHint ? `practice:${question.question_id}:${hintCount}:${solutionShown}` : `example:${exampleIndex}:${stepIndex}`}`

  function previewGestures(enabled: boolean) {
    setAllowPrototype(enabled)
    record(enabled ? 'prototype_opt_in' : 'validated_only')
  }

  function selectQuestion(index: number) {
    setRagAvatar(undefined)
    setQuestionIndex(index)
    setAnswer('')
    setFeedback(undefined)
    setCheckError('')
    setFocusHint(true)
    started.current = Date.now()
    record('practice_selected', { item: lesson.practice_questions[index].question_id })
  }

  function record(type: string, detail: Omit<Interaction, 'at' | 'type'> = {}) {
    setEvents(current => [...current, { at: new Date().toISOString(), type, ...detail }].slice(-1000))
  }

  function navigate(index: number) {
    setRagAvatar(undefined)
    setStepIndex(index)
    setStepCheck(null)
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
      if (result.correct) showSprinkles('answer')
      const prior = attempts[question.question_id]
      setAttempts(current => ({ ...current, [question.question_id]: { count: (prior?.count ?? 0) + 1, independent: prior?.independent ?? (result.correct && hintCount === 0 && !solutionsViewed[question.question_id] && !tutorHelpUsed.current[question.question_id]) } }))
      const numericAnswer = answer.replaceAll(' ', '').replaceAll('−', '-')
      record('practice_answer', { item: question.question_id, correct: result.correct, hints: hintCount, solution_viewed: solutionsViewed[question.question_id] ?? false, elapsed_ms: Date.now() - started.current,
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

  const workedExampleCard = <article className="lesson-card worked-example">
          <div className="card-heading"><h2>{stepIndex === 0 ? 'Key idea' : `Step ${stepIndex}`}</h2><span className="step-count">{stepIndex + 1} / {steps.length}</span></div>
          <div className="step-rail" role="progressbar" aria-label="Worked example progress" aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={stepIndex + 1}>{steps.map((_, index) => <span key={index} className={index <= stepIndex ? 'reached' : ''} />)}</div>
          <label className="example-picker"><span><span className="picker-icon" aria-hidden="true">✦</span> Choose an example</span><select value={exampleIndex} onChange={event => { setRagAvatar(undefined); setExampleIndex(Number(event.target.value)); setStepIndex(0); setStepCheck(null); setFocusHint(false); record('example_selected', { item: event.target.value }) }}>{lesson.worked_examples.map((item, index) => <option key={item.problem} value={index}>{item.problem}</option>)}</select></label>
          <p className="original-equation">Original equation: <strong>{example.problem}</strong></p>
          <div className="equation adaptive-equation" aria-label={step.expression}>{step.expression}</div>
          <div className="bilingual-instruction" aria-live="polite"><p className="instruction" lang="en">{step.instruction}</p><SinhalaText text={step.instruction} /></div>
          {!!step.avatar_segments?.length && <details key={`${exampleIndex}:${stepIndex}`} className="step-explanation" aria-label="Detailed explanation">
            <summary>{stepIndex === 0 ? 'How we will learn' : 'Why this step works'} / <span lang="si">{stepIndex === 0 ? 'ඉගෙන ගන්නා ආකාරය' : 'මේ පියවරේ හේතුව'}</span></summary>
            {step.avatar_segments.filter(segment => segment.text !== step.instruction).map((segment, index) => <div key={index}><p lang="en">{segment.text}</p>{segment.text_si ? <p lang="si" className="sinhala-text">{segment.text_si}</p> : <SinhalaText text={segment.text} />}</div>)}
          </details>}
          {strategy === 'conceptual_explanation' && rightSide !== undefined && <figure className="balance-visual">
            <div className="balance-sides"><div><small>Left / <span lang="si">වම් පස</span></small><strong>{leftSide.trim()}</strong></div><span className="balance-equals" aria-label="equals">=</span><div><small>Right / <span lang="si">දකුණු පස</span></small><strong>{rightSide.trim()}</strong></div></div>
            <figcaption><span lang="en">Same value · same operation on both sides</span><span lang="si">සමාන අගය · දෙපසටම එකම ගණිත ක්‍රියාව</span></figcaption>
          </figure>}
          {strategy === 'step_by_step' && operationStep && <fieldset className="step-check">
            <legend>Quick check / <span lang="si">කෙටි පරීක්ෂාව</span></legend>
            <p>Which sides must receive this operation?</p><p lang="si" className="sinhala-text">මේ ගණිත ක්‍රියාව සිදු කළ යුත්තේ කුමන පැතිවලටද?</p>
            <div className="lesson-actions">{(['both', 'one'] as const).map(choice => <button key={choice} type="button" className="secondary-button" aria-pressed={stepCheck === choice} onClick={() => { setStepCheck(choice); record('step_checkpoint', { item: `${exampleIndex}:${stepIndex}`, correct: choice === 'both' }) }}>{choice === 'both' ? 'Both sides / දෙපසටම' : 'Only one side / එක් පසකට පමණයි'}</button>)}</div>
            {stepCheck && <p role="status">{stepCheck === 'both' ? 'Correct. Apply the same operation to both sides. / නිවැරදියි. දෙපසටම එකම ගණිත ක්‍රියාව සිදු කරන්න.' : 'Try again. Changing only one side breaks equality. / නැවත උත්සාහ කරන්න. එක් පසක් පමණක් වෙනස් කළොත් සමානතාව නැති වෙනවා.'}</p>}
          </fieldset>}
          <div className="lesson-actions"><button className="secondary-button" disabled={stepIndex === 0} onClick={() => navigate(stepIndex - 1)}>Previous</button><button className="primary-button" disabled={stepIndex === steps.length - 1} onClick={() => navigate(stepIndex + 1)}>Next step</button></div>
          {strategy === 'worked_example_based' && <button type="button" className="secondary-button" onClick={() => {
            selectQuestion(exampleIndex % lesson.practice_questions.length)
            if (practiceSectionRef.current) practiceSectionRef.current.open = true
            document.getElementById('practice')?.scrollIntoView({ block: 'start' })
          }}>Try a similar question / සමාන ප්‍රශ්නයක් විසඳන්න</button>}
          <TutorQuestion key={`${lesson.plan.level}:${strategy}:${example.problem}:${stepIndex}`} level={lesson.plan.level} strategy={strategy} exampleProblem={example.problem} stepIndex={stepIndex}
            onHelpUsed={() => { tutorHelpUsed.current[question.question_id] = true; record('tutor_help_viewed', { item: question.question_id }) }}
            onAvatarSupport={answer => { setShowAvatar(true); setRagAvatar({ id: crypto.randomUUID(), answer }); record('tutor_avatar_support', { item: answer.sources.map(source => source.id).join(',') }) }} />
          {!!step.knowledge_notes?.length && <details className="lesson-knowledge-notes"><summary>Related lesson notes / <span lang="si">අදාළ පාඩම් සටහන්</span></summary>{step.knowledge_notes.map(source => <div key={source.id}><strong>{source.title_en}</strong><p lang="en">{source.text_en}</p><p lang="si" className="sinhala-text">{source.text_si}</p></div>)}<small>Draft content · teacher review pending.</small></details>}
        </article>

  const practiceCard = <article id="practice" className="lesson-card practice-card">
          <div className="card-heading"><h2>Question {questionIndex + 1} <span className="question-total">/ {lesson.practice_questions.length}</span></h2><span className="level-label">{label(lesson.plan.level)}</span></div>
          <div className="approach-guidance"><p lang="en">{approach.practice}</p><p lang="si" className="sinhala-text">{approach.practiceSi}</p></div>
          <div className="bilingual-question"><p className="practice-prompt" lang="en">{question.prompt}</p><SinhalaText text={question.prompt} /></div>
          <form className="answer-form" onSubmit={submit}><label htmlFor="practice-answer">Your answer</label><div className="answer-row"><input id="practice-answer" value={answer} maxLength={80} autoComplete="off" placeholder="x = …" disabled={checking || feedback?.correct} onChange={event => { setAnswer(event.target.value); setFeedback(undefined) }} /><button className="primary-button" disabled={checking || !answer.trim() || feedback?.correct}>{checking ? 'Checking…' : 'Check answer'}</button></div></form>
          {checkError && <p role="alert">{checkError}</p>}
          {feedback && <div className={`feedback ${feedback.correct ? 'correct' : 'incorrect'}`} role="status"><strong>{feedback.correct ? 'Well done!' : 'Keep trying'}</strong><p lang="en">{feedback.feedback}</p><SinhalaText text={feedback.feedback} />{!feedback.correct && <button type="button" className="secondary-button" onClick={() => navigate(0)}>Review the worked example</button>}</div>}
          <section className="question-hints" aria-label="Hints">
            <button className="hint-button" disabled={checking || hintCount === question.progressive_hints.length} onClick={() => {
              setRagAvatar(undefined)
              setHintCounts(current => ({ ...current, [question.question_id]: hintCount + 1 })); setFocusHint(true)
              record('hint', { item: question.question_id, hints: hintCount + 1 })
            }}>{hintCount === 0 ? 'Show hint' : hintCount === question.progressive_hints.length ? 'All hints shown' : 'Next hint'}</button>
            {hintCount > 0 && <div className="hint-panel" role="status"><strong>Hint {hintCount} of {question.progressive_hints.length}</strong><p lang="en">{hint.text}</p><SinhalaText text={hint.text} />
              {hint.avatar_segments?.filter(segment => segment.text !== hint.text).map((segment, index) => <div key={index}><p lang="en">{segment.text}</p>{segment.text_si && <p className="sinhala-text" lang="si">{segment.text_si}</p>}</div>)}
            </div>}
          </section>
          {(strategy !== 'progressive_hints' || hintCount === question.progressive_hints.length) && <button type="button" className="secondary-button" disabled={checking} aria-expanded={solutionShown} aria-controls="practice-solution" onClick={() => {
            setRagAvatar(undefined)
            setSolutionsShown(current => ({ ...current, [question.question_id]: !solutionShown }))
            if (!solutionShown) setSolutionsViewed(current => ({ ...current, [question.question_id]: true }))
            record(solutionShown ? 'solution_hidden' : 'solution_revealed', { item: question.question_id, hints: hintCount })
            setFocusHint(true)
          }}>{solutionShown ? 'Hide worked solution / විසඳුම සඟවන්න' : 'Show worked solution / පියවර සහිත විසඳුම බලන්න'}</button>}
          {solutionShown && <section id="practice-solution" className="practice-solution" aria-label="Worked solution for this question">
            <h3>Worked solution / <span lang="si">පියවර සහිත විසඳුම</span></h3>
            <ol>{question.worked_solution.steps.map(solutionStep => <li key={solutionStep.order}><p lang="en">{solutionStep.instruction}</p><SinhalaText text={solutionStep.instruction} /><div className="solution-equation">{solutionStep.expression}</div></li>)}</ol>
          </section>}
          <div className="lesson-actions question-navigation"><button className="secondary-button" disabled={checking || questionIndex === 0} onClick={() => selectQuestion(questionIndex - 1)}>Previous question</button><button className="secondary-button" disabled={checking || questionIndex === lesson.practice_questions.length - 1} onClick={() => selectQuestion(questionIndex + 1)}>Next question <span aria-hidden="true">→</span></button></div>
        </article>

  return <>
    <section id="lesson-content" tabIndex={-1} data-strategy={strategy} className={`lesson-grid ${!showAvatar ? 'text-only-grid' : ''}`}>
      <div className="learning-column">
        {workedExampleCard}
      </div>
      {showAvatar && <AvatarSignPlayer compact signActions={avatarContent.sign_actions} caption={avatarContent.instruction} expression={avatarContent.expression} teachingSegments={avatarContent.avatar_segments} teachingKey={avatarTeachingKey} teachingApproach={approach.title} initialPlaybackSpeed={lesson.plan.avatar_playback_speed} validatedSignIds={validated} prototypeSignIds={prototypes} reviewSignIds={reviewAnimations} allowPrototype={allowPrototype} onEnablePrototype={() => previewGestures(true)} onInteraction={record} />}
    </section>
    <details ref={practiceSectionRef} className="practice-section">
      <summary>Practice questions / <span lang="si">පුහුණු ප්‍රශ්න</span></summary>
      {practiceCard}
    </details>
    <details className="lesson-card reviewer-settings"><summary>Teaching & review settings</summary>
      <div className="avatar-playback-controls">
        <label><input type="checkbox" checked={showAvatar} onChange={event => { setShowAvatar(event.target.checked); record(event.target.checked ? 'avatar_enabled' : 'text_visual_baseline') }} /> Show avatar support</label>
        <label><input type="checkbox" checked={allowPrototype} onChange={event => previewGestures(event.target.checked)} /> Preview unvalidated gestures (reviewers only)</label>
      </div>
      <p>{label(strategy)} · {lesson.plan.misconception_support}</p>
      <details><summary>Why this lesson?</summary><p>{lesson.plan.source === 'preview' ? 'Manually selected preview · no diagnostic data.' : 'Diagnostic-based support.'} {lesson.learning_objective}</p><p>{lesson.plan.rationale}</p><p>Strategy engine: <code>{lesson.plan.model_version}</code>. {lesson.plan.model_version.startsWith('rule-based') && 'This is a transparent baseline, not a trained ML model.'}</p><p>Content: {lesson.plan.content_version} · teacher review required.</p><p>Additional support: {lesson.plan.supporting_strategies.map(label).join(', ') || 'none'}. Preferred format: {lesson.plan.preferred_mode}.</p></details>
      <details className="practice-evidence"><summary>Session insights & export</summary><p>{independent} / {lesson.practice_questions.length} correct on the first attempt without hints, viewing the worked solution or Ask tutor help. Repeated tries do not increase this count.</p><p>{lesson.plan.reassessment_note}</p>
          <p>Evidence includes numeric answer attempts, hints, replay events and timing. It stays in memory until you export it. Reloading or changing the plan clears it; nothing here automatically updates mastery or Supabase.</p>
          <div className="lesson-actions"><button className="secondary-button" onClick={exportEvidence}>Export session evidence</button>{independent === lesson.practice_questions.length && lesson.plan.level !== 'extended' && <button className="primary-button" onClick={onNextTopic}>Preview the next topic</button>}</div>
      </details>
    </details>
  </>
}
