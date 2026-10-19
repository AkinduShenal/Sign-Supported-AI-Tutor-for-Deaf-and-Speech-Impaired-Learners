// Bilingual (English + Sinhala) UI labels for the live Phaser game.
//
// DRAFT: the Sinhala below has NOT been reviewed by a native speaker or a
// Sinhala maths teacher. Reuse the wording from the old prototype strings
// (game/i18n/uiStrings.ts) and the Tutor (components/sinhalaLessonText.ts)
// where it overlaps, and get it reviewed before any learner or research
// use. Never describe it as validated.
//
// Both languages remain visible. Sinhala is primary by default; the Game
// language toggle changes their order and prominence without restarting play.
import { formatGameLanguages } from '../gameLanguage.ts'

// Extra room for Sinhala glyphs (tall marks above and below the line), and
// never bold: synthetic bold smears the marks together.
export const SINHALA_TEXT = {
  lineSpacing: 8,
  padding: { top: 4, bottom: 4 },
}

// The Sinhala fonts come before the generic fallback so canvas text that
// mixes English and Sinhala renders on Windows, Android and macOS.
export const FONT_FAMILY =
  'system-ui, "Segoe UI", Roboto, "Nirmala UI", "Noto Sans Sinhala", "Iskoola Pota", "Sinhala MN", sans-serif'

export interface Bilingual {
  en: string
  si: string
}

export const GAME_TEXT = {
  balanceEquation: { en: 'Balance the Equation', si: 'සමීකරණය තුලනය කරන්න' },
  instruction: {
    en: 'Choose the operation that keeps the equation balanced.',
    si: 'සමීකරණය තුලනය කර තබන ක්‍රියාව තෝරන්න.',
  },
  dropHere: { en: 'Drop operation here', si: 'මෙතැනට දමන්න' },
  hint: { en: 'Hint', si: 'ඉඟිය' },
  next: { en: 'Next', si: 'ඊළඟ' },
  correct: { en: '✓ Correct!', si: 'නිවැරදියි!' },
  tryAgain: { en: '✕ Try again', si: 'නැවත උත්සාහ කරන්න' },
  perfect: { en: 'Perfect!', si: 'විශිෂ්ටයි!' },
  wellDone: { en: 'Well done!', si: 'හොඳයි!' },
  level: { en: 'Level', si: 'මට්ටම' },
  step: { en: 'Step', si: 'පියවර' },
  easy: { en: 'Easy', si: 'පහසු' },
  medium: { en: 'Medium', si: 'මධ්‍යම' },
  hard: { en: 'Hard', si: 'අමාරු' },
  preparing: { en: 'Preparing your assessment…', si: 'ඔබේ ඇගයීම සූදානම් කරමින්…' },
  calculating: { en: 'Calculating your results…', si: 'ප්‍රතිඵල ගණනය කරමින්…' },
  assessmentComplete: { en: 'Assessment Complete!', si: 'ඇගයීම අවසන්!' },
  sessionComplete: { en: 'Session Complete!', si: 'සැසිය අවසන්!' },
  nextTutor: { en: 'Next: meet your Tutor!', si: 'ඊළඟට: ඔබේ ගුරුවරයා හමුවන්න!' },
  showDetails: { en: 'Show details ▾', si: 'විස්තර පෙන්වන්න' },
  hideDetails: { en: 'Hide details ▴', si: 'විස්තර සඟවන්න' },
  chooseGame: { en: 'Choose Your Game', si: 'ක්‍රීඩාව තෝරන්න' },
  play: { en: 'Play', si: 'ක්‍රීඩා කරන්න' },
  comingNext: { en: 'Coming next', si: 'ඉක්මනින්' },
  chooseAnother: { en: 'Choose Another Game', si: 'වෙනත් ක්‍රීඩාවක් තෝරන්න' },
  menu: { en: '☰ Menu', si: 'මෙනුව' },
  // Hangman-specific (Milestone 4 §19). Draft Sinhala, same review caveat.
  solveForX: { en: 'Solve for x', si: 'x සඳහා විසඳන්න' },
  enterAnswer: { en: 'Enter your answer', si: 'ඔබේ පිළිතුර ඇතුළත් කරන්න' },
  submitAnswer: { en: 'Submit Answer', si: 'පිළිතුර යොමු කරන්න' },
  attemptsLeft: { en: 'Attempts Left', si: 'ඉතිරි උත්සාහයන්' },
  correctAnswerLabel: { en: 'Correct answer', si: 'නිවැරදි පිළිතුර' },
  questionFailed: { en: 'Question Failed', si: 'ප්‍රශ්නය අසාර්ථකයි' },
  questionsSolved: { en: 'Questions Solved', si: 'විසඳූ ප්‍රශ්න' },
  questionsFailed: { en: 'Questions Failed', si: 'අසාර්ථක ප්‍රශ්න' },
  // Session-level only (Milestone 4 session summary) — shown once, never
  // per question, and only when the figure never fell this session.
  neverFell: { en: "🎉 You didn't let him fall!", si: 'ඔබ ඔහුට වැටෙන්න ඉඩ දුන්නේ නැහැ!' },
  wrongAnswers: { en: 'Wrong Answers', si: 'වැරදි පිළිතුරු' },
  hintsUsed: { en: 'Hints Used', si: 'භාවිත කළ ඉඟි' },
  totalTime: { en: 'Total Time', si: 'මුළු කාලය' },
  starsEarned: { en: 'Stars Earned', si: 'ලබාගත් තරු' },
  tasks: { en: 'Tasks', si: 'කාර්යයන්' },
  successful: { en: 'Successful', si: 'සාර්ථක කාර්යයන්' },
  successRate: { en: 'Success Rate', si: 'සාර්ථකත්ව අනුපාතය' },
  completionRate: { en: 'Completion Rate', si: 'සම්පූර්ණ කිරීමේ අනුපාතය' },
  averageAttempts: { en: 'Average Attempts', si: 'සාමාන්‍ය උත්සාහ ගණන' },
  hintRate: { en: 'Hint Rate', si: 'ඉඟි භාවිත අනුපාතය' },
  retries: { en: 'Retries', si: 'නැවත උත්සාහ' },
  activeTime: { en: 'Active Time', si: 'ක්‍රියාකාරී කාලය' },
  levelsCompleted: { en: 'Levels Completed', si: 'සම්පූර්ණ කළ මට්ටම්' },
  saveUnverified: { en: 'Save unverified. Tap to retry.', si: 'සුරැකීම තහවුරු නැත. නැවත උත්සාහ කරන්න.' },
  retryingSave: { en: 'Retrying save…', si: 'නැවත සුරකිමින්…' },
} satisfies Record<string, Bilingual>

// Game Selection card text, keyed by GameType (draft Sinhala, same review
// caveat as above).
export const GAME_TYPE_TEXT: Record<
  'drag_drop' | 'hangman' | 'mystery_reveal',
  { name: Bilingual; description: Bilingual }
> = {
  drag_drop: {
    name: { en: 'Drag & Drop', si: 'ඇදගෙන දමන්න' },
    description: {
      en: 'Balance the equation.',
      si: 'සමීකරණය තුලනය කරන්න.',
    },
  },
  hangman: {
    name: { en: 'Hangman', si: 'හෑන්ග්මන්' },
    description: {
      en: 'Don\'t let the man fall.',
      si: 'වැටෙන්න නොදි තියාගන්න​.',
    },
  },
  mystery_reveal: {
    name: { en: 'Mystery Reveal', si: 'රහස් හෙළිදරව්ව' },
    description: {
      en: 'Solve the steps. Uncover the mystery.',
      si: 'පියවර විසඳන්න. රහස හෙළි කරන්න.',
    },
  },
}

type Difficulty = 'easy' | 'medium' | 'hard'

export function difficultyText(difficulty: Difficulty): Bilingual {
  return GAME_TEXT[difficulty]
}

// Primary language first; both remain visible.
export function inline(text: Bilingual): string {
  return formatGameLanguages(text, ' · ')
}

// Primary language on the first line.
export function stacked(text: Bilingual): string {
  return formatGameLanguages(text)
}

// DRAFT Sinhala for the per-step hint sentences in data/equationVariants.ts.
// Template-based, like the Tutor's sinhalaLessonText.ts: mathematical tokens
// (+3, ×2, x, numbers) are kept as they are. Returns null when no template
// matches, and the hint then shows in English only. Same review caveat as
// GAME_TEXT above: not reviewed by a native speaker or maths teacher.
const HINT_TEMPLATES: Array<[RegExp, (m: RegExpExecArray) => string]> = [
  [
    /^Use the opposite operation to remove (.+)\.$/,
    (m) => `${m[1]} ඉවත් කිරීමට ප්‍රතිවිරුද්ධ ක්‍රියාව භාවිතා කරන්න.`,
  ],
  [
    /^(\d+) is multiplying x\. Use the opposite operation\.$/,
    (m) => `${m[1]} x ගුණ කරයි. ප්‍රතිවිරුද්ධ ක්‍රියාව භාවිතා කරන්න.`,
  ],
  [
    /^x is divided by (\d+)\. Use the opposite operation\.$/,
    (m) => `x ${m[1]} න් බෙදා ඇත. ප්‍රතිවිරුද්ධ ක්‍රියාව භාවිතා කරන්න.`,
  ],
  [
    /^Remove the bracket by undoing the (.+) outside it first\.$/,
    (m) => `මුලින්ම වරහනට පිටතින් ඇති ${m[1]} ආපසු හරවා වරහන ඉවත් කරන්න.`,
  ],
  [/^Remove (.+) first\.$/, (m) => `මුලින්ම ${m[1]} ඉවත් කරන්න.`],
  [
    /^Now remove the multiplication by (\d+)\.$/,
    (m) => `දැන් ${m[1]} න් ගුණ කිරීම ඉවත් කරන්න.`,
  ],
  [/^Now remove (.+)\.$/, (m) => `දැන් ${m[1]} ඉවත් කරන්න.`],
  [
    /^Remove x from both sides to collect the variable on one side\.$/,
    () => 'විචල්‍යය එක් පසකට ගැනීමට දෙපසින්ම x ඉවත් කරන්න.',
  ],
  [
    /^Clear the fraction first by multiplying both sides by (\d+)\.$/,
    (m) => `මුලින්ම දෙපසම ${m[1]} න් ගුණ කර භාගය ඉවත් කරන්න.`,
  ],
  [
    /^A number increased by (\d+) gives (\d+) — remove (.+) from both sides\.$/,
    (m) => `සංඛ්‍යාවකට ${m[1]} ක් එකතු කළ විට ${m[2]} ලැබේ — දෙපසින්ම ${m[3]} ඉවත් කරන්න.`,
  ],
  [
    /^Double a number, then subtract (\d+), gives (\d+) — remove (.+) first\.$/,
    (m) => `සංඛ්‍යාවක් දෙගුණ කර ${m[1]} ක් අඩු කළ විට ${m[2]} ලැබේ — මුලින්ම ${m[3]} ඉවත් කරන්න.`,
  ],
]

export function sinhalaHint(english: string): string | null {
  for (const [pattern, build] of HINT_TEMPLATES) {
    const match = pattern.exec(english)
    if (match) return build(match)
  }
  return null
}

// Primary language first when a Sinhala hint template is available.
export function bilingualHint(english: string): string {
  const sinhala = sinhalaHint(english)
  return sinhala ? stacked({ en: english, si: sinhala }) : english
}
