import type { Language } from './language'

interface UiStrings {
  taskProgress: (current: number, total: number) => string
  chooseOperationPrompt: string
  hintButton: (shown: number, total: number) => string
  retryButton: string
  skipButton: string
  continueButton: string
  finishButton: string
  correctFeedback: (variableLabel: string, value: number) => string
  incorrectFeedback: string
  sessionComplete: string
  tasksSolved: (solved: number, total: number) => string
  taskStatusSolved: string
  taskStatusNotSolved: string
  taskStatusSkipped: string
  attemptsLabel: (count: number) => string
  hintsLabel: (count: number) => string
  languageToggleLabel: string
}

// Sinhala strings are draft placeholders for this prototype slice and have
// not been reviewed by a native speaker or Sinhala maths teacher yet.
export const UI_STRINGS: Record<Language, UiStrings> = {
  en: {
    taskProgress: (current, total) => `Task ${current} of ${total}`,
    chooseOperationPrompt: 'Choose the move that keeps the balance level',
    hintButton: (shown, total) => `Show a hint (${shown}/${total} used)`,
    retryButton: 'Try again',
    skipButton: 'Skip this task',
    continueButton: 'Continue',
    finishButton: 'Finish',
    correctFeedback: (variableLabel, value) => `Correct! ${variableLabel} = ${value}`,
    incorrectFeedback: 'That tips the balance. Try again, or ask for a hint.',
    sessionComplete: 'Session complete',
    tasksSolved: (solved, total) => `${solved} of ${total} tasks solved.`,
    taskStatusSolved: 'solved',
    taskStatusNotSolved: 'not solved',
    taskStatusSkipped: 'skipped',
    attemptsLabel: (count) => `${count} attempt(s)`,
    hintsLabel: (count) => `${count} hint(s)`,
    languageToggleLabel: 'සිංහල',
  },
  si: {
    taskProgress: (current, total) => `කාර්යය ${current} න් ${total}`,
    chooseOperationPrompt: 'තුලනය සමතලව තබා ගන්නා ක්‍රියාව තෝරන්න',
    hintButton: (shown, total) => `ඉඟියක් පෙන්වන්න (${shown}/${total} භාවිතා කළා)`,
    retryButton: 'නැවත උත්සාහ කරන්න',
    skipButton: 'මෙම කාර්යය මඟ හරින්න',
    continueButton: 'ඉදිරියට යන්න',
    finishButton: 'අවසන් කරන්න',
    correctFeedback: (variableLabel, value) => `හරි! ${variableLabel} = ${value}`,
    incorrectFeedback: 'එයින් තුලනය නැඹුරු වේ. නැවත උත්සාහ කරන්න, හෝ ඉඟියක් ඉල්ලන්න.',
    sessionComplete: 'සැසිය සම්පූර්ණයි',
    tasksSolved: (solved, total) => `කාර්යයන් ${total} න් ${solved} ක් විසඳා ඇත.`,
    taskStatusSolved: 'විසඳා ඇත',
    taskStatusNotSolved: 'විසඳා නැත',
    taskStatusSkipped: 'මඟ හැරිණි',
    attemptsLabel: (count) => `උත්සාහයන් ${count}`,
    hintsLabel: (count) => `ඉඟි ${count}`,
    languageToggleLabel: 'English',
  },
}
