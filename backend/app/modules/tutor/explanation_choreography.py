"""One semantic choreography path for all authored tutor explanations.

This compiles meaning demonstrations, not Sinhala-to-SLSL word translation.
The exact caption survives, mathematical context is explicit, and the GLB cue
sheet determines timing. Unknown lexical signs are never certified by a rule.
"""
from __future__ import annotations

import re

from app.modules.tutor.content_schemas import AvatarTeachingSegment
from app.modules.tutor.knowledge import ExplanationMotion, MotionBeat
from app.modules.tutor.sign_planner import MathSignPlanner

LABELS = {
    "look": ("Look at this", "මෙය බලන්න"),
    "reference": ("Look at the equation", "සමීකරණය බලන්න"),
    "original": ("The original equation above", "ඉහත දැක්වෙන මුල් සමීකරණය"),
    "equation": ("Read the equation", "සමීකරණය කියවමු"),
    "left": ("The left side", "වම් පස"),
    "right": ("The right side", "දකුණු පස"),
    "both": ("Both sides", "දෙපසම"),
    "equal": ("The values stay equal", "අගයන් සමානයි"),
    "balanced": ("Keep the balance", "සමබරතාව රකිමු"),
    "one_side": ("Only one side", "එක් පසක් පමණයි"),
    "compare": ("Compare the two sides", "දෙපස සසඳන්න"),
    "variable": ("The place occupied by x", "x තිබෙන ස්ථානය"),
    "unknown": ("x is the unknown number", "x නොදන්නා සංඛ්‍යාවයි"),
    "not_multiply": ("x is not the multiplication symbol ×", "x යනු ගුණ කිරීමේ × ලකුණ නොවේ"),
    "isolate": ("Leave x by itself", "x තනි කරන්න"),
    "add": ("Add the amount", "ප්‍රමාණය එකතු කරන්න"),
    "subtract": ("Subtract the amount", "ප්‍රමාණය අඩු කරන්න"),
    "multiply": ("Multiply", "ගුණ කරන්න"),
    "divide": ("Divide by a nonzero value", "ශුන්‍ය නොවන අගයකින් බෙදන්න"),
    "undo_subtract": ("Undo with subtraction", "අඩු කිරීමෙන් ඉවත් කරන්න"),
    "undo_add": ("Undo with addition", "එකතු කිරීමෙන් ඉවත් කරන්න"),
    "undo_divide": ("Undo with division", "බෙදීමෙන් ඉවත් කරන්න"),
    "value": ("The value to use", "යෙදිය යුතු අගය"),
    "place": ("Put that value in place of x", "x වෙනුවට එම අගය දමන්න"),
    "replaced": ("Now the value occupies every x position", "දැන් සෑම x ස්ථානයකම එම අගය තිබෙනවා"),
    "collect": ("Collect the variable terms", "විචල්‍ය පද එක් පසකට ගන්න"),
    "group": ("The bracketed group", "වරහන තුළ ඇති කොටස"),
    "each_term": ("Include every term", "සෑම පදයක්ම ඇතුළත් කරන්න"),
    "one_step": ("One small step", "එක් කුඩා පියවරක්"),
    "continue": ("Continue to the next step", "ඊළඟ පියවරට යන්න"),
    "try": ("Try the question", "ප්‍රශ්නය උත්සාහ කරන්න"),
    "check": ("Check the result", "ප්‍රතිඵලය පරීක්ෂා කරන්න"),
    "negative": ("A negative sign", "ඍණ ලකුණක්"),
    "keep_sign": ("Keep the sign with its number", "ලකුණ එහි සංඛ්‍යාව සමඟ තබන්න"),
}


def choose_flow(text: str, actions: list[str]) -> tuple[str, str | None]:
    en = text.casefold()
    amount = re.search(r"\b(?:substitute|substituting)\s+(-?\d+(?:/\d+|\.\d+)?)\s+for\s+x", en)
    if any(word in en for word in ("substitut", "in place of", "replace")):
        value = amount.group(1) if amount else None
        return (f"FLOW_SUBSTITUTE_{value}" if value in set("123456789") else "FLOW_SUBSTITUTE"), value
    if "not the multiplication" in en or "not a multiplication" in en:
        return "FLOW_VARIABLE_NOT_MULTIPLY", None
    if "only one side" in en or "break the balance" in en:
        return "FLOW_UNBALANCED", None
    if any(word in en for word in ("check", "verify", "confirms", "satisfies", "calculate the")):
        return "FLOW_CHECK", None
    if any(word in en for word in ("collect", "variable terms on", "same variable term on both sides")):
        return "FLOW_COLLECT", None
    if "bracket" in en or "every term" in en or "denominator" in en or "include the constant terms" in en:
        return "FLOW_EXPAND", None
    if "undo" in en and "multipli" in en:
        return "FLOW_INVERSE_MULTIPLY", None
    if "undo" in en and "subtract" in en and en.startswith(("adding", "addition")):
        return "FLOW_INVERSE_SUBTRACT", None
    if "undo" in en and ("add" in en or "subtract" in en):
        return "FLOW_INVERSE_ADD", None
    if any(word in en for word in ("subtract", "lose the same")):
        return "FLOW_SUBTRACT_BOTH", None
    if any(word in en for word in ("add ", "adding", "gain the same", "addition")):
        return "FLOW_ADD_BOTH", None
    if "divid" in en:
        return "FLOW_DIVIDE_BOTH", None
    if "multipl" in en or "coefficient" in en:
        return "FLOW_MULTIPLY_BOTH", None
    if any(word in en for word in ("by itself", "one side", "leave x", "goal")):
        return "FLOW_ISOLATE", None
    if "negative" in en or "keep the sign" in en or "change a sign" in en:
        return "FLOW_NEGATIVE", None
    if "try again" in en or "try the question again" in en:
        return "FLOW_RETRY", None
    if "hint" in en or "help" in en:
        return "FLOW_HINT", None
    if "practice" in en or "independen" in en or "challenge" in en:
        return "FLOW_PRACTICE", None
    if "unknown" in en or "x represents" in en:
        return "FLOW_VARIABLE", None
    if "compare" in en or "previous equation" in en:
        return "FLOW_COMPARE", None
    if "step" in en or "simplify" in en or "simplifying" in en:
        return "FLOW_STEP", None
    if "balance" in en or "scale" in en:
        return "FLOW_BALANCE", None
    if "equal" in en or "same value" in en or "same operation" in en or "value stays the same" in en:
        return "FLOW_EQUALITY", None
    if "answer" in en or "result" in en:
        return "FLOW_ANSWER", None
    if "equation" in en or "read" in en or "written form" in en:
        return "FLOW_READ", None
    # Authored cue IDs remain useful for very short bank labels. These are
    # semantic demonstrations; selecting one never claims lexical equivalence.
    mapping = {"SUBTRACTION": "FLOW_SUBTRACT_BOTH", "ADDITION": "FLOW_ADD_BOTH",
               "DIVISION": "FLOW_DIVIDE_BOTH", "MULTIPLICATION": "FLOW_MULTIPLY_BOTH",
               "VARIABLE": "FLOW_VARIABLE", "SOLVE": "FLOW_ISOLATE",
               "ANSWER": "FLOW_ANSWER", "BOTH_SIDES": "FLOW_EQUALITY"}
    return next((mapping[a] for a in actions if a in mapping), "FLOW_READ"), None


def choreograph_segments(segments: list[AvatarTeachingSegment], *,
                         original_expression: str | None = None,
                         expression_context: str | None = None) -> list[AvatarTeachingSegment]:
    planner = MathSignPlanner()
    results = []
    for segment in segments:
        if segment.support_kind == "expression" or segment.motion is not None:
            results.append(segment)
            continue
        clip, value = choose_flow(segment.text, segment.sign_actions)
        if clip in {"FLOW_ADD_BOTH", "FLOW_SUBTRACT_BOTH", "FLOW_MULTIPLY_BOTH", "FLOW_DIVIDE_BOTH"}:
            amount_match = re.search(r"(?:\b(?:subtract(?:ing)?|add(?:ing)?)\s+|\bby\s+|amount:\s*)(-?\d+(?:/\d+|\.\d+)?)", segment.text, re.I)
            if amount_match:
                value = amount_match.group(1)
                if value in set("123456789"):
                    clip += f"_{value}"
        entry = planner.manifest_entry(clip)
        if not entry or not entry.get("teaching_beats"):
            # Missing build is explicit, not a fabricated successful animation.
            results.append(segment.model_copy(update={"unsupported_tokens": [*segment.unsupported_tokens, "explanation motion unavailable"]}))
            continue
        current = segment.expression or expression_context
        original = original_expression or current
        substituted = None
        if clip.startswith("FLOW_SUBSTITUTE") and value and original and "x" in original:
            substituted = re.sub(r"(?<![A-Za-z])x(?![A-Za-z])", f"({value})", original)
        beats = []
        for beat in entry["teaching_beats"]:
            text, text_si = LABELS[beat["role"]]
            if value and beat["role"] == "value":
                text, text_si = f"Use {value}", f"{value} යොදන්න"
            if value and beat["role"] == "place":
                text, text_si = f"Put {value} in place of x", f"x වෙනුවට {value} ආදේශ කරන්න"
            beats.append(MotionBeat(**beat, text=text, text_si=text_si))
        motion = ExplanationMotion(clip=clip, kind=clip.removeprefix("FLOW_").lower(),
                                   beats=beats, original_expression=original,
                                   current_expression=current, substituted_expression=substituted, value=value)
        results.append(segment.model_copy(update={"sign_actions": [clip], "motion": motion,
                                                  "support_kind": "meaning_demonstration"}))
    return results
