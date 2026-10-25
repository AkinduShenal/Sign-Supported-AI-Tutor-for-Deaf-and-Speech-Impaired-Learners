"""Generate the review-pending 60-item PP1 bank from the existing ten-slot blueprint.

Run from backend/: python -m scripts.generate_quiz_dynamic_bank
No database connection is used. Generated files are committed as review artifacts.
"""

import json
from fractions import Fraction
from pathlib import Path

BANK_VERSION = "pp1_dynamic_v1_DRAFT"
ORIGINAL = Path(__file__).with_name("quiz_pre_prototype.json")
OUT = Path(__file__).with_name("quiz_dynamic_60_DRAFT.json")
REPORT = Path(__file__).with_name("quiz_dynamic_60_teacher_review.md")
SI_PREFIX = "සමීකරණය විසඳන්න: "


def load_original() -> dict:
    return json.loads(ORIGINAL.read_text(encoding="utf-8"))

# The first parameter set reproduces the original equation for each slot.
# Slots 05-08 stay two-step equations; slot 10 stays distributive.
PARAMETERS = [
    [(5, 7), (3, 4), (6, 2), (8, 5), (9, 3), (4, 10)],
    [(8, 11), (4, 7), (6, 5), (9, 12), (3, 12), (7, 8)],
    [(4, 7), (3, 8), (5, 6), (6, 4), (7, 3), (8, 5)],
    [(3, 6), (2, 7), (4, 5), (5, 3), (6, 4), (7, 2)],
    [(2, 3, 6), (3, 2, 5), (4, 1, 4), (5, 3, 3), (2, 5, 7), (3, 4, 6)],
    [(3, 4, 7), (2, 5, 6), (4, 3, 5), (5, 2, 4), (3, 7, 8), (6, 4, 3)],
    [(5, 2, 6), (3, 4, 5), (4, 3, 7), (2, 7, 6), (6, 5, 4), (7, 1, 3)],
    [(2, 4, 10), (3, 2, 9), (4, 3, 8), (5, 1, 10), (2, 6, 12), (3, 5, 6)],
    [(3, 1, 4, 7), (4, 2, 3, 5), (5, 2, 1, 4), (6, 3, 5, 8), (4, 1, 2, 6), (7, 4, 3, 2)],
    [(2, 3, 1, 8), (3, 2, 1, 7), (4, 1, 2, 5), (3, 4, 2, 9), (5, 2, 3, 6), (4, 3, 1, 8)],
]


def equation(slot: int, p: tuple[int, ...]) -> tuple[str, int, list[tuple[int, str]]]:
    if slot == 1:
        a, x = p; eq = f"x + {a} = {x+a}"; wrong = [(x+2*a, "inverse_operation"), (a, "concept_confusion"), (x+a, "concept_confusion")]
    elif slot == 2:
        a, x = p; eq = f"x - {a} = {x-a}"; wrong = [(x-2*a, "sign_error"), (a, "concept_confusion"), (x-a, "concept_confusion")]
    elif slot == 3:
        a, x = p; eq = f"{a}x = {a*x}"; wrong = [(a*x+a, "inverse_operation"), (a*x-a, "inverse_operation"), (a, "concept_confusion")]
    elif slot == 4:
        a, b = p; x = a*b; eq = f"x ÷ {a} = {b}"; wrong = [(b+a, "inverse_operation"), (b, "concept_confusion"), (a, "concept_confusion")]
    elif slot in (5, 7):
        a, b, x = p; eq = f"{a}x + {b} = {a*x+b}"; wrong = [(a*x, "concept_confusion"), (x+1, "arithmetic_error"), (x-1, "arithmetic_error")]
    elif slot == 6:
        a, b, x = p; eq = f"{a}x - {b} = {a*x-b}"; wrong = [(a*x, "concept_confusion"), (x+1, "arithmetic_error"), (x-1, "arithmetic_error")]
    elif slot == 8:
        a, b, x = p; eq = f"x ÷ {a} + {b} = {x//a+b}"; wrong = [(x//a, "concept_confusion"), (x+a*b, "inverse_operation"), (x+1, "arithmetic_error")]
        assert x % a == 0
    elif slot == 9:
        a, c, b, x = p; eq = f"{a}x + {b} = {'' if c == 1 else c}x + {(a-c)*x+b}"; wrong = [((a-c)*x, "concept_confusion"), (x+1, "arithmetic_error"), (x-1, "sign_error")]
        assert a > c
    else:
        a, b, c, x = p; eq = f"{a}(x + {b}) = {'' if c == 1 else c}x + {(a-c)*x+a*b}"; wrong = [(x+a*b, "concept_confusion"), (x+1, "arithmetic_error"), (x-1, "sign_error")]
        assert a > c
    # Every item has three distinct incorrect integer choices. Candidate tags
    # are hypotheses for teacher review, never validated diagnostic mappings.
    seen = {x}; clean = []
    for value, tag in wrong + [(x+2, "arithmetic_error"), (x-2, "arithmetic_error"), (x+3, "concept_confusion")]:
        if value not in seen:
            seen.add(value); clean.append((value, tag))
        if len(clean) == 3: break
    assert len(clean) == 3 and all(isinstance(v, int) for v, _ in clean)
    return eq, x, clean


def build_bank() -> list[dict]:
    original = load_original()["questions"]
    items = []
    for index, (source, params) in enumerate(zip(original, PARAMETERS, strict=True), 1):
        for variant, values in enumerate(params, 1):
            eq, answer, wrong = equation(index, tuple(values))
            if variant == 1:
                # Preserve the existing diagnostic option evidence where its
                # equation is identical; it remains teacher-unreviewed.
                assert eq.replace("Solve ", "") in source["text_en"]
                choices = [(int(Fraction(text)), tag) for _, text, _, tag in source["options"]]
                correct_index = next(i for i, option in enumerate(source["options"]) if option[2])
                assert choices[correct_index][0] == answer
            else:
                correct_index = (index + variant) % 4
                choices = list(wrong)
                choices.insert(correct_index, (answer, None))
            code = f"PP1-DYN-S{index:02d}-V{variant:02d}"
            items.append({
                "question_code": code, "bank_version": BANK_VERSION,
                "logical_slot": f"S{index:02d}", "concept_id": "linear_equations",
                "subconcept_code": source["subconcept"], "difficulty_level": source["difficulty"],
                "question_text_en": f"Solve {eq}.", "question_text_si": f"{SI_PREFIX}{eq}.",
                "answer": str(answer), "teacher_validated": False,
                "review_status": "DRAFT_REVIEW", "research_use": "DEVELOPMENT_ONLY",
                "options": [
                    {"option_code": letter, "text": str(value), "is_correct": pos == correct_index,
                     "misconception_code": None if pos == correct_index else tag}
                    for pos, (letter, (value, tag)) in enumerate(zip("ABCD", choices, strict=True))
                ],
            })
    return items


def main() -> None:
    bank = build_bank()
    OUT.write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# PP1 Dynamic Quiz: teacher review", "", "All 60 questions and Sinhala wording are drafts. Distractor misconception tags are provisional. Sign off each slot and variant before research use.", ""]
    for slot in range(1, 11):
        source = load_original()["questions"][slot - 1]
        lines += [f"## S{slot:02d} · {source['subconcept']} · {source['difficulty']}", f"Original: {source['text_en']}", ""]
        for item in bank[(slot-1)*6:slot*6]:
            options = "; ".join(f"{o['option_code']} {o['text']} ({'correct' if o['is_correct'] else o['misconception_code']})" for o in item["options"])
            lines += [f"- {item['question_code']}: {item['question_text_en']} / {item['question_text_si']}", f"  - {options}", "  - Math / skill / difficulty / Sinhala / distractor tags approved: __________"]
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {len(bank)} draft items and review report")


if __name__ == "__main__": main()
