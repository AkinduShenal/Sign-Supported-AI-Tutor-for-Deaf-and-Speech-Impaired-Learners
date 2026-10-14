/** Sinhala wording for the current lesson bank. Keep mathematical tokens intact. */
const sentences: Record<string, string> = {
  'An equation is like a balance. Perform the SAME operation on BOTH sides to keep them equal.': 'සමීකරණයක් තුලාවක් වගේ. දෙපස සමානව තබා ගැනීමට දෙපසටම එකම ගණිත ක්‍රියාව සිදු කරන්න.',
  'Identify x, the unknown variable. Both sides must have the same value.': 'නොදන්නා අගය නියෝජනය කරන විචල්‍යය වන x හඳුනාගන්න. දෙපසෙහි අගයන් සමාන විය යුතුය.',
  'Simplify each side. The equation remains balanced.': 'එක් එක් පස සරල කරන්න. සමීකරණයේ දෙපස තවමත් සමානයි.',
  'Simplify both sides.': 'දෙපසම සරල කරන්න.',
  'Solve the equation. The variable is now by itself.': 'සමීකරණය විසඳන්න. දැන් විචල්‍යය එක් පසක තනිව තිබෙනවා.',
  'Check both sides. They have the same value, so the solution satisfies the original equation.': 'දෙපසෙහි අගයන් පරීක්ෂා කරන්න. ඒවා සමාන නිසා මේ විසඳුම මුල් සමීකරණය සපුරාලනවා.',
  'Final answer.': 'අවසාන පිළිතුර.',
  'Multiply every term inside the bracket by the number outside.': 'වරහන තුළ ඇති සෑම පදයක්ම වරහනට පිටතින් ඇති සංඛ්‍යාවෙන් ගුණ කරන්න.',
  'Keep both sides equal. Aim to leave x by itself.': 'දෙපස සමානව තබා ගන්න. x එක් පසක තනි කිරීමට උත්සාහ කරන්න.',
  'Use an inverse operation on both sides.': 'දෙපසටම ප්‍රතිලෝම ගණිත ක්‍රියාවක් සිදු කරන්න.',
  'Correct. Substitute your value into the original equation to check it.': 'නිවැරදියි. ඔබ ලබාගත් අගය මුල් සමීකරණයට ආදේශ කර පරීක්ෂා කරන්න.',
  'Not yet. Use the next hint or review a worked example; apply each operation to both sides.': 'තවම නිවැරදි නැහැ. ඊළඟ ඉඟිය බලන්න හෝ විසඳන ලද උදාහරණයක් අධ්‍යයනය කරන්න. සෑම ගණිත ක්‍රියාවක්ම දෙපසටම සිදු කරන්න.',
  'Enter a number, fraction, or x = number (for example x = -5/2).': 'සංඛ්‍යාවක්, භාගයක් හෝ x = සංඛ්‍යාව ලෙස පිළිතුර ඇතුළත් කරන්න (උදාහරණයක් ලෙස x = -5/2).',
  'Think of a balance: changing only one side would break the equality. The operation must be the same on the left and right.': 'තුලාවක් ගැන සිතන්න. එක් පසක් පමණක් වෙනස් කළොත් සමානතාව නැති වෙනවා. වම් සහ දකුණු දෙපසටම එකම ගණිත ක්‍රියාව සිදු කළ යුතුයි.',
}

export function sinhalaLessonText(text: string): string | null {
  if (Object.hasOwn(sentences, text)) return sentences[text]
  let match = /^Solve (.+)\.$/.exec(text)
  if (match) return `${match[1]} සමීකරණය විසඳන්න.`
  match = /^Subtract (.+) from both sides(?: to keep the balance)?\.$/.exec(text)
  if (match) return `දෙපසින්ම ${match[1]} අඩු කරන්න.`
  match = /^Add (.+) to both sides\.$/.exec(text)
  if (match) return `දෙපසටම ${match[1]} එකතු කරන්න.`
  match = /^(Subtract|Add) (.+) on both sides to collect the variable terms\.$/.exec(text)
  if (match) return match[1] === 'Subtract'
    ? `විචල්‍ය පද එක් පසකට ගැනීමට දෙපසින්ම ${match[2]} අඩු කරන්න.`
    : `විචල්‍ය පද එක් පසකට ගැනීමට දෙපසටම ${match[2]} එකතු කරන්න.`
  match = /^Divide both sides by (.+)\.$/.exec(text)
  if (match) return `දෙපසම ${match[1]} න් බෙදන්න.`
  match = /^Substitute (.+) for x in the ORIGINAL equation shown above\.$/.exec(text)
  if (match) return `ඉහත දැක්වෙන මුල් සමීකරණයේ x වෙනුවට ${match[1]} ආදේශ කරන්න.`
  match = /^Multiply BOTH sides, including every term, by (.+) to remove the denominator\.$/.exec(text)
  if (match) return `හරය ඉවත් කිරීමට, සෑම පදයක්ම ඇතුළුව දෙපසම ${match[1]} න් ගුණ කරන්න.`
  match = /^After collecting terms: (.+)\. Divide both sides by (.+) if needed\.$/.exec(text)
  if (match) return `පද එක් පසකට ගත් පසු: ${match[1]}. අවශ්‍ය නම් දෙපසම ${match[2]} න් බෙදන්න.`
  return null
}
