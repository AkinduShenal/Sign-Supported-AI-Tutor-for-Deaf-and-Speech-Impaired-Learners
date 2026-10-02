"""Bounded, auditable Grade 10 content. No generated mathematics or sign motion.

The diagnostic contract is shared with /strategy. A trained strategy predictor
can be injected; the default is explicitly the existing rule-based baseline.
Content and thresholds remain drafts pending teacher/student evaluation.
"""

import re
from decimal import Decimal
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.tutor.content_schemas import (
    LessonStep,
    PracticeFeedback,
    PracticeQuestion,
    SignReference,
    SignSupportedText,
    TutorLessonResponse,
    WorkedExample,
)
from app.modules.tutor.schemas import TutorStrategyRequest, TutoringStrategy
from app.modules.tutor.sign_planner import MathSignPlanner
from app.modules.tutor.strategy_model import RuleBasedStrategyModel, StrategyPredictor

Level = Literal["foundation", "one_step", "two_step", "extended"]
LEVELS: tuple[Level, ...] = ("foundation", "one_step", "two_step", "extended")
CONTENT_VERSION = "grade10-linear-v1-draft"
SUPPORTED_CONCEPTS = {"linear_equations", "linear_equation_balancing"}
PLANNER = MathSignPlanner()


class PlanMetadata(BaseModel):
    level: Level
    source: Literal["diagnostic", "preview"]
    model_version: str
    content_version: str = CONTENT_VERSION
    primary_strategy: TutoringStrategy
    supporting_strategies: list[TutoringStrategy] = Field(default_factory=list)
    rationale: str
    misconception_support: str
    preferred_mode: str = "mixed"
    sign_support_required: bool = True
    content_review_status: str = "teacher_review_required"
    reassessment_note: str = "Return practice evidence to Quiz/Game for reassessment; this is not a new mastery diagnosis."


class AdaptivePractice(PracticeQuestion):
    progressive_hints: list[SignSupportedText]


class AdaptiveLesson(TutorLessonResponse):
    plan: PlanMetadata
    practice_questions: list[AdaptivePractice]


class PracticeCheckRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=80)


class PracticeCheckResponse(BaseModel):
    correct: bool
    feedback: str


def _actions(text: str) -> list[str]:
    # Key-term support, never a claim of sentence translation.
    actions = list(PLANNER.plan(instruction=text).sign_actions)
    # The bank only has single positive digit gestures. Never mime -5/2 as 5,2.
    if re.search(r"-\d|\d[/.]\d|\d{2,}", text):
        actions = [action for action in actions if not action.startswith("NUMBER_")]
    return actions


def _text(text: str) -> SignSupportedText:
    return SignSupportedText(text=text, sign_actions=_actions(text))


def _number(n: Fraction | int) -> str:
    return str(Fraction(n))


def _side(a: int, b: int) -> str:
    variable = "x" if a == 1 else "-x" if a == -1 else f"{a}x" if a else ""
    if not variable:
        return str(b)
    return variable + (f" + {b}" if b > 0 else f" - {-b}" if b < 0 else "")


def _example(a: int, b: int, c: int, d: int) -> WorkedExample:
    """Solve ax+b=cx+d by equivalence-preserving steps (unique solutions)."""
    if a == c:
        raise ValueError("This lesson bank requires a unique solution")
    original_a, original_b, original_c, original_d = a, b, c, d
    problem = f"{_side(a, b)} = {_side(c, d)}"
    steps: list[LessonStep] = []

    def add(instruction: str, expression: str) -> None:
        steps.append(
            LessonStep(
                order=len(steps) + 1,
                instruction=instruction,
                expression=expression,
                sign_actions=_actions(instruction),
            )
        )

    add(
        "Identify x, the unknown variable. Both sides must have the same value.",
        problem,
    )
    if c:
        operation = "Subtract" if c > 0 else "Add"
        symbol = "-" if c > 0 else "+"
        term = _side(abs(c), 0)
        add(
            f"{operation} {term} on both sides to collect the variable terms.",
            f"({_side(a, b)}) {symbol} {term} = ({_side(c, d)}) {symbol} {term}",
        )
        a -= c
        add(
            "Simplify each side. The equation remains balanced.", f"{_side(a, b)} = {d}"
        )
    if b:
        operation = "Subtract" if b > 0 else "Add"
        symbol = "-" if b > 0 else "+"
        add(
            f"{operation} {abs(b)} {'from' if b > 0 else 'to'} both sides.",
            f"({_side(a, b)}) {symbol} {abs(b)} = {d} {symbol} {abs(b)}",
        )
        d -= b
        add("Simplify both sides.", f"{_side(a, 0)} = {d}")
    result = Fraction(d, a)
    if a != 1:
        add(
            f"Divide both sides by {a}.",
            f"({_side(a, 0)}) / ({a}) = {d} / ({a})",
        )
    add("Solve the equation. The variable is now by itself.", f"x = {_number(result)}")
    # Refer back to the original coefficients, not the transformed equation.
    add(
        f"Substitute {_number(result)} for x in the ORIGINAL equation shown above.",
        f"{original_a} × ({_number(result)}) + ({original_b}) = {original_c} × ({_number(result)}) + ({original_d})",
    )
    add(
        "Check both sides. They have the same value, so the solution satisfies the original equation.",
        f"{_number(original_a * result + original_b)} = {_number(original_c * result + original_d)}",
    )
    add("Final answer.", f"x = {_number(result)}")
    return WorkedExample(problem=problem, steps=steps, answer=f"x = {_number(result)}")


def _bracket_example(k: int, b: int, d: int) -> WorkedExample:
    base = _example(k, k * b, 0, d)
    original = f"{k}({_side(1, b)}) = {d}"
    opening = LessonStep(
        order=1,
        instruction="Multiply every term inside the bracket by the number outside.",
        expression=f"{original} → {_side(k, k * b)} = {d}",
        sign_actions=["MULTIPLICATION", "BRACKET"],
    )
    base.steps.insert(0, opening)
    base.problem = original
    value = Fraction(d, k) - b
    base.steps[-3].expression = f"{k} × ({_number(value)} + {b}) = {d}"
    for index, step in enumerate(base.steps):
        step.order = index + 1
    return base


def _fraction_example(divisor: int, b: int, d: int) -> WorkedExample:
    base = _example(1, divisor * b, 0, divisor * d)
    problem = f"x/{divisor} + {b} = {d}"
    base.steps.insert(
        0,
        LessonStep(
            order=1,
            instruction=f"Multiply BOTH sides, including every term, by {divisor} to remove the denominator.",
            expression=f"{divisor} × (x/{divisor} + {b}) = {divisor} × {d}",
            sign_actions=["MULTIPLICATION", f"NUMBER_{divisor}", "BOTH_SIDES"],
        ),
    )
    base.problem = problem
    value = divisor * (d - b)
    base.steps[-3].expression = f"{value}/{divisor} + {b} = {d}"
    for index, step in enumerate(base.steps):
        step.order = index + 1
    return base


def _examples(level: Level) -> list[WorkedExample]:
    return {
        "foundation": lambda: [_example(1, 3, 0, 7), _example(1, -4, 0, 2)],
        "one_step": lambda: [_example(1, -4, 0, 5), _example(3, 0, 0, 12)],
        "two_step": lambda: [_example(2, 3, 0, 11), _example(3, -5, 0, 7)],
        "extended": lambda: [
            _example(3, 2, 1, 10),
            _bracket_example(2, 3, 14),
            _fraction_example(3, 2, 5),
            _example(-2, 3, 0, 8),
        ],
    }[level]()


# Separate examples and practice; each level has two unique practice items.
PRACTICE = {
    "foundation": [(1, 5, 0, 12), (1, 2, 0, 8)],
    "one_step": [(1, -4, 0, 6), (4, 0, 0, 20)],
    "two_step": [(2, 5, 0, 17), (3, -2, 0, 13)],
    "extended": [(4, 3, 2, 15), (-2, 1, 0, 6)],
}


def _practice(level: Level) -> list[AdaptivePractice]:
    questions = []
    for index, (a, b, c, d) in enumerate(PRACTICE[level]):
        worked = _example(a, b, c, d)
        operation = next(
            (
                s.instruction
                for s in worked.steps[1:]
                if "both sides" in s.instruction.lower()
            ),
            "Use an inverse operation on both sides.",
        )
        questions.append(
            AdaptivePractice(
                question_id=f"g10-v1-{level}-{index + 1}",
                prompt=f"Solve {worked.problem}.",
                hint=_text(operation),
                expected_answer=worked.answer,
                progressive_hints=[
                    _text("Keep both sides equal. Aim to leave x by itself."),
                    _text(operation),
                    _text(
                        f"After collecting terms: {_side(a - c, 0)} = {d - b}. Divide both sides by {a - c} if needed."
                    ),
                ],
                feedback=PracticeFeedback(
                    correct="Correct. Substitute your value into the original equation to check it.",
                    incorrect="Not yet. Use the next hint or review a worked example; apply each operation to both sides.",
                ),
            )
        )
    return questions


MISCONCEPTION_SUPPORT = {
    "none": "Check each operation on both sides, then substitute your answer.",
    "inverse_operation": "Undo addition with subtraction, and multiplication with division. Apply the operation to both sides.",
    "sign_error": "Keep the sign attached to its number. Adding 4 undoes subtracting 4; do not change signs just by moving a term.",
    "arithmetic_error": "Write one arithmetic calculation at a time. Recheck negative numbers and verify both sides using your answer.",
    "concept_confusion": "The equals sign means both sides have the SAME value. x is an unknown number, not a multiplication sign.",
    "other": "Start with the balance idea. Review one worked example and identify the first step that is unclear.",
}


def build_lesson(level: Level, metadata: PlanMetadata) -> AdaptiveLesson:
    examples = _examples(level)
    questions = _practice(level)
    simple = _text(
        "An equation is like a balance. Perform the SAME operation on BOTH sides to keep them equal."
    )
    sign_ids = set(simple.sign_actions)
    for example in examples:
        for step in example.steps:
            sign_ids.update(step.sign_actions)
    for question in questions:
        for hint in question.progressive_hints:
            sign_ids.update(hint.sign_actions)
    glossary = []
    for sign_id in sorted(sign_ids):
        entry = PLANNER.manifest_entry(sign_id) or {}
        glossary.append(
            SignReference(
                sign_id=sign_id,
                label=sign_id.replace("_", " "),
                source_title="Manifest key-term mapping; not a validated sentence translation",
                source_page=None,
                source_entry=None,
                animation_asset=entry.get("animation_asset"),
                animation_action=entry.get("animation_action"),
                prototype_ready=bool(entry.get("prototype_ready")),
                validation_status="validated"
                if entry.get("validation_status") == "validated"
                else "pending",
            )
        )
    return AdaptiveLesson(
        concept_id="linear_equation_balancing",
        title="Grade 10 · Linear equations",
        learning_objective={
            "foundation": "Understand equality and undo addition or subtraction.",
            "one_step": "Solve one-step equations using inverse operations.",
            "two_step": "Undo addition/subtraction, then multiplication/division.",
            "extended": "Solve equations with variables on both sides, brackets, fractions and negative coefficients.",
        }[level],
        simple_explanation=simple,
        sign_glossary=glossary,
        worked_examples=examples,
        practice_questions=questions,
        plan=metadata,
    )


def preview_lesson(level: Level) -> AdaptiveLesson:
    return build_lesson(
        level,
        PlanMetadata(
            level=level,
            source="preview",
            model_version="preview-no-inference",
            primary_strategy=TutoringStrategy.STEP_BY_STEP,
            rationale="Manually selected preview; no student performance was assessed.",
            misconception_support=MISCONCEPTION_SUPPORT["none"],
        ),
    )


def plan_lesson(
    request: TutorStrategyRequest, model: StrategyPredictor | None = None
) -> AdaptiveLesson:
    if (
        request.concept_id not in SUPPORTED_CONCEPTS
        or request.quiz.weak_concept not in SUPPORTED_CONCEPTS
    ):
        raise ValueError(
            "This planner supports only Grade 10 linear equations; route other concepts to their own tutor."
        )
    model = model or RuleBasedStrategyModel()
    prediction = model.predict(request)
    # Mastery is input supplied by Quiz/Game, not a new diagnostic owned by Tutor.
    score = (
        sum(
            Decimal(str(value))
            for value in (
                request.quiz.quiz_mastery_score,
                request.game.game_mastery_score,
                request.learner.prior_mastery_score,
            )
        )
        / 3
    )
    level: Level = (
        "foundation"
        if score < Decimal("0.5")
        else "one_step"
        if score < Decimal("0.7")
        else "two_step"
    )
    if (
        prediction.primary_strategy == TutoringStrategy.ADVANCED_CHALLENGE
        and request.quiz.quiz_difficulty_level == "advanced"
    ):
        level = "extended"
    if prediction.primary_strategy in {
        TutoringStrategy.STEP_BY_STEP,
        TutoringStrategy.CONCEPTUAL_EXPLANATION,
    }:
        level = "foundation"
    metadata = PlanMetadata(
        level=level,
        source="diagnostic",
        model_version=model.version,
        primary_strategy=prediction.primary_strategy,
        supporting_strategies=list(prediction.supporting_strategies),
        rationale=f"Quiz mastery {request.quiz.quiz_mastery_score:.0%}; Game mastery {request.game.game_mastery_score:.0%}; prior mastery {request.learner.prior_mastery_score:.0%}. Conservative draft placement; response speed is not used as an ability penalty.",
        misconception_support=MISCONCEPTION_SUPPORT[request.quiz.misconception_code],
        preferred_mode=request.learner.preferred_mode,
        sign_support_required=request.learner.sign_support_required,
    )
    lesson = build_lesson(level, metadata)
    # Keep the same verified equation steps, but begin with the example that
    # targets this learner's reported misconception rather than a fixed order.
    if request.quiz.misconception_code == "sign_error" and level in {
        "foundation",
        "two_step",
    }:
        lesson.worked_examples.reverse()
    return lesson


def check_practice(request: PracticeCheckRequest) -> PracticeCheckResponse:
    question = next(
        (
            q
            for level in LEVELS
            for q in _practice(level)
            if q.question_id == request.question_id
        ),
        None,
    )
    if question is None:
        raise KeyError(request.question_id)
    # Bounded grammar, no eval; equivalent finite decimals/fractions are accepted.
    answer = (
        re.sub(r"\s+", "", request.answer.lower()).removeprefix("x=").replace("−", "-")
    )
    if not re.fullmatch(
        r"[+-]?(?:\d{1,12}(?:\.\d{1,12})?|\.\d{1,12})(?:/[+-]?\d{1,12})?", answer
    ):
        return PracticeCheckResponse(
            correct=False,
            feedback="Enter a number, fraction, or x = number (for example x = -5/2).",
        )
    try:
        parts = answer.split("/")
        value = Fraction(parts[0]) / (Fraction(parts[1]) if len(parts) == 2 else 1)
        correct = value == Fraction(question.expected_answer.split("=")[1].strip())
    except (ValueError, ZeroDivisionError):
        correct = False
    return PracticeCheckResponse(
        correct=correct,
        feedback=question.feedback.correct if correct else question.feedback.incorrect,
    )
