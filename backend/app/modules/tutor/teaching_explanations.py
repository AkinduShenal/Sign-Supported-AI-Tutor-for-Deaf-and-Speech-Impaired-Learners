"""Small bilingual teaching ideas paired with same-rig educational cues.

Pairings are authored together: English and Sinhala are never independently
split or translated by word matching. These are review-only topic cues, not
SLSL sentence translations. Numeric instructions come from the checked bank.
"""

import re
from collections.abc import Callable

from app.modules.tutor.content_schemas import AvatarTeachingSegment, LessonStep
from app.modules.tutor.schemas import TutoringStrategy

TeachingLine = tuple[str, str] | tuple[str, str, tuple[str, ...]]


def cue(en: str, si: str, *signs: str) -> TeachingLine:
    return en, si, signs


BALANCE = cue("An equation is like a balanced scale.", "සමීකරණයක් සමබර තුලාවක් වගේ.", "CUE_EQUATION_BALANCE")
EQUALITY = cue("Both sides have the same value.", "දෙපසෙහි අගයන් සමානයි.", "CUE_EQUAL_SIDES")
UNKNOWN = cue("x represents a number we do not know yet.", "x නියෝජනය කරන්නේ අපි තවම නොදන්නා සංඛ්‍යාවක්.", "VARIABLE")
SMALL_STEP = cue("Work through one small step at a time.", "එක් වරකට එක් කුඩා පියවරක් බැගින් වැඩ කරමු.", "STEP")
SAME_OPERATION = cue("Apply the same operation to both sides.", "දෙපසටම එකම ගණිත ක්‍රියාව සිදු කරමු.", "BOTH_SIDES")
ISOLATE = cue("Our goal is to leave x by itself on one side.", "අපේ අරමුණ x එක් පසක තනි කිරීමයි.", "CUE_ISOLATE_VARIABLE")
SUBSTITUTE = cue("Put the answer in place of x in the original equation.", "මුල් සමීකරණයේ x වෙනුවට පිළිතුර ආදේශ කරමු.", "CUE_SUBSTITUTE_ANSWER")
VERIFY = cue("Check that the two sides have the same value.", "දෙපසෙහි අගයන් සමානදැයි පරීක්ෂා කරමු.", "CUE_VERIFY_EQUALITY")

STRATEGY_OPENINGS: dict[TutoringStrategy, list[TeachingLine]] = {
    TutoringStrategy.STEP_BY_STEP: [
        BALANCE, EQUALITY, UNKNOWN, SMALL_STEP, SAME_OPERATION, ISOLATE, SUBSTITUTE, VERIFY,
    ],
    TutoringStrategy.CONCEPTUAL_EXPLANATION: [
        BALANCE, EQUALITY,
        cue("Changing only one side can break the balance.", "එක් පසක් පමණක් වෙනස් කළොත් සමබරතාව නැති විය හැකියි.", "BALANCE"),
        SAME_OPERATION,
        cue("The equation stays balanced as we solve it.", "සමීකරණය විසඳන අතරතුර සමබරතාව රැකෙනවා.", "CUE_EQUAL_SIDES"),
        UNKNOWN, ISOLATE, VERIFY,
    ],
    TutoringStrategy.WORKED_EXAMPLE_BASED: [
        cue("Read the original equation in this example.", "මේ උදාහරණයේ මුල් සමීකරණය කියවන්න.", "EQUATION"),
        UNKNOWN,
        cue("Identify the operations around x.", "x සමඟ ඇති ගණිත ක්‍රියා හඳුනාගන්න.", "VARIABLE"),
        SMALL_STEP,
        cue("Compare the equation before and after this step.", "මේ පියවරට පෙර සහ පසු සමීකරණය සසඳන්න.", "EQUATION"),
        SAME_OPERATION, SUBSTITUTE, VERIFY,
        cue("Use the same method in a similar practice question.", "සමාන පුහුණු ප්‍රශ්නයකටත් එම ක්‍රමයම යොදන්න.", "PRACTICE"),
    ],
    TutoringStrategy.PROGRESSIVE_HINTS: [
        cue("Try the practice question yourself first.", "මුලින් පුහුණු ප්‍රශ්නය තනිව විසඳීමට උත්සාහ කරන්න.", "PRACTICE"),
        UNKNOWN, ISOLATE,
        cue("Open a hint only when you need help.", "උදව් අවශ්‍ය විට පමණක් ඉඟියක් බලන්න.", "HINT"),
        SMALL_STEP, SAME_OPERATION,
        cue("Try again before asking for the next hint.", "ඊළඟ ඉඟිය ඉල්ලීමට පෙර නැවත උත්සාහ කරන්න.", "TRY_AGAIN"),
    ],
    TutoringStrategy.ADVANCED_CHALLENGE: [
        cue("Read the challenge equation.", "අභියෝග සමීකරණය කියවන්න.", "EQUATION"),
        cue("Decide which operation to undo first.", "මුලින් ඉවත් කළ යුතු ගණිත ක්‍රියාව තීරණය කරන්න.", "SOLVE"),
        cue("Collect variable terms on one side when needed.", "අවශ්‍ය විට විචල්‍ය පද එක් පසකට ගන්න.", "CUE_COLLECT_VARIABLE"),
        cue("Solve independently and justify each step.", "තනිව විසඳා එක් එක් පියවරේ හේතුව පැහැදිලි කරන්න.", "SOLVE"),
        SAME_OPERATION, SUBSTITUTE, VERIFY,
    ],
}


def segments_from_lines(
    lines: list[TeachingLine], actions: Callable[[str], list[str]],
    expression: str | None = None,
) -> list[AvatarTeachingSegment]:
    return [AvatarTeachingSegment(
        text=line[0], text_si=line[1], expression=expression,
        sign_actions=list(line[2]) if len(line) == 3 else actions(line[0]),
    ) for line in lines]


def _core_parts(step: LessonStep) -> list[AvatarTeachingSegment]:
    """Shorten known bank instructions without changing the checked math."""
    instruction = step.instruction
    if instruction.startswith("Identify"):
        lines = [UNKNOWN, EQUALITY]
    elif instruction.startswith("Check"):
        lines = [
            cue("Compare the calculated values on both sides.", "දෙපසින් ගණනය කළ අගයන් සසඳන්න.", "BOTH_SIDES"),
            EQUALITY,
            cue("This confirms the solution satisfies the original equation.", "මෙයින් පිළිතුර මුල් සමීකරණය සපුරාලන බව තහවුරු වෙනවා.", "CUE_VERIFY_EQUALITY"),
        ]
    elif instruction.startswith("Solve"):
        lines = [cue("x is now by itself.", "දැන් x තනිව තිබෙනවා.", "CUE_ISOLATE_VARIABLE")]
    elif instruction.startswith("Simplify"):
        lines = [cue("Simplify the calculation on each side.", "එක් එක් පසෙහි ගණනය සරල කරන්න.", *step.sign_actions)]
    else:
        # Exact operation/amount cues survive, including unsupported-number
        # filtering in the planner. Do not invent number or negative gestures.
        text_si = None
        operation = re.match(r"(Subtract|Add) (.+?) (?:from|to|on) both sides", instruction)
        divide = re.match(r"Divide both sides by (.+)\.", instruction)
        substitute = re.match(r"Substitute (.+?) for x", instruction)
        denominator = re.match(r"Multiply BOTH sides, including every term, by (.+?) to remove", instruction)
        if operation:
            verb, amount = operation.groups()
            text_si = f"දෙපසින්ම {amount} අඩු කරන්න." if verb == "Subtract" else f"දෙපසටම {amount} එකතු කරන්න."
            if "collect the variable terms" in instruction:
                text_si += " විචල්‍ය පද එක් පසකට ගන්න."
        elif divide:
            text_si = f"දෙපසම {divide.group(1)} න් බෙදන්න."
        elif substitute:
            text_si = f"මුල් සමීකරණයේ x වෙනුවට {substitute.group(1)} ආදේශ කරන්න."
        elif denominator:
            text_si = f"හරය ඉවත් කිරීමට දෙපසෙහි ඇති සෑම පදයක්ම {denominator.group(1)} න් ගුණ කරන්න."
        elif "inside the bracket" in instruction:
            text_si = "වරහන තුළ ඇති සෑම පදයක්ම පිටත ඇති සංඛ්‍යාවෙන් ගුණ කරන්න."
        elif instruction == "Final answer.":
            text_si = "අවසන් පිළිතුර."
        return [AvatarTeachingSegment(text=instruction, expression=step.expression,
                                      text_si=text_si,
                                      sign_actions=list(step.sign_actions))]
    return segments_from_lines(lines, lambda _: [], step.expression)


def _reason_parts(instruction: str) -> list[TeachingLine]:
    if "collect the variable terms" in instruction:
        return [
            cue("Use the same variable term on both sides.", "දෙපසටම එකම විචල්‍ය පදය යොදන්න.", "CUE_COLLECT_VARIABLE"),
            cue("The remaining x terms can now be collected on one side.", "ඉතිරි x පද දැන් එක් පසකට ගත හැකියි.", "CUE_ISOLATE_VARIABLE"),
            EQUALITY,
        ]
    match = re.match(r"(Subtract|Add) (.+?) (?:from|to|on) both sides", instruction)
    if match:
        operation, amount = match.groups()
        if operation == "Subtract":
            return [
                cue(f"Subtracting {amount} undoes the matching addition.", f"{amount} අඩු කිරීමෙන් ඊට අදාළ එකතු කිරීම ඉවත් වෙනවා.", "CUE_INVERSE_ADDITION"),
                cue(f"Both sides lose the same amount: {amount}.", f"දෙපසින්ම එකම ප්‍රමාණය වන {amount} අඩු වෙනවා.", "CUE_SUBTRACT_BOTH"),
                EQUALITY,
            ]
        return [
            cue(f"Adding {amount} undoes the matching subtraction.", f"{amount} එකතු කිරීමෙන් ඊට අදාළ අඩු කිරීම ඉවත් වෙනවා.", "SUBTRACTION", "ADDITION"),
            cue(f"Both sides gain the same amount: {amount}.", f"දෙපසටම එකම ප්‍රමාණය වන {amount} එකතු වෙනවා.", "CUE_ADD_BOTH"),
            EQUALITY,
        ]
    match = re.match(r"Divide both sides by (.+)\.", instruction)
    if match:
        divisor = match.group(1)
        return [
            cue("The coefficient multiplies x.", "සංගුණකය x ගුණ කරනවා.", "MULTIPLICATION", "VARIABLE"),
            cue(f"Dividing both sides by {divisor} undoes that multiplication.", f"දෙපසම {divisor} න් බෙදීමෙන් එම ගුණ කිරීම ඉවත් වෙනවා.", "CUE_INVERSE_MULTIPLICATION"),
            cue("x is left by itself after simplifying.", "සරල කළ පසු x තනිව ඉතිරි වෙනවා.", "CUE_ISOLATE_VARIABLE"),
        ]
    if "inside the bracket" in instruction:
        return [
            cue("Multiply each term inside the bracket.", "වරහන තුළ ඇති එක් එක් පදය ගුණ කරන්න.", "MULTIPLICATION", "BRACKET"),
            cue("Include the variable term and the constant term.", "විචල්‍ය පදය සහ නියත පදය දෙකම ඇතුළත් කරන්න.", "VARIABLE", "TERM"),
            cue("The written form changes; its value stays the same.", "ලියන ආකාරය වෙනස් වුවත් අගය සමානව පවතිනවා.", "CUE_EQUAL_SIDES"),
        ]
    if "remove the denominator" in instruction:
        return [
            cue("Multiplication undoes division by the denominator.", "ගුණ කිරීමෙන් හරයෙන් බෙදීම ඉවත් වෙනවා.", "DIVISION", "MULTIPLICATION"),
            cue("Multiply every term on both sides.", "දෙපසෙහි ඇති සෑම පදයක්ම ගුණ කරන්න.", "CUE_MULTIPLY_BOTH"),
            cue("Include the constant terms too.", "නියත පදත් ඇතුළත් කරන්න.", "TERM"),
        ]
    if instruction.startswith("Identify"):
        return [ISOLATE]
    if instruction.startswith("Simplify"):
        return [
            cue("The same operation has already been applied to both sides.", "දැනටමත් දෙපසටම එකම ගණිත ක්‍රියාව සිදු කර තිබෙනවා.", "BOTH_SIDES"),
            EQUALITY,
        ]
    if instruction.startswith("Substitute"):
        return [
            SUBSTITUTE,
            cue("Calculate the left side.", "වම් පස ගණනය කරන්න.", "EQUATION"),
            cue("Calculate the right side separately.", "දකුණු පස වෙනම ගණනය කරන්න.", "EQUATION"),
            VERIFY,
        ]
    if instruction.startswith("Check"):
        return []
    return [SUBSTITUTE, VERIFY]


def explain_step(
    step: LessonStep, strategy: TutoringStrategy, actions: Callable[[str], list[str]],
) -> list[AvatarTeachingSegment]:
    core = _core_parts(step)
    reasoning = segments_from_lines(_reason_parts(step.instruction), actions, step.expression)
    if strategy == TutoringStrategy.CONCEPTUAL_EXPLANATION:
        return reasoning + core + segments_from_lines([
            cue("Why are both sides still equal?", "දෙපස තවම සමානව තිබෙන්නේ ඇයි?", "CUE_EQUAL_SIDES"),
        ], actions, step.expression)
    if strategy == TutoringStrategy.WORKED_EXAMPLE_BASED:
        return core + reasoning + segments_from_lines([
            cue("Compare this with the previous equation in the example.", "මේ සමීකරණය උදාහරණයේ පෙර සමීකරණය සමඟ සසඳන්න.", "EQUATION"),
        ], actions, step.expression)
    if strategy == TutoringStrategy.STEP_BY_STEP:
        return core + reasoning + segments_from_lines([
            cue("Check this small step before continuing.", "ඉදිරියට යාමට පෙර මේ කුඩා පියවර පරීක්ෂා කරන්න.", "CUE_VERIFY_EQUALITY"),
        ], actions, step.expression)
    return core + reasoning


def explain_hint(
    text: str, index: int, expression: str, actions: Callable[[str], list[str]],
) -> list[AvatarTeachingSegment]:
    """Only the already-revealed hint is available to this function."""
    if index == 0:
        lines = [EQUALITY, ISOLATE]
    elif index == 1:
        core = _core_parts(LessonStep(order=1, instruction=text, expression=expression,
                                    sign_actions=actions(text)))
        return core + segments_from_lines([
            SAME_OPERATION,
            cue("Simplify, then try the question again.", "සරල කර, ප්‍රශ්නයට නැවත උත්සාහ කරන්න.", "TRY_AGAIN"),
        ], actions, expression)
    else:
        # Split only the bank's known boundary, never a decimal or fraction.
        collected, separator, division = text.partition(". Divide")
        lines = [cue(collected + ("." if separator else ""),
                     "පද එක් පසකට ගත් පසු ලැබෙන සමීකරණය: " + collected.removeprefix("After collecting terms: "), *actions(collected))]
        if separator:
            lines.append(cue("Divide" + division, "අවශ්‍ය නම් දක්වා ඇති සංගුණකයෙන් දෙපසම බෙදන්න.", *actions("Divide" + division)))
        collected_expression = collected.removeprefix("After collecting terms: ")
        return segments_from_lines(lines, actions, collected_expression) + segments_from_lines(
            [SUBSTITUTE, VERIFY], actions, expression
        )
    return segments_from_lines(lines, actions, expression)
