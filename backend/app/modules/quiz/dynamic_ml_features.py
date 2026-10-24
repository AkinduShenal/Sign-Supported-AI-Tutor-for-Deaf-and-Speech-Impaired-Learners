"""Read-only, versioned predictors for completed PP1 dynamic Quiz sessions.

The bank blueprint is deliberately pinned. A changed bank needs a reviewed schema
version instead of silently reinterpreting logical slots or option tags.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import timezone
from statistics import mean, median, pstdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.quiz.models import (
    QuizQuestion, QuizQuestionOption, QuizResponse, QuizSession,
    QuizSessionQuestion,
)

FEATURE_SCHEMA_VERSION = "quiz_dynamic_features_v1"
SUPPORTED_BANK_VERSION = "pp1_dynamic_v1_DRAFT"
SLOT_BLUEPRINT = {
    "S01": ("one_step_addition", "easy"),
    "S02": ("one_step_subtraction", "easy"),
    "S03": ("one_step_multiplication", "easy"),
    "S04": ("one_step_division", "easy"),
    "S05": ("two_step_equations", "medium"),
    "S06": ("two_step_equations", "medium"),
    "S07": ("two_step_equations", "medium"),
    "S08": ("two_step_equations", "medium"),
    "S09": ("variables_both_sides", "hard"),
    "S10": ("distributive_equations", "hard"),
}
SKILLS = tuple(dict.fromkeys(skill for skill, _ in SLOT_BLUEPRINT.values()))
DIFFICULTIES = ("easy", "medium", "hard")
CONFIDENCES = ("low", "medium", "high")
OPTION_TAGS = (
    "inverse_operation", "sign_error", "arithmetic_error", "concept_confusion",
)

FEATURE_NAMES = (
    "correct_count", "incorrect_count", "accuracy",
    *(f"{tier}_{name}" for tier in DIFFICULTIES
      for name in ("correct_count", "accuracy")),
    *(f"slot_{slot}_correct" for slot in SLOT_BLUEPRINT),
    *(f"skill_{skill}_{name}" for skill in SKILLS
      for name in ("correct_count", "accuracy")),
    "response_time_mean_sec", "response_time_median_sec",
    "response_time_min_sec", "response_time_max_sec",
    "response_time_std_sec", "correct_time_mean_sec",
    "incorrect_time_mean_sec", "first_half_time_mean_sec",
    "second_half_time_mean_sec",
    *(f"confidence_{level}_count" for level in CONFIDENCES),
    "confidence_mean", "high_confidence_wrong_count",
    "low_confidence_correct_count", "confidence_correct_mean",
    "confidence_incorrect_mean",
    *(f"option_{tag}_count" for tag in OPTION_TAGS),
    "repeated_tag_type_count", "repeated_tag_error_count",
    "max_same_tag_count", "max_wrong_streak",
    "first_half_correct_count", "second_half_correct_count",
    "correctness_switch_count", "wrong_after_correct_count",
)


class DynamicFeatureError(ValueError):
    """Saved evidence is incomplete or incompatible with this schema."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DynamicFeatureError(message)


def _average(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _utc(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def extract_dynamic_features(
    quiz_session: QuizSession,
    selections: list[QuizSessionQuestion],
    questions: list[QuizQuestion],
    responses: list[QuizResponse],
    options: list[QuizQuestionOption],
) -> dict:
    """Return metadata and numeric predictors from ten official first answers.

    Option IDs/codes, question variant IDs, learner IDs and timestamps are never
    predictor columns. Tags describe chosen distractors, not teacher labels.
    """
    _require(quiz_session.bank_version == SUPPORTED_BANK_VERSION,
             "Unsupported dynamic bank version")
    _require(quiz_session.status == "completed" and quiz_session.completed_at is not None,
             "Quiz session is incomplete")
    _require(quiz_session.started_at is not None and
             _utc(quiz_session.started_at) <= _utc(quiz_session.completed_at),
             "Invalid session chronology")
    _require(quiz_session.concept_id == "linear_equations" and
             quiz_session.assessment_phase == "pre_tutor",
             "Unsupported concept or assessment phase")
    _require(len(selections) == len(questions) == len(responses) == 10,
             "Expected ten selections, questions and official responses")
    question_by_id = {q.id: q for q in questions}
    _require(len(question_by_id) == 10, "Question IDs are not unique")
    ordered = sorted(selections, key=lambda item: item.question_order)
    _require([item.question_order for item in ordered] == list(range(1, 11)),
             "Invalid saved question order")
    _require(all(item.quiz_session_id == quiz_session.quiz_session_id for item in ordered),
             "Selection belongs to another session")
    _require({item.question_id for item in ordered} == set(question_by_id),
             "Selection/question mapping is inconsistent")

    option_by_id = {option.id: option for option in options}
    _require(len(option_by_id) == 40, "Expected forty unique saved-bank options")
    by_question = {}
    for option in options:
        by_question.setdefault(option.question_id, []).append(option)
    _require(set(by_question) == set(question_by_id), "Option/question mapping is inconsistent")
    for question_id, choices in by_question.items():
        _require(len(choices) == 4 and len({o.option_code for o in choices}) == 4
                 and sum(o.is_correct is True for o in choices) == 1,
                 "Invalid answer options")
        _require(all(o.misconception_code is None if o.is_correct else
                     o.misconception_code in OPTION_TAGS for o in choices),
                 "Unsupported or inconsistent option tag")

    response_by_question = {r.question_id: r for r in responses}
    _require(len(response_by_question) == 10 and
             set(response_by_question) == set(question_by_id),
             "Official response/question mapping is inconsistent")
    seen_slots = set()
    rows = []
    last_answered_at = _utc(quiz_session.started_at)
    for selection in ordered:
        q = question_by_id[selection.question_id]
        r = response_by_question[q.id]
        slot = q.logical_slot
        _require(slot in SLOT_BLUEPRINT and slot not in seen_slots,
                 "Missing, duplicate or unsupported logical slot")
        seen_slots.add(slot)
        expected_skill, expected_tier = SLOT_BLUEPRINT[slot]
        _require(q.bank_version == quiz_session.bank_version and
                 q.concept_id == quiz_session.concept_id and
                 q.subconcept_code == expected_skill and
                 q.difficulty_level == expected_tier and
                 q.question_type == "multiple_choice" and
                 q.assessment_use in ("pre", "both") and
                 re.fullmatch(rf"PP1-DYN-{slot}-V0[1-6]", q.question_code or "") is not None,
                 "Question does not match the versioned bank blueprint")
        _require(r.quiz_session_id == quiz_session.quiz_session_id and
                 r.question_order == selection.question_order and
                 r.selected_option_id in option_by_id and
                 r.answered_at is not None,
                 "Missing or inconsistent first-answer evidence")
        option = option_by_id[r.selected_option_id]
        _require(option.question_id == q.id and r.is_correct is option.is_correct and
                 r.misconception_code == option.misconception_code,
                 "Saved answer disagrees with selected option")
        _require(r.confidence_level in CONFIDENCES and
                 isinstance(r.response_time_sec, (int, float)) and
                 math.isfinite(r.response_time_sec) and r.response_time_sec >= 0,
                 "Invalid confidence or response time")
        answered_at = _utc(r.answered_at)
        _require(last_answered_at <= answered_at <= _utc(quiz_session.completed_at),
                 "Answer timestamps do not follow the saved question order")
        last_answered_at = answered_at
        rows.append((q, r))
    _require(seen_slots == set(SLOT_BLUEPRINT), "Session is missing a logical slot")

    correct = [int(r.is_correct) for _, r in rows]
    times = [float(r.response_time_sec) for _, r in rows]
    confidence_values = {"low": 1, "medium": 2, "high": 3}
    confidence = [confidence_values[r.confidence_level] for _, r in rows]
    tags = Counter(r.misconception_code for _, r in rows if not r.is_correct)
    features = {
        "correct_count": sum(correct),
        "incorrect_count": 10 - sum(correct),
        "accuracy": sum(correct) / 10,
    }
    for tier in DIFFICULTIES:
        tier_rows = [(q, r) for q, r in rows if q.difficulty_level == tier]
        features[f"{tier}_correct_count"] = sum(r.is_correct for _, r in tier_rows)
        features[f"{tier}_accuracy"] = features[f"{tier}_correct_count"] / len(tier_rows)
    for slot in SLOT_BLUEPRINT:
        features[f"slot_{slot}_correct"] = next(int(r.is_correct) for q, r in rows
                                                if q.logical_slot == slot)
    for skill in SKILLS:
        skill_rows = [r for q, r in rows if q.subconcept_code == skill]
        features[f"skill_{skill}_correct_count"] = sum(r.is_correct for r in skill_rows)
        features[f"skill_{skill}_accuracy"] = features[f"skill_{skill}_correct_count"] / len(skill_rows)
    features.update({
        "response_time_mean_sec": mean(times),
        "response_time_median_sec": median(times),
        "response_time_min_sec": min(times),
        "response_time_max_sec": max(times),
        "response_time_std_sec": pstdev(times),
        "correct_time_mean_sec": _average([t for t, c in zip(times, correct) if c]),
        "incorrect_time_mean_sec": _average([t for t, c in zip(times, correct) if not c]),
        "first_half_time_mean_sec": mean(times[:5]),
        "second_half_time_mean_sec": mean(times[5:]),
    })
    for level in CONFIDENCES:
        features[f"confidence_{level}_count"] = sum(r.confidence_level == level
                                                     for _, r in rows)
    features.update({
        "confidence_mean": mean(confidence),
        "high_confidence_wrong_count": sum(r.confidence_level == "high" and not r.is_correct
                                           for _, r in rows),
        "low_confidence_correct_count": sum(r.confidence_level == "low" and r.is_correct
                                            for _, r in rows),
        "confidence_correct_mean": _average([v for v, c in zip(confidence, correct) if c]),
        "confidence_incorrect_mean": _average([v for v, c in zip(confidence, correct) if not c]),
    })
    for tag in OPTION_TAGS:
        features[f"option_{tag}_count"] = tags[tag]
    features["repeated_tag_type_count"] = sum(count >= 2 for count in tags.values())
    features["repeated_tag_error_count"] = sum(count for count in tags.values() if count >= 2)
    features["max_same_tag_count"] = max(tags.values(), default=0)
    streak = maximum = 0
    for value in correct:
        streak = 0 if value else streak + 1
        maximum = max(maximum, streak)
    features.update({
        "max_wrong_streak": maximum,
        "first_half_correct_count": sum(correct[:5]),
        "second_half_correct_count": sum(correct[5:]),
        "correctness_switch_count": sum(a != b for a, b in zip(correct, correct[1:])),
        "wrong_after_correct_count": sum(a == 1 and b == 0
                                         for a, b in zip(correct, correct[1:])),
    })
    _require(set(features) == set(FEATURE_NAMES), "Feature schema mismatch")
    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "bank_version": quiz_session.bank_version,
        "quiz_session_id": quiz_session.quiz_session_id,
        "student_code": quiz_session.student_id,
        "quiz_completed_at": quiz_session.completed_at.isoformat(),
        "feature_names": list(FEATURE_NAMES),
        "features": {name: features[name] for name in FEATURE_NAMES},
    }


def extract_dynamic_features_for_session(database: Session, session_id: str) -> dict:
    """Read a session's immutable selection plan and official response rows."""
    session = database.scalar(select(QuizSession).where(QuizSession.quiz_session_id == session_id))
    _require(session is not None, "Quiz session was not found")
    selections = list(database.scalars(select(QuizSessionQuestion).where(
        QuizSessionQuestion.quiz_session_id == session_id)))
    ids = [item.question_id for item in selections]
    questions = list(database.scalars(select(QuizQuestion).where(QuizQuestion.id.in_(ids))))
    responses = list(database.scalars(select(QuizResponse).where(
        QuizResponse.quiz_session_id == session_id)))
    options = list(database.scalars(select(QuizQuestionOption).where(
        QuizQuestionOption.question_id.in_(ids))))
    return extract_dynamic_features(session, selections, questions, responses, options)
