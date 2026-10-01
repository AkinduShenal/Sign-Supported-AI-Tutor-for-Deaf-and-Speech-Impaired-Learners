from __future__ import annotations

import re

AVAILABLE = {
    "IDLE", "EQUATION", "BALANCE", "BOTH_SIDES", "VARIABLE",
    "ADDITION", "SUBTRACTION", "MULTIPLICATION", "DIVISION",
    "SUBSTITUTION", "SOLVE", "ANSWER",
    *{f"NUMBER_{i}" for i in range(10)},
}


def _numbers(text: str) -> list[str]:
    out: list[str] = []
    for token in re.findall(r"\d+", text):
        for digit in token:
            out.append(f"NUMBER_{digit}")
    return out


def plan_linear_equation_signs(instruction: str, expression: str = "") -> list[str]:
    text = f"{instruction} {expression}".lower()
    actions: list[str] = []

    if any(k in text for k in ("equation", "equals", "equal", "=")):
        actions.append("EQUATION")
    if any(k in text for k in ("both sides", "same operation", "keep both sides", "keep the balance")):
        actions.append("BOTH_SIDES")
    elif "balance" in text:
        actions.append("BALANCE")
    if any(k in text for k in ("variable", "unknown", " x ", " x+", "x +", "x-", "x -")):
        actions.append("VARIABLE")
    if any(k in text for k in ("add ", "addition", "plus", "+")):
        actions.append("ADDITION")
    if any(k in text for k in ("subtract", "subtraction", "minus", "-")):
        actions.append("SUBTRACTION")
    if any(k in text for k in ("multiply", "multiplication", "times", "×", "*")):
        actions.append("MULTIPLICATION")
    if any(k in text for k in ("divide", "division", "divided", "÷", "/")):
        actions.append("DIVISION")
    if any(k in text for k in ("substitute", "substitution")):
        actions.append("SUBSTITUTION")
    if any(k in text for k in ("solve", "find x", "find the value")):
        actions.append("SOLVE")
    if any(k in text for k in ("answer", "solution is", "result is")):
        actions.append("ANSWER")

    actions.extend(_numbers(instruction))

    # Prefer teaching intent and avoid long token-by-token sequences.
    deduped = list(dict.fromkeys(a for a in actions if a in AVAILABLE))
    return deduped[:4]
