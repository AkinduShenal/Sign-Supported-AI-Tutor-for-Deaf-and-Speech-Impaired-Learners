import type { QuizDiagnosticResult, QuizLanguage } from './types'

type Localized = { en: string; si: string }

const understanding: Record<QuizDiagnosticResult['mastery_level'], Localized> = {
  high: { en: 'Strong Understanding', si: 'හොඳ අවබෝධයක්' },
  medium: { en: 'Developing Understanding', si: 'වර්ධනය වෙමින් පවතින අවබෝධයක්' },
  low: { en: 'Needs More Practice', si: 'තවත් පුහුණුව අවශ්‍යයි' },
}

// Only codes in the current question bank are shown to learners.
const areas: Record<string, Localized> = {
  one_step_addition: { en: 'One-step Addition', si: 'එක් පියවරක එකතු කිරීම' },
  one_step_subtraction: { en: 'One-step Subtraction', si: 'එක් පියවරක අඩු කිරීම' },
  one_step_multiplication: { en: 'One-step Multiplication', si: 'එක් පියවරක ගුණ කිරීම' },
  one_step_division: { en: 'One-step Division', si: 'එක් පියවරක බෙදීම' },
  two_step_equations: { en: 'Two-step Equations', si: 'පියවර දෙකක සමීකරණ' },
  variables_both_sides: { en: 'Variables on Both Sides', si: 'දෙපසම විචල්‍ය ඇති සමීකරණ' },
  distributive_equations: { en: 'Equations with Brackets', si: 'වරහන් සහිත සමීකරණ' },
}

const focusByArea: Record<string, Localized> = {
  one_step_addition: { en: 'Practising addition when solving one-step equations', si: 'එක් පියවරක සමීකරණ විසඳීමේදී එකතු කිරීම පුහුණු කරන්න.' },
  one_step_subtraction: { en: 'Practising subtraction when solving one-step equations', si: 'එක් පියවරක සමීකරණ විසඳීමේදී අඩු කිරීම පුහුණු කරන්න.' },
  one_step_multiplication: { en: 'Practising multiplication when solving one-step equations', si: 'එක් පියවරක සමීකරණ විසඳීමේදී ගුණ කිරීම පුහුණු කරන්න.' },
  one_step_division: { en: 'Practising division when solving one-step equations', si: 'එක් පියවරක සමීකරණ විසඳීමේදී බෙදීම පුහුණු කරන්න.' },
  two_step_equations: { en: 'Practising how to solve two-step equations', si: 'පියවර දෙකක සමීකරණ විසඳන ආකාරය පුහුණු කරන්න.' },
  variables_both_sides: { en: 'Practising equations with variables on both sides', si: 'දෙපසම විචල්‍ය ඇති සමීකරණ විසඳීම පුහුණු කරන්න.' },
  distributive_equations: { en: 'Practising equations with brackets', si: 'වරහන් සහිත සමීකරණ විසඳීම පුහුණු කරන්න.' },
}
const focusByBackendLabel: Record<string, Localized> = Object.fromEntries(
  Object.entries(areas).map(([code, value]) => [value.en, focusByArea[code]]),
)

const noSingleArea: Localized = {
  en: 'No single weak area identified',
  si: 'විශේෂිත දුර්වල ප්‍රදේශයක් හඳුනාගෙන නැත',
}
const generalFocus: Localized = {
  en: 'Continue practising all Linear Equation skills.',
  si: 'රේඛීය සමීකරණවල සියලුම කුසලතා දිගටම පුහුණු කරන්න.',
}

export function presentResult(result: QuizDiagnosticResult, language: QuizLanguage) {
  const pick = (value: Localized) => language === 'si' ? value.si : value.en
  const weak = result.weak_subconcept
  // The backend selects the weak area. Use that same conclusion for both
  // learner-facing rows, including older saved results with a conflicting focus.
  const supportedArea = weak ? areas[weak] : undefined
  const focusLabel = supportedArea
    ? result.recommended_focus === supportedArea.en ? result.recommended_focus : supportedArea.en
    : null
  return {
    score: `${result.correct_answers} / ${result.questions_total}`,
    correctAnswers: result.correct_answers,
    wrongAnswers: result.questions_attempted - result.correct_answers,
    level: pick(understanding[result.mastery_level]),
    practice: pick(supportedArea ?? noSingleArea),
    focus: pick(focusLabel ? focusByBackendLabel[focusLabel] ?? generalFocus : generalFocus),
  }
}

export function presentConfidenceInsight(result: QuizDiagnosticResult, language: QuizLanguage): string {
  const { kind, high_confidence_incorrect_count: highWrong, low_confidence_correct_count: lowRight } = result.confidence_insight
  const highMessage = language === 'si'
    ? `වැරදි පිළිතුරු ${highWrong}කට ඔබ ඉහළ විශ්වාසයකින් පිළිතුරු ලබා දී ඇත. එම ප්‍රදේශ තවදුරටත් සමාලෝචනය කර පුහුණු කිරීම සුදුසුය.`
    : `You were highly confident on ${highWrong} incorrect ${highWrong === 1 ? 'answer' : 'answers'}. These areas may need further review.`
  const lowMessage = language === 'si'
    ? `ඔබ ප්‍රශ්න ${lowRight}කට නිවැරදිව පිළිතුරු ලබා දී තිබුණද, එම පිළිතුරු පිළිබඳ ඔබගේ විශ්වාසය අඩු විය. තවත් පුහුණුවෙන් ඔබගේ විශ්වාසය වැඩි කර ගත හැක.`
    : `You answered ${lowRight} ${lowRight === 1 ? 'question' : 'questions'} correctly but with low confidence. More practice may help strengthen your confidence.`
  if (kind === 'mixed') return `${highMessage} ${lowMessage}`
  if (kind === 'high_incorrect') return highMessage
  if (kind === 'low_correct') return lowMessage
  return language === 'si'
    ? 'ඔබගේ පිළිතුරු සහ විශ්වාස මට්ටම පිළිබඳ සාරාංශය සකස් කර ඇත. දිගටම පුහුණු වන්න.'
    : 'Your answers and confidence levels have been reviewed. Keep practicing.'
}
