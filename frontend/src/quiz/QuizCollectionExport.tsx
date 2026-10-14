import { useState } from 'react'
import { API_BASE_URL } from './api'

export function QuizCollectionExport({ disabled }: { disabled: boolean }) {
  const [key, setKey] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  async function download() {
    if (disabled || busy || !key.trim()) return
    setBusy(true); setMessage('')
    try {
      const response = await fetch(`${API_BASE_URL}/quiz/exports/collection`, {
        headers: { Accept: 'application/zip', Authorization: `Bearer ${key.trim()}` },
        cache: 'no-store', signal: AbortSignal.timeout(120000),
      })
      if (!response.ok) throw new Error(`Quiz export failed (${response.status}). Check researcher access and backend connection.`)
      if (response.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/zip') {
        throw new Error('The server did not return a Quiz CSV archive.')
      }
      const blob = await response.blob()
      if (!blob.size) throw new Error('The Quiz CSV archive was empty.')
      const url = URL.createObjectURL(blob)
      const filename = response.headers.get('Content-Disposition')?.match(/filename="(quiz-collection-[0-9TZ-]+\.zip)"/)?.[1]
        ?? `quiz-collection-${new Date().toISOString().replace(/[:.]/g, '-')}.zip`
      const anchor = document.createElement('a')
      try {
        anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click()
      } finally {
        anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      }
      setMessage('Download started. Check your browser downloads.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Quiz export failed.')
    } finally { setBusy(false) }
  }

  return <details className="quiz-collection-export">
    <summary>Download Quiz CSV files</summary>
    <p>Contains saved database records, including incomplete Quiz sessions.</p>
    <form onSubmit={event => { event.preventDefault(); void download() }}>
      <label htmlFor="quiz-export-key">Researcher export key</label>
      <input id="quiz-export-key" type="password" autoComplete="off" value={key}
        onChange={event => setKey(event.target.value)} disabled={disabled || busy} />
      <button type="submit" disabled={disabled || busy || !key.trim()}>Download Quiz CSVs (.zip)</button>
    </form>
    {disabled && <p>Recover pending evidence before downloading.</p>}
    {message && <p role="status">{message}</p>}
  </details>
}
