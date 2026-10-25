import type { Bilingual } from './gameText'

// Shown by createResultsLoadingCard() (theme/gameUi.ts) while the backend
// calculates the session result — the one moment both Game scenes make the
// learner wait on the network with nothing else to look at. Short, general
// linear-equation strategy reminders, not tied to any one variant, so the
// same set works for both Drag & Drop and Hangman.
//
// DRAFT: the Sinhala below has not been reviewed by a native speaker or a
// Sinhala maths teacher — same caveat as every other line in gameText.ts.
export const LOADING_TIPS: Bilingual[] = [
  { en: 'Keep it balanced - do the same thing to both sides.', si: 'සමතුලිතව තබන්න - දෙපැත්තටම එකම දේ කරන්න.' },
  { en: 'To undo +, use −. To undo −, use +.', si: '+ ඉවත් කිරීමට − භාවිත කරන්න. − ඉවත් කිරීමට + භාවිත කරන්න.' },
  { en: 'To undo ×, use ÷. To undo ÷, use ×.', si: '× ඉවත් කිරීමට ÷ භාවිත කරන්න. ÷ ඉවත් කිරීමට × භාවිත කරන්න.' },
  { en: 'Work one step at a time - no need to rush.', si: 'වරකට එක් පියවරක් කරන්න - ඉක්මන් වීමට අවශ්‍ය නැත.' },
  { en: 'Check your answer - put it back into the equation.', si: 'ඔබේ පිළිතුර පරීක්ෂා කරන්න - එය සමීකරණයට නැවත ආදේශ කරන්න.' },
  { en: "Watch the negative signs - they're easy to miss.", si: 'සෘණ ලකුණු දෙස බලන්න - ඒවා මග හැරීම පහසුයි.' },
  { en: 'Collect the x terms on one side first.', si: 'මුලින්ම x පද එක් පැත්තකට රැස් කරන්න.' },
]
