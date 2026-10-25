import { useEffect, useState } from 'react'
import { API_BASE_URL } from './api/game'
import { getCollectionStore } from './api/collectionStore'
import { forgetMLAcknowledgement, MLVerificationError, readyMLAcknowledgement, verifyGameML } from './gameMLVerification'
import { MLProficiencyCard } from './MLProficiencyCard'
import type { GameMLPredictionState } from './mlPrediction'

/** Caller keys this by session. Once the completed session is Saved, its
 *  one-time completion receipt is sent automatically; no researcher key. */
export function ResearcherMLResult({ sessionId }: { sessionId: string | null }) {
  const [state, setState] = useState<GameMLPredictionState>({ status: 'unavailable' })

  useEffect(() => {
    if (!sessionId) return
    const store = getCollectionStore()
    const controller = new AbortController()
    let started = false
    const check = () => {
      if (started) return
      const row = store.session(sessionId)
      const saved = readyMLAcknowledgement(sessionId, row.request, row.completed && store.status(sessionId) === 'Saved')
      if (!saved) return
      started = true
      setState({ status: 'loading' })
      verifyGameML(API_BASE_URL, saved, controller.signal)
        .then(prediction => {
          if (controller.signal.aborted) return
          setState({ status: 'ready', prediction })
          forgetMLAcknowledgement(sessionId)
        })
        .catch(failure => {
          if (controller.signal.aborted) return
          const problem = failure instanceof MLVerificationError ? failure : new MLVerificationError(0)
          setState({ status: [404, 422, 503].includes(problem.status) ? 'unavailable' : 'error' })
        })
    }
    check()
    const unsubscribe = store.subscribe(check)
    return () => { controller.abort(); unsubscribe() }
  }, [sessionId])

  return <MLProficiencyCard state={state} />
}
