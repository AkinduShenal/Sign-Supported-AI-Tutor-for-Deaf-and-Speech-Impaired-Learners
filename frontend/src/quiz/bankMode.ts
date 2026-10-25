// 'dynamic' is the teacher-approved bank (pp1_dynamic_v1); 'dynamic_dev' is the
// local-only draft bank for development; 'fixed' is the original ten questions.
export type QuizBankMode = 'fixed' | 'dynamic_dev' | 'dynamic'

export function isDynamicBankMode(mode: QuizBankMode | undefined): boolean {
  return mode === 'dynamic' || mode === 'dynamic_dev'
}

// New sessions use the approved dynamic bank unless a developer opts into the
// draft bank (VITE_QUIZ_DYNAMIC_DEV=true) or the fixed bank (VITE_QUIZ_BANK_MODE=fixed).
export function newSessionBankMode(env: Record<string, unknown>): QuizBankMode {
  if (env.VITE_QUIZ_DYNAMIC_DEV === 'true') return 'dynamic_dev'
  if (env.VITE_QUIZ_BANK_MODE === 'fixed') return 'fixed'
  return 'dynamic'
}
