import assert from 'node:assert/strict'
import test from 'node:test'
import { selectPlayback } from '../src/components/playbackPolicy.ts'

test('equation playback retains every repeated symbol and its caption index', () => {
  const requested = ['VARIABLE', 'ADDITION', 'NUMBER_3', 'SUBTRACTION', 'NUMBER_3', 'EQUATION', 'NUMBER_7', 'SUBTRACTION', 'NUMBER_3']
  const playback = selectPlayback(requested, [...new Set(requested)], [], [...new Set(requested)], true)
  assert.deepEqual(playback.map(sign => sign.name), requested)
  assert.deepEqual(playback.map(sign => sign.sourceIndex), requested.map((_, index) => index))
})

test('missing and unapproved clips retain the original token positions', () => {
  const requested = ['VARIABLE', 'EQUATION', 'NUMBER_4']
  assert.deepEqual(selectPlayback(requested, requested, ['EQUATION'], ['NUMBER_4'], false), [{ name: 'EQUATION', sourceIndex: 1 }])
  assert.deepEqual(selectPlayback(requested, ['EQUATION'], requested, [], true), [{ name: 'EQUATION', sourceIndex: 1 }])
})
