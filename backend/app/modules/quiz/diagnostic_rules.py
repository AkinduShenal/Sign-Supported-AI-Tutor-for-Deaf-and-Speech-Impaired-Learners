"""Provisional PP1 Quiz rules; thresholds require teacher/research validation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticRuleConfig:
    version: str = "pp1-pre-v1"
    expected_questions: int = 10
    expected_difficulty_counts: tuple[int, int, int] = (4, 4, 2)

    # One wrong answer in a one-question group is insufficient for a weak area.
    weak_subconcept_min_attempts: int = 2
    weak_subconcept_accuracy_below: float = 0.75
    fallback_repeated_error_minimum: int = 2

    # Accuracy dominates; tier performance adds bounded evidence from harder items.
    accuracy_weight: float = 0.80
    difficulty_weight: float = 0.20
    easy_tier_weight: int = 1
    medium_tier_weight: int = 2
    hard_tier_weight: int = 3
    low_mastery_below: float = 0.45
    high_mastery_at_least: float = 0.75

    # Performance, not the question label alone, determines this Tutor field.
    advanced_accuracy_at_least: float = 0.80
    advanced_medium_accuracy_at_least: float = 0.75
    advanced_hard_accuracy_at_least: float = 0.50
    intermediate_accuracy_at_least: float = 0.50
    intermediate_medium_accuracy_at_least: float = 0.50

    confidence_pattern_min_count: int = 2
    calibrated_extreme_confidence_min_count: int = 3
    high_support_repeated_errors_at_least: int = 3
    high_support_high_confidence_errors_at_least: int = 3


RULES = DiagnosticRuleConfig()

SUBCONCEPT_FOCUS = {
    "one_step_addition": "One-step Addition",
    "one_step_subtraction": "One-step Subtraction",
    "one_step_multiplication": "One-step Multiplication",
    "one_step_division": "One-step Division",
    "two_step_equations": "Two-step Equations",
    "variables_both_sides": "Variables on Both Sides",
    "distributive_equations": "Equations with Brackets",
}

MISCONCEPTION_FOCUS = {
    "inverse_operation": "Inverse Operations",
    "sign_error": "Signs in Equations",
    "arithmetic_error": "Arithmetic Steps",
    "concept_confusion": "Equation Meaning",
    "other": "Linear Equation Steps",
}

TUTOR_MISCONCEPTION_CODES = frozenset(
    {
        "none",
        "inverse_operation",
        "sign_error",
        "arithmetic_error",
        "concept_confusion",
        "other",
    }
)
