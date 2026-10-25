/** Explicit synthetic browser-only entry, never imported by the application. */
import { createRoot } from 'react-dom/client'
import { useEffect, useState } from 'react'
import { ResearcherMLResult } from '../../src/game/ResearcherMLResult'
import { openCollectionStore } from '../../src/game/api/collectionStore'
import '../../src/index.css'

const store = openCollectionStore()
export function Harness() {
  const [id, setId] = useState<string | null>(null)
  async function start(code: string) {
    for (const row of store.sessions().filter(row => !row.closed)) store.close(row.request.client_session_id)
    const next = crypto.randomUUID()
    store.start({ client_session_id: next, student_id: code, concept_id: 'linear_equations',
      learning_cycle_id: crypto.randomUUID(), assessment_phase: 'pre_tutor' }, 'hangman')
    await store.flush(next)
    store.requestCompletion(next)
    await store.flush(next)
    setId(next)
  }
  // Synchronize the fixture with the external durable-save queue acknowledgement.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void start('STU_999') }, [])
  return <main data-scenario={new URLSearchParams(location.search).get('state')} data-prepared={String(!!id)} style={{width:'min(100% - 32px, 1000px)',margin:'24px auto'}}>
    <p>Isolated visual test — synthetic session and prediction fixtures only.</p>
    <button id="fixture-switch" onClick={() => void start('STU_998')}>Switch synthetic learner</button>
    {id && <ResearcherMLResult key={id} sessionId={id} />}
  </main>
}
createRoot(document.getElementById('root')!).render(<Harness />)
