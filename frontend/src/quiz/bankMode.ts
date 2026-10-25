// 'dynamic' is the teacher-approved bank (pp1_dynamic_v1); 'dynamic_dev' is the
// local-only draft bank for development; 'fixed' is the original ten questions.
export type QuizBankMode = 'fixed' | 'dynamic_dev' | 'dynamic'

export function isDynamicBankMode(mode: QuizBankMode | undefined): boolean {
  return mode === 'dynamic' || mode === 'dynamic_dev'
}

// Keep the existing ten-question bank until the dynamic schema and approved
// bank are installed. Opt in with VITE_QUIZ_BANK_MODE=dynamic, or use the
// isolated draft bank with VITE_QUIZ_DYNAMIC_DEV=true.
export function newSessionBankMode(env: Record<string, unknown>): QuizBankMode {
  if (env.VITE_QUIZ_DYNAMIC_DEV === 'true') return 'dynamic_dev'
  if (env.VITE_QUIZ_BANK_MODE === 'dynamic') return 'dynamic'
  return 'fixed'
}
