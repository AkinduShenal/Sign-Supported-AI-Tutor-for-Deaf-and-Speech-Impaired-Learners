import assert from 'node:assert/strict'
import test from 'node:test'
import { withQuizTimeout } from '../src/quiz/requestTimeout.ts'

function stalledRequest(signal: AbortSignal): Promise<never> {
  return new Promise((_resolve, reject) => {
    const keepAlive = setTimeout(() => reject(new Error('Request never settled')), 200)
    signal.addEventListener('abort', () => {
      clearTimeout(keepAlive)
      reject(signal.reason)
    }, { once: true })
  })
}

test('Quiz question request times out even with a caller cancellation signal', async () => {
  const caller = new AbortController()
  await assert.rejects(
    withQuizTimeout(stalledRequest, caller.signal, 20),
    /Quiz request timed out/,
  )
  assert.equal(caller.signal.aborted, false)
})

test('caller cancellation stays distinct from a timeout', async () => {
  const caller = new AbortController()
  const request = withQuizTimeout(stalledRequest, caller.signal, 100)
  caller.abort(new Error('Page changed'))
  await assert.rejects(request, /Page changed/)
})
