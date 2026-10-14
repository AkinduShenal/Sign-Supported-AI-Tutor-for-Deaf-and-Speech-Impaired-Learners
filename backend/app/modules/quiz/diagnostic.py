"""Deterministic diagnostics from stored Quiz response and question evidence."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping

from app.modules.quiz.diagnostic_rules import (
    RULES,
    SUBCONCEPT_FOCUS,
    TUTOR_MISCONCEPTION_CODES,
    DiagnosticRuleConfig,
)


@dataclass(frozen=True)
class ResponseEvidence:
    question_id: str
    question_order: int
    subconcept_code: str
    difficulty_level: str
    is_correct: bool
    response_time_sec: float
    confidence_level: str
    misconception_code: str | None


@dataclass(frozen=True)
class MappingEvidence:
    minimum_occurrences: int
    teacher_validated: bool


@dataclass(frozen=True)
class DiagnosticValues:
    questions_total: int
    questions_attempted: int
    correct_answers: int
    quiz_accuracy: float
    quiz_avg_response_time_sec: float
    quiz_hint_rate: float
    misconception_code: str
    repeated_error_count: int
    weak_subconcept: str | None
    quiz_mastery_score: float
    mastery_level: str
    recommended_support_level: str
    recommended_focus: str
    confidence_pattern: str
    quiz_difficulty_level: str
    diagnostic_evidence: dict


def _summary(rows: list[ResponseEvidence]) -> dict[str, float | int]:
    attempted = len(rows)
    correct = sum(item.is_correct for item in rows)
    return {
        "attempted": attempted,
        "correct": correct,
        "incorrect": attempted - correct,
        "accuracy": round(correct / attempted, 4) if attempted else 0.0,
    }


def calculate_diagnostic(
    responses: list[ResponseEvidence],
    mappings: Mapping[str, MappingEvidence],
    rules: DiagnosticRuleConfig = RULES,
) -> DiagnosticValues:
    if len(responses) != rules.expected_questions:
        raise ValueError("Diagnostic requires the complete official question set")

    attempted = len(responses)
    correct = sum(item.is_correct for item in responses)
    accuracy = correct / attempted
    response_times = [item.response_time_sec for item in responses]
    average_time = sum(response_times) / attempted

    by_subconcept: dict[str, list[ResponseEvidence]] = defaultdict(list)
    by_difficulty: dict[str, list[ResponseEvidence]] = defaultdict(list)
    for item in responses:
        by_subconcept[item.subconcept_code].append(item)
        by_difficulty[item.difficulty_level].append(item)
    subconcept_performance = {
        code: _summary(rows) for code, rows in sorted(by_subconcept.items())
    }
    difficulty_performance = {
        tier: _summary(by_difficulty[tier]) for tier in ("easy", "medium", "hard")
    }

    weak_candidates = [
        (code, item)
        for code, item in subconcept_performance.items()
        if item["attempted"] >= rules.weak_subconcept_min_attempts
        and item["accuracy"] < rules.weak_subconcept_accuracy_below
    ]
    # A tied lowest accuracy does not support naming one area as uniquely weak.
    lowest_accuracy = min((item["accuracy"] for _, item in weak_candidates), default=None)
    lowest_candidates = [
        code for code, item in weak_candidates if item["accuracy"] == lowest_accuracy
    ]
    weak_subconcept = lowest_candidates[0] if len(lowest_candidates) == 1 else None

    misconception_counts = Counter(
        item.misconception_code
        for item in responses
        if not item.is_correct and item.misconception_code
    )
    qualifying = [
        code
        for code, count in misconception_counts.items()
        if count
        >= (
            mappings[code].minimum_occurrences
            if code in mappings
            else rules.fallback_repeated_error_minimum
        )
    ]
    selected_source_code = (
        min(qualifying, key=lambda code: (-misconception_counts[code], code))
        if qualifying
        else None
    )
    misconception_code = (
        selected_source_code
        if selected_source_code in TUTOR_MISCONCEPTION_CODES
        else "other"
        if selected_source_code
        else "none"
    )
    repeated_error_count = (
        misconception_counts[selected_source_code] if selected_source_code else 0
    )

    confidence_counts = {
        "correct": {level: 0 for level in ("low", "medium", "high")},
        "incorrect": {level: 0 for level in ("low", "medium", "high")},
    }
    for item in responses:
        confidence_counts["correct" if item.is_correct else "incorrect"][
            item.confidence_level
        ] += 1
    confidence_correctness = {
        f"{level}_{outcome}": confidence_counts[outcome][level]
        for level in ("high", "medium", "low")
        for outcome in ("correct", "incorrect")
    }
    high_wrong = confidence_counts["incorrect"]["high"]
    low_right = confidence_counts["correct"]["low"]
    extremes = sum(
        confidence_counts[outcome][level]
        for outcome in ("correct", "incorrect")
        for level in ("low", "high")
    )
    if (
        high_wrong >= rules.confidence_pattern_min_count
        and low_right >= rules.confidence_pattern_min_count
    ):
        confidence_pattern = "mixed_inconsistent"
    elif high_wrong >= rules.confidence_pattern_min_count:
        confidence_pattern = "high_confidence_incorrect"
    elif low_right >= rules.confidence_pattern_min_count:
        confidence_pattern = "low_confidence_correct"
    elif extremes < rules.calibrated_extreme_confidence_min_count:
        confidence_pattern = "limited_signal"
    elif high_wrong + low_right >= rules.confidence_pattern_min_count:
        confidence_pattern = "mixed_inconsistent"
    else:
        confidence_pattern = "generally_calibrated"

    # This chooses learner copy; it does not change mastery or diagnose errors.
    if (
        high_wrong >= rules.confidence_pattern_min_count
        and low_right >= rules.confidence_pattern_min_count
    ):
        insight_kind = "mixed"
    elif high_wrong >= rules.confidence_pattern_min_count:
        insight_kind = "high_incorrect"
    elif low_right >= rules.confidence_pattern_min_count:
        insight_kind = "low_correct"
    else:
        insight_kind = "neutral"

    question_evidence = [
        {
            "question_order": item.question_order,
            "question_id": item.question_id,
            "is_correct": item.is_correct,
            "confidence_level": item.confidence_level,
            "confidence_correctness_state": (
                "secure_understanding"
                if item.is_correct and item.confidence_level == "high"
                else "fragile_understanding"
                if item.is_correct and item.confidence_level == "low"
                else "knowledge_gap_signal"
                if not item.is_correct and item.confidence_level == "low"
                else "possible_misconception_signal"
                if not item.is_correct and item.confidence_level == "high"
                else "medium_confidence_correct"
                if item.is_correct
                else "medium_confidence_incorrect"
            ),
            "response_time_sec": item.response_time_sec,
            "subconcept_code": item.subconcept_code,
            "difficulty_level": item.difficulty_level,
            "misconception_code": item.misconception_code
            if not item.is_correct
            else None,
        }
        for item in sorted(responses, key=lambda row: row.question_order)
    ]
    average_time_by_subconcept = {
        code: round(sum(item.response_time_sec for item in rows) / len(rows), 2)
        for code, rows in sorted(by_subconcept.items())
    }

    weighted_tier_accuracy = (
        difficulty_performance["easy"]["accuracy"] * rules.easy_tier_weight
        + difficulty_performance["medium"]["accuracy"] * rules.medium_tier_weight
        + difficulty_performance["hard"]["accuracy"] * rules.hard_tier_weight
    ) / (rules.easy_tier_weight + rules.medium_tier_weight + rules.hard_tier_weight)
    mastery_score = round(
        rules.accuracy_weight * accuracy
        + rules.difficulty_weight * weighted_tier_accuracy,
        4,
    )
    if mastery_score < rules.low_mastery_below:
        mastery_level = "low"
    elif mastery_score >= rules.high_mastery_at_least:
        mastery_level = "high"
    else:
        mastery_level = "medium"

    medium_accuracy = difficulty_performance["medium"]["accuracy"]
    hard_accuracy = difficulty_performance["hard"]["accuracy"]
    if (
        accuracy >= rules.advanced_accuracy_at_least
        and medium_accuracy >= rules.advanced_medium_accuracy_at_least
        and hard_accuracy >= rules.advanced_hard_accuracy_at_least
    ):
        quiz_difficulty_level = "advanced"
    elif (
        accuracy >= rules.intermediate_accuracy_at_least
        and medium_accuracy >= rules.intermediate_medium_accuracy_at_least
    ):
        quiz_difficulty_level = "intermediate"
    else:
        quiz_difficulty_level = "beginner"

    if (
        mastery_level == "low"
        or repeated_error_count >= rules.high_support_repeated_errors_at_least
        or high_wrong >= rules.high_support_high_confidence_errors_at_least
    ):
        recommended_support_level = "high"
    elif (
        mastery_level == "medium"
        or repeated_error_count >= rules.fallback_repeated_error_minimum
        or high_wrong >= rules.confidence_pattern_min_count
    ):
        recommended_support_level = "medium"
    else:
        recommended_support_level = "low"

    if weak_subconcept:
        recommended_focus = SUBCONCEPT_FOCUS.get(
            weak_subconcept, weak_subconcept.replace("_", " ").title()
        )
    else:
        recommended_focus = "Continue Linear Equation Practice"

    misconception_thresholds = {
        code: {
            "minimum_occurrences": mappings[code].minimum_occurrences
            if code in mappings
            else rules.fallback_repeated_error_minimum,
            "teacher_validated": mappings[code].teacher_validated
            if code in mappings
            else False,
        }
        for code in sorted(misconception_counts)
    }
    evidence = {
        "prototype_rule_version": rules.version,
        "subconcept_performance": subconcept_performance,
        "weak_subconcept_basis": {
            "minimum_attempts": rules.weak_subconcept_min_attempts,
            "accuracy_below": rules.weak_subconcept_accuracy_below,
            "selected": weak_subconcept,
        },
        "difficulty_performance": difficulty_performance,
        "misconception_counts": dict(sorted(misconception_counts.items())),
        "misconception_thresholds": misconception_thresholds,
        "selected_pattern_status": (
            "possible_teacher_validated"
            if selected_source_code
            and selected_source_code in mappings
            and mappings[selected_source_code].teacher_validated
            else "possible_unvalidated"
            if selected_source_code
            else "insufficient_repeated_evidence"
        ),
        "selected_source_misconception_code": selected_source_code,
        "confidence_counts": confidence_counts,
        "confidence_correctness": confidence_correctness,
        "confidence_insight": {
            "kind": insight_kind,
            "high_confidence_incorrect_count": high_wrong,
            "low_confidence_correct_count": low_right,
        },
        "question_evidence": question_evidence,
        "response_time_summary": {
            "average_sec": round(average_time, 2),
            "minimum_sec": min(response_times),
            "maximum_sec": max(response_times),
            "overall_average_sec": round(average_time, 2),
            "minimum_response_time_sec": min(response_times),
            "maximum_response_time_sec": max(response_times),
            "by_subconcept": average_time_by_subconcept,
        },
        "mastery_components": {
            "overall_accuracy": round(accuracy, 4),
            "weighted_difficulty_accuracy": round(weighted_tier_accuracy, 4),
            "accuracy_weight": rules.accuracy_weight,
            "difficulty_weight": rules.difficulty_weight,
        },
    }
    return DiagnosticValues(
        questions_total=rules.expected_questions,
        questions_attempted=attempted,
        correct_answers=correct,
        quiz_accuracy=round(accuracy, 4),
        quiz_avg_response_time_sec=round(average_time, 2),
        quiz_hint_rate=0.0,
        misconception_code=misconception_code,
        repeated_error_count=repeated_error_count,
        weak_subconcept=weak_subconcept,
        quiz_mastery_score=mastery_score,
        mastery_level=mastery_level,
        recommended_support_level=recommended_support_level,
        recommended_focus=recommended_focus,
        confidence_pattern=confidence_pattern,
        quiz_difficulty_level=quiz_difficulty_level,
        diagnostic_evidence=evidence,
    )
