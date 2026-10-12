// Pure, Phaser-free decision logic for Hangman (Milestone 4): the answer
// buffer, the correct/wrong comparison, failure after too many wrong
// submissions, and the Hangman-specific star rule. Kept separate from
// HangmanGameScene.ts so this can be unit-tested directly (node:test can't
// easily drive a live Phaser.Scene) and so the drawing code never has to
// re-derive what counts as a wrong answer.

// Ten wrong submissions releases the grip (revised design — the figure
// hangs from a bar by both hands, 5 fingers each, and one finger slips per
// wrong answer; see HangmanFigure.ts). The "stage" in HangmanFigure is
// always exactly the number of wrong submissions so far — correct answers
// and hints never move it.
export const MAX_WRONG_SUBMISSIONS = 10

export const HANGMAN_MAX_STARS = 3

// Only digits are ever appended through this; the keypad never calls this
// with more than one character, and the capped length guards against a
// learner holding a key down.
const MAX_BUFFER_LENGTH = 6

export function appendDigit(buffer: string, digit: string): string {
  if (buffer.length >= MAX_BUFFER_LENGTH) return buffer
  return buffer + digit
}

// '-' is only meaningful as the sign of the whole answer, so it is only
// accepted as the first character — pressing it again, or after a digit, is
// a no-op rather than producing something like "4-" or "--3". None of the
// current 18 variants need a negative finalAnswer, but the milestone asks
// for the key to exist regardless (see Milestone_4 §5), so this keeps it
// safe to press without ever producing an unsubmittable buffer.
export function appendMinus(buffer: string): string {
  return buffer.length === 0 ? '-' : buffer
}

export function backspace(buffer: string): string {
  return buffer.slice(0, -1)
}

// A lone '-' or an empty buffer can never be submitted (Milestone 4 §6: "Do
// not allow an empty answer submission").
export function isSubmittable(buffer: string): boolean {
  return buffer.length > 0 && buffer !== '-'
}

// Numeric comparison (not string equality) so "08" or a stray leading zero
// still matches "8" — the learner solved the equation either way.
function normalizeNumeric(value: string): string {
  const parsed = Number(value)
  return Number.isNaN(parsed) ? value : String(parsed)
}

export function isCorrectSubmission(buffer: string, finalAnswer: string): boolean {
  return normalizeNumeric(buffer) === normalizeNumeric(finalAnswer)
}

export interface SubmissionOutcome {
  correct: boolean
  // Wrong-submission count (== fingers slipped) after this submission.
  wrongCount: number
  // True exactly on the submission that reaches MAX_WRONG_SUBMISSIONS
  // without ever being correct (Milestone 4 §10).
  failed: boolean
}

export function submitAnswer(
  buffer: string,
  finalAnswer: string,
  wrongCountSoFar: number,
): SubmissionOutcome {
  if (isCorrectSubmission(buffer, finalAnswer)) {
    return { correct: true, wrongCount: wrongCountSoFar, failed: false }
  }
  const wrongCount = Math.min(MAX_WRONG_SUBMISSIONS, wrongCountSoFar + 1)
  return { correct: false, wrongCount, failed: wrongCount >= MAX_WRONG_SUBMISSIONS }
}

// A Hangman-specific reward rule (Milestone 4 §16), independent of
// stars.ts's starsForTask() (which Drag & Drop keeps unchanged): Hangman has
// no "operation step" concept, only submitted-answer counts, so the
// thresholds are defined directly on the wrong-submission count instead,
// scaled to the ten-wrong ceiling above. Shares formatStars()/
// MAX_STARS_PER_TASK from stars.ts for display.
export function starsForHangman(wrongSubmissions: number): number {
  if (wrongSubmissions <= 0) return 3
  if (wrongSubmissions <= 3) return 2
  if (wrongSubmissions <= 9) return 1
  return 0
}
