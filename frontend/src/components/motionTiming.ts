/** Read the baked cue sheet using clip time, so pause and speed stay in sync. */
export function motionBeatIndex(beats: { start: number; end: number }[], time: number): number {
  if (!beats.length) return -1
  let index = 0
  for (let i = 1; i < beats.length; i++) {
    if (time >= beats[i].start) index = i
  }
  return index
}
