import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { setCollectionStudent, validateStudentCode } from './collectionIdentity'
import { getCollectionStore, openCollectionStore } from './api/collectionStore'
import { CollectionExport } from './CollectionExport'
import './CollectionGate.css'
import { readLearningContext, selectLearningStudent } from '../learningContext'

export function CollectionGate({ children, onContinue }: { children: ReactNode; onContinue?: () => void }) {
  const [lock, setLock] = useState(false)
  const [code, setCode] = useState(() => {
    try { return readLearningContext()?.studentId ?? '' } catch { return '' }
  })
  const [active, setActive] = useState<string | null>(null)
  const [recoveryOnly, setRecoveryOnly] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState(() => navigator.locks ? '' : 'Use current Chrome or Edge for safe single-tab collection.')
  const [, render] = useState(0)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!navigator.locks) return
    let cancelled = false
    const controller = new AbortController()
    const waiting = window.setTimeout(() => {
      if (!cancelled) setError('Waiting for another Game collection tab. Close it before collecting here.')
    }, 1000)
    let release: (() => void) | undefined
    let unsubscribe: (() => void) | undefined
    void navigator.locks.request('game-school-collection-v1', { signal: controller.signal }, async () => {
      window.clearTimeout(waiting)
      if (cancelled) return
      try {
        const store = openCollectionStore()
        unsubscribe = store.subscribe(() => {
          if (store.fatalError) window.dispatchEvent(new Event('game-collection-stop'))
          render(n => n + 1)
        })
        setLock(true)
        setError('')
        await new Promise<void>(resolve => { release = resolve })
      } catch (e) { setError(e instanceof Error ? e.message : 'Browser storage is unavailable.') }
    }).catch(e => { if (!cancelled) setError(String(e)) })
    return () => {
      cancelled = true; window.clearTimeout(waiting); controller.abort()
      unsubscribe?.(); release?.(); setCollectionStudent(null)
    }
  }, [])

  const store = lock ? getCollectionStore() : null
  const rows = store?.sessions().filter(row => !row.closed) ?? []
  const pending = rows.some(row => store!.status(row.request.client_session_id) !== 'Saved')
  const fatal = store?.fatalError

  useEffect(() => {
    if (!lock) return
    const warn = (event: BeforeUnloadEvent) => {
      if (getCollectionStore().sessions().some(row => !row.closed)) { event.preventDefault(); event.returnValue = '' }
    }
    const online = () => {
      if (active) for (const row of getCollectionStore().sessions().filter(row => !row.closed && row.request.student_id === active)) {
        void getCollectionStore().flush(row.request.client_session_id)
      }
    }
    const navigation = (event: MouseEvent) => {
      if ((event.target as Element).closest('.app-navigation button') && getCollectionStore().sessions().some(row => !row.closed)) {
        event.preventDefault(); event.stopPropagation()
        setError('End the current Game collection explicitly before changing modules.')
      }
    }
    const warning = () => setError('End the unfinished collection explicitly before choosing another game.')
    window.addEventListener('beforeunload', warn)
    window.addEventListener('online', online)
    document.addEventListener('click', navigation, true)
    window.addEventListener('game-collection-warning', warning)
    return () => {
      window.removeEventListener('beforeunload', warn); window.removeEventListener('online', online)
      document.removeEventListener('click', navigation, true); window.removeEventListener('game-collection-warning', warning)
    }
  }, [active, lock])

  function choose() {
    try {
      const selected = validateStudentCode(code)
      if (rows.some(row => row.request.student_id !== selected)) throw new Error('Recover and close the previous learner’s collection before switching codes.')
      selectLearningStudent(selected)
      setCollectionStudent(selected)
      setRecoveryOnly(rows.length > 0)
      setActive(selected)
      setError('')
    } catch (e) { setError(e instanceof Error ? e.message : 'Invalid code') }
  }

  async function recover() {
    setBusy(true)
    try { for (const row of rows) await store!.flush(row.request.client_session_id) }
    finally { setBusy(false) }
  }

  function close() {
    try {
      if (pending) throw new Error('Recover all pending writes before switching.')
      window.dispatchEvent(new Event('game-collection-stop'))
      for (const row of rows) store!.close(row.request.client_session_id)
      setCollectionStudent(null)
      setActive(null); setRecoveryOnly(false); setCode(''); setError(''); setConfirmed(false)
      return true
    } catch (e) { setError(String(e)); return false }
  }

  return <div className="collection-shell">
    <section className="collection-gate" aria-label="Researcher Game collection">
      <strong>Researcher Game collection</strong>
      {!active ? <form onSubmit={event => { event.preventDefault(); choose() }}>
        <label htmlFor="collection-student">Assigned student code</label>
        <input id="collection-student" value={code} onChange={event => setCode(event.target.value)} placeholder="STU_001" autoComplete="off" maxLength={10} disabled={!lock || !!fatal} />
        <button type="submit" disabled={!lock || !!fatal}>Set student</button>
      </form> : <p>Active student: <strong data-testid="active-student">{active}</strong></p>}
      <p>No learner names. Codes are researcher assigned; no shared student registry is created.</p>
      {(error || fatal) && <p role="alert">{fatal || error}</p>}
      {recoveryOnly && <p>Previous evidence found. Recover it, then end this collection. Unfinished gameplay cannot resume after refresh; start a new session afterward.</p>}
      {rows.map(row => <p key={row.request.client_session_id}>
        {row.request.student_id} · {row.mode} · Game session: <code>{row.request.client_session_id}</code><br />
        <strong>{store!.status(row.request.client_session_id)}</strong> · {row.writes.length} queued writes · {row.completed ? 'Assessment complete' : 'Assessment incomplete'}
        {row.error && <span role="alert"> · {row.error}</span>}
      </p>)}
      {rows.length > 0 && <>
        {onContinue && rows.every(row => row.completed) && <button type="button" disabled={pending || busy || !!fatal} onClick={() => { if (close()) onContinue() }}>Continue to AI Tutor / AI Tutor වෙත යන්න</button>}
        <button type="button" onClick={() => void recover()} disabled={!active || busy || !!fatal}>Retry / recover saved evidence</button>
        <label><input type="checkbox" disabled={!active} checked={confirmed} onChange={event => setConfirmed(event.target.checked)} /> I am ending this collection. Unfinished assessments stay incomplete.</label>
        <button type="button" onClick={close} disabled={!active || !confirmed || pending || busy || !!fatal}>End collection / switch learner</button>
      </>}
      {active && rows.length === 0 && <button type="button" onClick={close}>Switch learner</button>}
      <CollectionExport disabled={!lock || pending || busy || !!fatal} />
    </section>
    {active && !recoveryOnly && !fatal && children}
  </div>
}
