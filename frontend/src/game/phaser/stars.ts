export const MAX_STARS_PER_TASK = 3

// Stars reward correctness only: 3 for a first-try solve, 2 for one wrong
// answer, 1 for finishing. Hints and time deliberately don't count — asking
// for help isn't a penalty, and a slower response is not lower ability
// (repo research-integrity rule). Stars are a local, learner-facing reward;
// they're not sent to the backend and aren't part of the game analytics.
export function starsForTask(wrongAttempts: number): number {
  if (wrongAttempts <= 0) return MAX_STARS_PER_TASK
  if (wrongAttempts === 1) return 2
  return 1
}

export function formatStars(earned: number): string {
  const clamped = Math.max(0, Math.min(MAX_STARS_PER_TASK, earned))
  return '★'.repeat(clamped) + '☆'.repeat(MAX_STARS_PER_TASK - clamped)
}
