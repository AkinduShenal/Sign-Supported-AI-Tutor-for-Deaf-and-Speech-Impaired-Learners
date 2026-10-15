import assert from 'node:assert/strict'
import test from 'node:test'
import { motionBeatIndex } from '../src/components/motionTiming.ts'

test('phrase changes follow clip-time boundaries and preserve the final result', () => {
  const beats = [{ start: 0, end: 2 }, { start: 2, end: 5 }, { start: 5, end: 8 }]
  assert.equal(motionBeatIndex(beats, 0), 0)
  assert.equal(motionBeatIndex(beats, 1.999), 0)
  assert.equal(motionBeatIndex(beats, 2), 1)
  assert.equal(motionBeatIndex(beats, 5), 2)
  assert.equal(motionBeatIndex(beats, 9), 2)
  assert.equal(motionBeatIndex([], 0), -1)
})
