import type { QuizDiagnosticResult, QuizLanguage } from './types'

type Localized = { en: string; si: string }

const levels: Record<QuizDiagnosticResult['mastery_level'], Localized> = {
  high: { en: 'Strong', si: 'ශක්තිමත්' },
  medium: { en: 'Developing', si: 'වර්ධනය වෙමින් පවතී' },
  low: { en: 'Needs Support', si: 'සහාය අවශ්‍යයි' },
}

const support: Record<QuizDiagnosticResult['recommended_support_level'], Localized> = {
  low: { en: 'Low', si: 'අඩු' },
  medium: { en: 'Medium', si: 'මධ්‍යම' },
  high: { en: 'High', si: 'ඉහළ' },
}

const areas: Record<string, Localized> = {
  one_step_addition: { en: 'One-step Addition', si: 'එක් පියවරක එකතු කිරීම' },
  one_step_subtraction: { en: 'One-step Subtraction', si: 'එක් පියවරක අඩු කිරීම' },
  one_step_multiplication: { en: 'One-step Multiplication', si: 'එක් පියවරක ගුණ කිරීම' },
  one_step_division: { en: 'One-step Division', si: 'එක් පියවරක බෙදීම' },
  two_step_equations: { en: 'Two-step Equations', si: 'පියවර දෙකක සමීකරණ' },
  variables_both_sides: { en: 'Variables on Both Sides', si: 'දෙපසම විචල්‍ය ඇති සමීකරණ' },
  distributive_equations: { en: 'Equations with Brackets', si: 'වරහන් සහිත සමීකරණ' },
}

const focusByText: Record<string, Localized> = {
  ...Object.fromEntries(Object.values(areas).map(value => [value.en, value])),
  'Inverse Operations': { en: 'Inverse Operations', si: 'ප්‍රතිලෝම ගණිත ක්‍රියා' },
  'Signs in Equations': { en: 'Signs in Equations', si: 'සමීකරණවල ලකුණු' },
  'Arithmetic Steps': { en: 'Arithmetic Steps', si: 'ගණිතමය පියවර' },
  'Equation Meaning': { en: 'Equation Meaning', si: 'සමීකරණයේ අර්ථය' },
  'Linear Equation Steps': { en: 'Linear Equation Steps', si: 'රේඛීය සමීකරණ පියවර' },
  'Continue Linear Equation Practice': { en: 'Continue Linear Equation Practice', si: 'රේඛීය සමීකරණ අභ්‍යාස දිගටම කරගෙන යන්න' },
}

export function presentResult(result: QuizDiagnosticResult, language: QuizLanguage) {
  const pick = (value: Localized) => language === 'si' ? value.si : value.en
  return {
    score: `${result.correct_answers} / ${result.questions_total}`,
    correctAnswers: result.correct_answers,
    wrongAnswers: result.questions_attempted - result.correct_answers,
    level: pick(levels[result.mastery_level]),
    practice: pick(result.weak_subconcept
      ? areas[result.weak_subconcept] ?? { en: 'Linear Equation Steps', si: 'රේඛීය සමීකරණ පියවර' }
      : { en: 'No clear area identified', si: 'විශේෂ අවධානයක් අවශ්‍ය ප්‍රදේශයක් හඳුනාගෙන නැත' }),
    focus: pick(focusByText[result.recommended_focus ?? '']
      ?? { en: 'Linear Equation Steps', si: 'රේඛීය සමීකරණ පියවර' }),
    support: pick(support[result.recommended_support_level]),
  }
}

export function presentConfidenceInsight(result: QuizDiagnosticResult, language: QuizLanguage): string {
  const { kind, high_confidence_incorrect_count: highWrong, low_confidence_correct_count: lowRight } = result.confidence_insight
  const highMessage = language === 'si'
    ? `වැරදි පිළිතුරු ${highWrong}කට ඔබ ඉතා විශ්වාසයෙන් පිළිතුරු දී ඇත. මෙම ප්‍රදේශය තවදුරටත් පුහුණු කිරීම සුදුසුය.`
    : `You were very confident on ${highWrong} incorrect ${highWrong === 1 ? 'answer' : 'answers'}. More practice may help you review this area.`
  const lowMessage = language === 'si'
    ? `ඔබ ප්‍රශ්න ${lowRight}කට නිවැරදිව පිළිතුරු දුන්නද විශ්වාසය අඩු විය. තවත් පුහුණුව ඔබේ විශ්වාසය ශක්තිමත් කිරීමට උපකාරී වේ.`
    : `You answered ${lowRight} ${lowRight === 1 ? 'question' : 'questions'} correctly but with low confidence. More practice may help strengthen your confidence.`
  if (kind === 'mixed') return `${highMessage} ${lowMessage}`
  if (kind === 'high_incorrect') return highMessage
  if (kind === 'low_correct') return lowMessage
  return language === 'si'
    ? 'ඔබේ පිළිතුරු සහ විශ්වාස මට්ටම පිළිබඳ සාරාංශය සකස් කර ඇත. දිගටම පුහුණු වන්න.'
    : 'Your answers and confidence levels have been reviewed. Keep practicing.'
}
