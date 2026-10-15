import { useEffect, useState } from 'react'
import { validateStudentCode } from '../game/collectionIdentity'
import { openQuizCollectionStore } from './collectionStore'
import { QuizCollectionExport } from './QuizCollectionExport'
import type { PendingQuizWrites } from './pendingQuizWrites'
import { QuizExperience } from './QuizAssessment'
import './quizCollection.css'

export function QuizCollectionGate() {
  const [store, setStore] = useState<PendingQuizWrites | null>(null)
  const [locked, setLocked] = useState(false)
  const [code, setCode] = useState('')
  const [active, setActive] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [revision, setRevision] = useState(0)
  const [error, setError] = useState(() => navigator.locks ? '' : 'Use current Chrome or Edge for Quiz collection.')
  const [, render] = useState(0)

  useEffect(() => {
    if (!navigator.locks) return
    let cancelled = false
    const controller = new AbortController()
    let release: (() => void) | undefined
    let unsubscribe: (() => void) | undefined
    const waiting = window.setTimeout(() => { if (!cancelled) setError('Waiting for another Quiz collection tab.') }, 1000)
    void navigator.locks.request('quiz-school-collection-v1', { signal: controller.signal }, async () => {
      window.clearTimeout(waiting)
      if (cancelled) return
      try {
        const opened = openQuizCollectionStore()
        unsubscribe = opened.subscribe(() => render(value => value + 1))
        setStore(opened); setLocked(true); setError('')
        await new Promise<void>(resolve => { release = resolve })
      } catch (cause) { setError(cause instanceof Error ? cause.message : 'Browser storage is unavailable.') }
    }).catch(cause => { if (!cancelled) setError(String(cause)) })
    return () => { cancelled = true; window.clearTimeout(waiting); controller.abort(); unsubscribe?.(); release?.() }
  }, [])

  const rows = store?.openSessions() ?? []
  const pending = rows.some(row => store!.status(`QUIZ-${row.request.client_session_id}`) !== 'Saved')
  const fatal = store?.fatalError

  useEffect(() => {
    if (!locked || !store) return
    const warn = (event: BeforeUnloadEvent) => {
      if (store.openSessions().length) { event.preventDefault(); event.returnValue = '' }
    }
    const online = () => {
      if (active && store.openSessions().some(row => store.status(`QUIZ-${row.request.client_session_id}`) !== 'Saved')) void recover()
    }
    const navigation = (event: MouseEvent) => {
      if ((event.target as Element).closest('.app-navigation button') && store.openSessions().length) {
        event.preventDefault(); event.stopPropagation(); setError('End the Quiz collection before changing modules.')
      }
    }
    window.addEventListener('beforeunload', warn)
    window.addEventListener('online', online)
    document.addEventListener('click', navigation, true)
    return () => {
      window.removeEventListener('beforeunload', warn)
      window.removeEventListener('online', online)
      document.removeEventListener('click', navigation, true)
    }
  // The browser online event uses this learner's recovery action.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, locked, store])

  function choose() {
    try {
      const selected = validateStudentCode(code)
      if (rows.some(row => row.request.student_id !== selected)) throw new Error('Recover and close the previous learner’s Quiz before switching codes.')
      setActive(selected); setError('')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Invalid learner code') }
  }

  async function recover() {
    if (!store || !active) return
    setBusy(true)
    try {
      for (const row of store.openSessions().filter(item => item.request.student_id === active)) {
        await store.flush(`QUIZ-${row.request.client_session_id}`)
      }
      setRevision(value => value + 1)
    } finally { setBusy(false) }
  }

  function close() {
    if (!store) return
    try {
      if (pending) throw new Error('Recover all pending Quiz evidence before switching.')
      for (const row of rows) store.close(`QUIZ-${row.request.client_session_id}`)
      setActive(null); setCode(''); setConfirmed(false); setError(''); setRevision(value => value + 1)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not end collection') }
  }

  return <div className="quiz-collection-shell">
    <section className="quiz-collection-gate" aria-label="Researcher Quiz collection">
      <strong>Researcher Quiz collection</strong>
      {!active ? <form onSubmit={event => { event.preventDefault(); choose() }}>
        <label htmlFor="quiz-student-code">Assigned learner code</label>
        <input id="quiz-student-code" value={code} onChange={event => setCode(event.target.value)}
          placeholder="STU_001" maxLength={10} autoComplete="off" disabled={!locked || !!fatal} />
        <button type="submit" disabled={!locked || !!fatal}>Set learner</button>
      </form> : <p>Active learner: <strong data-testid="quiz-active-student">{active}</strong></p>}
      <p>Use the approved code roster. Do not enter learner names.</p>
      {(error || fatal) && <p role="alert">{fatal || error}</p>}
      {rows.map(row => <p key={row.request.client_session_id}>
        {row.request.student_id} · Session: <code>QUIZ-{row.request.client_session_id}</code><br />
        <strong>{store!.status(`QUIZ-${row.request.client_session_id}`)}</strong> · {row.responses.filter(item => item.saved).length}/{row.question_ids.length} saved responses · {row.completed ? 'Assessment Complete' : 'Assessment Incomplete'}
        {row.error && <span role="alert"> · {row.error}</span>}
      </p>)}
      {rows.length > 0 && <>
        <button type="button" onClick={() => void recover()} disabled={!active || !pending || busy || !!fatal}>Retry / Recover Quiz evidence</button>
        <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} disabled={!active} /> I am ending this collection. An unfinished Quiz remains incomplete.</label>
        <button type="button" onClick={close} disabled={!active || !confirmed || pending || busy || !!fatal}>End collection / switch learner</button>
      </>}
      {active && rows.length === 0 && <button type="button" onClick={close}>Switch learner</button>}
      <QuizCollectionExport disabled={!locked || pending || busy || !!fatal} />
    </section>
    {active && store && !fatal && <QuizExperience key={`${active}-${revision}`} studentCode={active} store={store} />}
  </div>
}
