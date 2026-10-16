import type { TeachingStrategy } from '../types/tutor'

interface TeachingApproach {
  title: string
  titleSi: string
  guidance: string
  guidanceSi: string
  practice: string
  practiceSi: string
}

export const TEACHING_APPROACHES: Record<TeachingStrategy, TeachingApproach> = {
  step_by_step: {
    title: 'step_by_step',
    titleSi: 'පියවරෙන් පියවර',
    guidance: 'Read one step, look at how the equation changes, then continue. At an operation step, check which sides must change.',
    guidanceSi: 'එක් පියවරක් කියවා සමීකරණය වෙනස් වන ආකාරය බලන්න. ඉන්පසු ඉදිරියට යන්න. ගණිත ක්‍රියාවක් සිදු කරන පියවරකදී වෙනස් කළ යුතු පැති හඳුනාගන්න.',
    practice: 'Use the same small steps from the example. Apply an operation, simplify, and check before moving on.',
    practiceSi: 'උදාහරණයේ කුඩා පියවරම භාවිත කරන්න. ගණිත ක්‍රියාව සිදු කර, සරල කර, ඉදිරියට යාමට පෙර පරීක්ෂා කරන්න.',
  },
  conceptual_explanation: {
    title: 'conceptual_explanation',
    titleSi: 'සංකල්පමය පැහැදිලි කිරීම',
    guidance: 'Why does this step preserve equality? Both sides represent the same value; apply the same operation to keep the balance.',
    guidanceSi: 'මේ පියවරෙන් සමානතාව රැකෙන්නේ ඇයි? දෙපස එකම අගය නියෝජනය කරන නිසා සමබරතාව රැකීමට දෙපසටම එකම ගණිත ක්‍රියාව සිදු කරන්න.',
    practice: 'Before calculating, explain why your chosen operation keeps both sides equal. Then solve and check.',
    practiceSi: 'ගණනය කිරීමට පෙර, තෝරාගත් ගණිත ක්‍රියාවෙන් දෙපස සමානව පවතින්නේ ඇයි කියා පැහැදිලි කරන්න. ඉන්පසු විසඳා පරීක්ෂා කරන්න.',
  },
  worked_example_based: {
    title: 'worked_example_based',
    titleSi: 'විසඳන ලද උදාහරණ මත පදනම් වූ ඉගෙනීම',
    guidance: 'Compare each equation with the previous step. Notice the operation and follow the full solution before trying a similar question.',
    guidanceSi: 'එක් එක් සමීකරණය පෙර පියවර සමඟ සසඳන්න. භාවිත කළ ගණිත ක්‍රියාව හඳුනාගෙන, සමාන ප්‍රශ්නයකට උත්සාහ කිරීමට පෙර සම්පූර්ණ විසඳුම අධ්‍යයනය කරන්න.',
    practice: 'Compare this question with the worked example. The numbers may differ, but you can use the same solving method.',
    practiceSi: 'මේ ප්‍රශ්නය විසඳන ලද උදාහරණය සමඟ සසඳන්න. සංඛ්‍යා වෙනස් වුවත් එකම විසඳීමේ ක්‍රමය භාවිත කළ හැකියි.',
  },
  progressive_hints: {
    title: 'progressive_hints',
    titleSi: 'ක්‍රමානුකූල ඉඟි',
    guidance: 'Use this example when you need a reference. Start with the practice question and reveal only as much help as you need.',
    guidanceSi: 'අවශ්‍ය විට මේ උදාහරණය බලන්න. පුහුණු ප්‍රශ්නයෙන් පටන්ගෙන ඔබට අවශ්‍ය ප්‍රමාණයට පමණක් ඉඟි බලන්න.',
    practice: 'Try first. Reveal one hint, try again, then ask for the next hint. After all three hints, you can open this question’s worked solution.',
    practiceSi: 'මුලින් උත්සාහ කරන්න. එක් ඉඟියක් බලා නැවත උත්සාහ කර, අවශ්‍ය නම් ඊළඟ ඉඟිය බලන්න. ඉඟි තුනම බැලූ පසු මේ ප්‍රශ්නයේ පියවර සහිත විසඳුම විවෘත කළ හැකියි.',
  },
  advanced_challenge: {
    title: 'advanced_challenge',
    titleSi: 'උසස් අභියෝගය',
    guidance: 'Use the example to compare methods after your own attempt. Explain each transformation and verify the final answer.',
    guidanceSi: 'ඔබේ උත්සාහයෙන් පසු ක්‍රම සසඳන්න මේ උදාහරණය භාවිත කරන්න. එක් එක් වෙනස්කිරීම පැහැදිලි කර අවසාන පිළිතුර පරීක්ෂා කරන්න.',
    practice: 'Choose your own method and solve independently. Explain your reasoning and substitute the answer into the original equation to verify it.',
    practiceSi: 'ඔබේම ක්‍රමයක් තෝරාගෙන තනිව විසඳන්න. ඔබේ හේතුව පැහැදිලි කර, මුල් සමීකරණයට පිළිතුර ආදේශ කර පරීක්ෂා කරන්න.',
  },
}
