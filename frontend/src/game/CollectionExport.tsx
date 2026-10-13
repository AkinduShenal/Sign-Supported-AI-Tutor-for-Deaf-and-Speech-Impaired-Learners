import { useState } from 'react'
import { API_BASE_URL } from './api/game'
import { requestGameCsvDownload } from './api/gameCsvDownload'

export function CollectionExport({ disabled }: { disabled: boolean }) {
  const [key, setKey] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [message, setMessage] = useState('')
  const [failed, setFailed] = useState(false)

  async function download() {
    if (disabled || downloading) return
    setDownloading(true); setMessage(''); setFailed(false)
    try {
      const { blob, filename } = await requestGameCsvDownload(API_BASE_URL, key)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      try {
        anchor.href = url; anchor.download = filename
        document.body.appendChild(anchor)
        anchor.click()
      } finally {
        anchor.remove()
        window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      }
      setMessage('Download started. Check your browser’s downloads.')
    } catch (error) {
      setFailed(true)
      setMessage(error instanceof Error ? error.message : 'CSV download failed. Please retry.')
    } finally { setDownloading(false) }
  }

  return <details className="collection-export">
    <summary>Download Game CSV files</summary>
    <p>Downloads all saved Game records as a ZIP containing CSV files and a manifest.</p>
    <form onSubmit={event => { event.preventDefault(); void download() }}>
      <label htmlFor="game-export-key">Researcher export key</label>
      <input id="game-export-key" type="password" autoComplete="off" value={key}
        onChange={event => setKey(event.target.value)} disabled={disabled || downloading} />
      <button type="submit" disabled={disabled || downloading || !key.trim()}>
        {downloading ? 'Downloading…' : 'Download Game CSVs (.zip)'}
      </button>
    </form>
    {disabled && <p>Recover pending writes before downloading. Downloads contain saved database records only.</p>}
    {message && <p role={failed ? 'alert' : 'status'}>{message}</p>}
  </details>
}
