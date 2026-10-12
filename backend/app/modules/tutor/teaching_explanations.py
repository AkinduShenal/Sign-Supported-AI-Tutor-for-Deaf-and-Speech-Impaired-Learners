"""Teacher-reviewable bilingual reasoning, using existing key-term gestures.

These are educational cues, not SLSL sentence translations. Equation values
always come from the checked lesson bank; this module never invents motion.
"""

import re
from collections.abc import Callable

from app.modules.tutor.content_schemas import AvatarTeachingSegment, LessonStep
from app.modules.tutor.schemas import TutoringStrategy

TeachingLine = tuple[str, str]

STRATEGY_OPENINGS: dict[TutoringStrategy, list[TeachingLine]] = {
    TutoringStrategy.STEP_BY_STEP: [
        ("Start with the equation. x stands for a number we do not know yet.", "සමීකරණයෙන් පටන් ගමු. x නියෝජනය කරන්නේ අපි තවම නොදන්නා සංඛ්‍යාවක්."),
        ("Work step by step. Undo one operation at a time, applying it to both sides.", "පියවරෙන් පියවර වැඩ කරමු. එක් වරකට එක් ගණිත ක්‍රියාවක් ප්‍රතිලෝම ක්‍රියාවෙන් ඉවත් කරමු. එය දෙපසටම සිදු කරමු."),
        ("Check the answer by substitution in the original equation.", "මුල් සමීකරණයට පිළිතුර ආදේශ කර පරීක්ෂා කරමු."),
    ],
    TutoringStrategy.CONCEPTUAL_EXPLANATION: [
        ("An equation says that the left and right sides have the same value.", "සමීකරණයකින් කියවෙන්නේ වම් සහ දකුණු දෙපසෙහි අගයන් සමාන බවයි."),
        ("Think of a balanced scale. Changing only one side would break the balance.", "සමබර තුලාවක් ගැන සිතන්න. එක් පසක් පමණක් වෙනස් කළොත් සමබරතාව නැති වෙනවා."),
        ("Apply the same operation to both sides. The equality is preserved while we isolate x.", "දෙපසටම එකම ගණිත ක්‍රියාව සිදු කරන්න. එවිට x තනි කරන අතරතුර සමානතාව රැකෙනවා."),
    ],
    TutoringStrategy.WORKED_EXAMPLE_BASED: [
        ("Read the original equation in this example. Identify the variable and the operations around it.", "මේ උදාහරණයේ මුල් සමීකරණය කියවන්න. විචල්‍යය සහ ඒ සමඟ ඇති ගණිත ක්‍රියා හඳුනාගන්න."),
        ("Follow the example one step at a time. Compare the equation before and after each operation.", "උදාහරණයේ එක් පියවරක් බැගින් අධ්‍යයනය කරන්න. එක් එක් ගණිත ක්‍රියාවට පෙර සහ පසු සමීකරණය සසඳන්න."),
        ("Check the solved example, then use the same method in a practice question.", "විසඳන ලද උදාහරණය පරීක්ෂා කර, ඉන්පසු එම ක්‍රමයම පුහුණු ප්‍රශ්නයකට යොදන්න."),
    ],
    TutoringStrategy.PROGRESSIVE_HINTS: [
        ("Start with the practice question. Try to solve it before opening a hint.", "පුහුණු ප්‍රශ්නයෙන් පටන් ගන්න. ඉඟියක් බැලීමට පෙර එය විසඳීමට උත්සාහ කරන්න."),
        ("If you need a hint, first identify the goal: leave the variable x by itself.", "ඉඟියක් අවශ්‍ය නම්, මුලින් අරමුණ හඳුනාගන්න: විචල්‍යය වන x එක් පසක තනි කිරීම."),
        ("Reveal the next hint only when you need it. Apply the suggested operation to both sides and try again.", "අවශ්‍ය නම් පමණක් ඊළඟ ඉඟිය බලන්න. යෝජිත ගණිත ක්‍රියාව දෙපසටම සිදු කර නැවත උත්සාහ කරන්න."),
    ],
    TutoringStrategy.ADVANCED_CHALLENGE: [
        ("Read the challenge equation. Decide which terms to collect and which operation to undo first.", "අභියෝග සමීකරණය කියවන්න. එකතු කළ යුතු පද සහ මුලින් ඉවත් කළ යුතු ගණිත ක්‍රියාව තීරණය කරන්න."),
        ("Solve independently, keeping both sides equal at every transformation.", "සෑම වෙනස්කිරීමකදීම දෙපස සමානව තබාගෙන තනිව විසඳන්න."),
        ("Explain your method and check the answer by substitution. Use an example or hint if needed.", "ඔබේ ක්‍රමය පැහැදිලි කර පිළිතුර ආදේශ කර පරීක්ෂා කරන්න. අවශ්‍ය නම් උදාහරණයක් හෝ ඉඟියක් බලන්න."),
    ],
}


def segments_from_lines(
    lines: list[TeachingLine], actions: Callable[[str], list[str]],
    expression: str | None = None,
) -> list[AvatarTeachingSegment]:
    return [AvatarTeachingSegment(text=en, text_si=si, expression=expression,
                                 sign_actions=actions(en)) for en, si in lines]


def _reason(instruction: str) -> TeachingLine:
    match = re.match(r"(Subtract|Add) (.+?) (?:from|to|on) both sides", instruction)
    if match:
        operation, amount = match.groups()
        if operation == "Subtract":
            return (
                f"Subtracting {amount} on both sides undoes the matching addition. Both sides lose the same amount, so equality is preserved.",
                f"දෙපසින්ම {amount} අඩු කිරීමෙන් ඊට අදාළ එකතු කිරීම ඉවත් වෙනවා. දෙපසින්ම එකම ප්‍රමාණය අඩු වන නිසා සමානතාව රැකෙනවා.",
            )
        return (
            f"Adding {amount} to both sides undoes the matching subtraction. Both sides gain the same amount, so equality is preserved.",
            f"දෙපසටම {amount} එකතු කිරීමෙන් ඊට අදාළ අඩු කිරීම ඉවත් වෙනවා. දෙපසටම එකම ප්‍රමාණය එකතු වන නිසා සමානතාව රැකෙනවා.",
        )
    match = re.match(r"Divide both sides by (.+)\.", instruction)
    if match:
        divisor = match.group(1)
        return (
            f"The coefficient multiplies x. Divide both sides by {divisor} to undo that multiplication and leave x by itself.",
            f"සංගුණකය x ගුණ කරනවා. එම ගුණ කිරීම ඉවත් කර x තනි කිරීමට දෙපසම {divisor} න් බෙදන්න.",
        )
    if "inside the bracket" in instruction:
        return (
            "Multiplication distributes over every term in the bracket. Expand every term before collecting terms; this changes the form, not the value.",
            "ගුණ කිරීම වරහන තුළ ඇති සෑම පදයකටම යොදන්න. පද එක් පසකට ගැනීමට පෙර සියලු පද විහිදුවන්න. මෙයින් වෙනස් වන්නේ ලියන ආකාරය මිස අගය නොවේ.",
        )
    if "remove the denominator" in instruction:
        return (
            "Multiply every term on both sides, including the constant terms. Multiplying only the fraction would change the equation.",
            "නියත පද ඇතුළුව දෙපසෙහි ඇති සෑම පදයක්ම ගුණ කරන්න. භාගය පමණක් ගුණ කළොත් සමීකරණය වෙනස් වෙනවා.",
        )
    if instruction.startswith("Identify"):
        return ("The variable x is an unknown number. Our goal is to find a value that makes the original equation true.", "විචල්‍යය වන x නොදන්නා සංඛ්‍යාවක්. අපේ අරමුණ මුල් සමීකරණය සත්‍ය කරන අගයක් සොයා ගැනීමයි.")
    if instruction.startswith("Simplify"):
        return ("Simplify the arithmetic on each side. The operation was already applied to both sides, so the balance is preserved.", "එක් එක් පසෙහි ගණනය සරල කරන්න. ගණිත ක්‍රියාව දැනටමත් දෙපසටම සිදු කර ඇති නිසා සමබරතාව රැකෙනවා.")
    if instruction.startswith("Substitute"):
        return ("Substitution means replacing every x in the original equation with the answer. Calculate the left and right sides separately.", "ආදේශ කිරීම යනු මුල් සමීකරණයේ ඇති සෑම x වෙනුවටම පිළිතුර යෙදීමයි. වම් සහ දකුණු දෙපස වෙන වෙනම ගණනය කරන්න.")
    if instruction.startswith("Check"):
        return ("Compare the two calculated values. Equal values confirm that the answer satisfies the original equation.", "ගණනය කළ අගයන් දෙක සසඳන්න. ඒවා සමාන නම් පිළිතුර මුල් සමීකරණය සපුරාලන බව තහවුරු වෙනවා.")
    return ("The variable is now isolated. Check this answer in the original equation before finishing.", "දැන් විචල්‍යය තනිව තිබෙනවා. අවසන් කිරීමට පෙර මේ පිළිතුර මුල් සමීකරණයට ආදේශ කර පරීක්ෂා කරන්න.")


def explain_step(
    step: LessonStep, strategy: TutoringStrategy, actions: Callable[[str], list[str]],
) -> list[AvatarTeachingSegment]:
    core = AvatarTeachingSegment(text=step.instruction, expression=step.expression,
                                 sign_actions=list(step.sign_actions))
    reasoning = segments_from_lines([_reason(step.instruction)], actions, step.expression)
    if strategy == TutoringStrategy.CONCEPTUAL_EXPLANATION:
        return reasoning + [core] + segments_from_lines([
            ("Why is the equation still balanced? Describe what happened to both sides.", "සමීකරණය තවම සමබර වන්නේ ඇයි? දෙපසට සිදු වූ දේ පැහැදිලි කරන්න."),
        ], actions, step.expression)
    if strategy == TutoringStrategy.WORKED_EXAMPLE_BASED:
        return [core] + reasoning + segments_from_lines([
            ("Compare this step with the previous equation in the example. Use the same operation in your practice question when appropriate.", "මේ පියවර උදාහරණයේ පෙර සමීකරණය සමඟ සසඳන්න. සුදුසු අවස්ථාවක ඔබේ පුහුණු ප්‍රශ්නයටත් එම ගණිත ක්‍රියාව යොදන්න."),
        ], actions, step.expression)
    if strategy == TutoringStrategy.STEP_BY_STEP:
        return [core] + reasoning + segments_from_lines([
            ("Check this step before moving to the next step. Read the equation and confirm the change on both sides.", "ඊළඟ පියවරට යාමට පෙර මේ පියවර පරීක්ෂා කරන්න. සමීකරණය කියවා දෙපසෙහි වෙනස තහවුරු කරන්න."),
        ], actions, step.expression)
    # References stay concise for learners who are trying independently.
    return [core] + reasoning
