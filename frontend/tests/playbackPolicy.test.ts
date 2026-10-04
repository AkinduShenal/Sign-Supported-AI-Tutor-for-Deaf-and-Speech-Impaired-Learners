import test from 'node:test'
import assert from 'node:assert/strict'
import { selectPlayback } from '../src/components/playbackPolicy.ts'

test('unvalidated signs are not played by default', () => {
  assert.deepEqual(selectPlayback(['ADDITION'], ['ADDITION'], [], ['ADDITION'], false), [])
})
test('missing clips are skipped even if validated', () => {
  assert.deepEqual(selectPlayback(['MISSING'], [], ['MISSING'], [], true), [])
})
test('explicit reviewer opt-in admits prototypes, preserving repeated actions', () => {
  assert.deepEqual(selectPlayback(['NUMBER_1', 'NUMBER_1'], ['NUMBER_1'], [], ['NUMBER_1'], true), [
    { name: 'NUMBER_1', sourceIndex: 0 }, { name: 'NUMBER_1', sourceIndex: 1 },
  ])
})
test('validated clips keep their original positions after fallback', () => {
  assert.deepEqual(selectPlayback(['MISSING', 'EQUATION'], ['EQUATION'], ['EQUATION'], [], false), [{ name: 'EQUATION', sourceIndex: 1 }])
})
