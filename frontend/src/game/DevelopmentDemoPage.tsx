import { useState } from 'react'
import { API_BASE_URL } from './api/game'
import { openDevelopmentCollectionStore } from './api/collectionStore'
import { GameCanvas } from './phaser/PhaserGame'
import { setDevelopmentDemo } from './developmentDemoState'
import type { DevelopmentDemoContext } from './developmentDemoState'

/** Separate page: no student bank, research queue, Tutor navigation or export. */
export function DevelopmentDemoPage() {
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function start() {
    if (busy) return
    setBusy(true); setError('')
    try {
      const endpoint = new URL(API_BASE_URL)
      if (!['localhost', '127.0.0.1', '[::1]'].includes(endpoint.hostname)
        || !['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)) throw new Error('Localhost only.')
      const response = await fetch(`${API_BASE_URL}/game/development-demo/bootstrap`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, cache: 'no-store', credentials: 'omit',
        body: JSON.stringify({ development_demo: true }), signal: AbortSignal.timeout(15000),
      })
      if (!response.ok) throw new Error('Start the separate local demo backend with demo mode enabled.')
      const value = await response.json() as DevelopmentDemoContext
      if (value.student_id !== 'DEMO_TEAM' || value.classification !== 'DEVELOPMENT_DEMO_NOT_RESEARCH'
        || value.concept_id !== 'linear_equations' || value.assessment_phase !== 'pre_tutor'
        || !Array.isArray(value.session_ids) || !value.session_ids.length || !value.capability) throw new Error('Invalid demo designation.')
      setDevelopmentDemo(value)
      openDevelopmentCollectionStore()
      setReady(true)
    } catch (failure) {
      setDevelopmentDemo(null)
      setError(failure instanceof Error ? failure.message : 'Development demo unavailable.')
    } finally { setBusy(false) }
  }
  return <main style={{ display: 'block', width: 'min(1180px, calc(100% - 32px))', margin: '0 auto', padding: '20px 0' }}>
    <section style={{ background: '#fff3ce', color: '#372b00', padding: '14px', marginBottom: '16px', border: '2px solid #ad7500' }}>
      <h1 style={{ fontSize: '1.2rem', margin: '0 0 8px' }}>Game ML Prediction</h1>
      {!ready && <button type="button" disabled={busy} onClick={() => void start()}>{busy ? 'Starting…' : 'Start Game'}</button>}
      {ready && <button type="button" onClick={() => window.location.reload()}>Start a fresh session</button>}
      {' '}<a href="/">Exit</a>
      {error && <p role="alert">{error}</p>}
    </section>
    {ready && <GameCanvas />}
  </main>
}
