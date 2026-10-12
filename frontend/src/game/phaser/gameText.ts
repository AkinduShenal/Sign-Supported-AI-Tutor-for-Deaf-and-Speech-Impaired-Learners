// Bilingual (English + Sinhala) UI labels for the live Phaser game.
//
// DRAFT: the Sinhala below has NOT been reviewed by a native speaker or a
// Sinhala maths teacher. Reuse the wording from the old prototype strings
// (game/i18n/uiStrings.ts) and the Tutor (components/sinhalaLessonText.ts)
// where it overlaps, and get it reviewed before any learner or research
// use. Never describe it as validated.
//
// Both languages are always shown together (no toggle) so the text stays
// visible and nothing depends on finding a switch first. The analytics
// detail lines and the per-step hint sentences are still English-only.

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
  chooseGame: { en: 'Choose Your Game', si: 'ඔබේ ක්‍රීඩාව තෝරන්න' },
  play: { en: 'Play', si: 'ක්‍රීඩා කරන්න' },
  comingNext: { en: 'Coming next', si: 'ඉක්මනින්' },
  chooseAnother: { en: 'Choose Another Game', si: 'වෙනත් ක්‍රීඩාවක් තෝරන්න' },
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
      en: 'Move operations. Balance the equation.',
      si: 'ක්‍රියා ගෙන යන්න. සමීකරණය තුලනය කරන්න.',
    },
  },
  hangman: {
    name: { en: 'Hangman', si: 'හෑන්ග්මන්' },
    description: {
      en: 'Solve the equation before the figure is complete.',
      si: 'රූපය සම්පූර්ණ වීමට පෙර සමීකරණය විසඳන්න.',
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

// "English · සිංහල" on one line, for places with room for it.
export function inline(text: Bilingual): string {
  return `${text.en} · ${text.si}`
}

// "English\nසිංහල" on two lines.
export function stacked(text: Bilingual): string {
  return `${text.en}\n${text.si}`
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

// English hint with the draft Sinhala under it (English only if no template).
export function bilingualHint(english: string): string {
  const sinhala = sinhalaHint(english)
  return sinhala ? `${english}\n${sinhala}` : english
}
