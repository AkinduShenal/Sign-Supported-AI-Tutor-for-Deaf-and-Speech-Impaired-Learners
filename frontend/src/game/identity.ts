const STUDENT_ID_KEY = 'game.studentId'

// A pseudonymous, per-browser identifier — no name or other personal
// information is ever stored. There's no login system yet, so this is a
// stand-in until real learner accounts exist.
export function getOrCreateStudentId(): string {
  try {
    const existing = localStorage.getItem(STUDENT_ID_KEY)
    if (existing) return existing

    const generated = crypto.randomUUID()
    localStorage.setItem(STUDENT_ID_KEY, generated)
    return generated
  } catch {
    // Private browsing or blocked storage: fall back to a one-off id
    // rather than breaking the game.
    return crypto.randomUUID()
  }
}
