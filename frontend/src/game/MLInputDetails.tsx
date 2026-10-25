import { useEffect, useState } from 'react'
import { fetchMlInputPreview } from './api/gameApi'
import { copyMlFeatures, ML_INPUT_NAMES, mlFeaturesForCopy, mlFeaturesJson } from './mlInputFeatures'
import type { MLInputPreview } from './mlInputFeatures'
import './MLInputDetails.css'

export function MLInputDetails({ sessionId }: { sessionId: string | null }) {
  const [loaded, setLoaded] = useState<{ attempt: number; preview: MLInputPreview | null; error: string } | null>(null)
  const [copyStatus, setCopyStatus] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    if (!sessionId) {
      return () => controller.abort()
    }
    void fetchMlInputPreview(sessionId, controller.signal).then(result => {
      if (controller.signal.aborted) return
      if (result.game_session_id !== sessionId) throw new Error('Session evidence does not match these results.')
      setLoaded({ attempt: retry, preview: result, error: '' })
    }).catch(() => {
      if (!controller.signal.aborted) setLoaded({ attempt: retry, preview: null,
        error: 'Saved ML evidence could not be loaded. Values remain unavailable; retry after recording is saved.' })
    })
    return () => controller.abort()
  }, [sessionId, retry])

  const current = loaded?.attempt === retry ? loaded : null
  const preview = current?.preview
  const loading = !!sessionId && !current
  const error = !sessionId ? 'Saved session evidence is unavailable.' : current?.error
  const features = mlFeaturesForCopy(preview?.features)
  const missing = ML_INPUT_NAMES.filter(name => features[name] === null)
  async function copy() {
    try {
      await copyMlFeatures(features, navigator.clipboard)
      setCopyStatus(missing.length ? 'Copied JSON with null values. Not ready for ML inference.' : 'Copied all nine values. Confirm the Colab model contract before inference.')
    } catch { setCopyStatus('Copy failed. Select and copy the JSON below.') }
  }

  return <details className="ml-input-details">
    <summary>ML Input Details — Research Preview</summary>
    <div className="ml-input-details__body">
      <p>Read-only saved session evidence. A model estimate requires researcher verification and separate approval for this exact session.</p>
      <p className="ml-input-details__status" role="status">
        {loading ? 'Loading saved evidence…' : missing.length
          ? 'Not ready for ML inference: required features are unavailable.'
          : 'All nine values available. Colab compatibility is unverified; this record is not yet cleared for inference.'}
      </p>
      {error && <p role="alert">{error}</p>}
      <button type="button" className="ml-input-details__refresh" disabled={loading || !sessionId} onClick={() => { setCopyStatus(''); setRetry(n => n + 1) }}>{error ? 'Retry evidence' : 'Refresh evidence'}</button>
      <dl>
        {ML_INPUT_NAMES.map(name => <div key={name}>
          <dt><code>{name}</code></dt>
          <dd>{features[name] === null ? 'Unavailable' : String(features[name])}
            {preview?.unavailable_reasons?.[name] && <small>{preview.unavailable_reasons[name]}</small>}
          </dd>
        </div>)}
      </dl>
      <p><strong>First-attempt definition:</strong> correct first attempts / all planned steps. Drag &amp; Drop counts operation steps; Hangman counts one final-answer step per question.</p>
      <p><strong>Time:</strong> <code>game_active_time_sec</code> is the saved, rounded sum of recorded task durations. It is elapsed task time, not independently verified active engagement.</p>
      <p><strong>Model contract:</strong> research inference uses a separately verified legacy adapter, including hint requests per task and three-decimal rounding. This preview uses backend analytics definitions; copied JSON is not automatically the model's inference vector.</p>
      <button type="button" className="ml-input-details__copy" disabled={loading} onClick={() => void copy()}>Copy ML Features</button>
      <p role="status" aria-live="polite">{copyStatus}</p>
      <label>Exact JSON — missing values are null
        <textarea readOnly value={mlFeaturesJson(features)} rows={11} spellCheck={false} />
      </label>
    </div>
  </details>
}
