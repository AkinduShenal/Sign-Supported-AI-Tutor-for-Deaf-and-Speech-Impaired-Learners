"""Variant-invariant feature extraction; all examples use local draft-bank data."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as Row

import pytest

from app.modules.quiz.dynamic_ml_features import (
    DynamicFeatureError, FEATURE_NAMES, FEATURE_SCHEMA_VERSION,
    extract_dynamic_features,
)
from scripts.seed_quiz_dynamic import load_bank


def _evidence(variant: int = 1):
    bank = {q["logical_slot"]: q for q in load_bank()
            if q["question_code"].endswith(f"V{variant:02d}")}
    started = datetime(2026, 10, 21, 10, tzinfo=timezone.utc)
    session = Row(quiz_session_id="QUIZ-test", student_id="STU_999",
                  bank_version="pp1_dynamic_v1_DRAFT", concept_id="linear_equations",
                  assessment_phase="pre_tutor", status="completed",
                  started_at=started,
                  completed_at=started + timedelta(minutes=11))
    selections, questions, responses, options = [], [], [], []
    for order in range(1, 11):
        slot = f"S{order:02d}"
        item = bank[slot]
        question_id = item["question_code"]
        questions.append(Row(id=question_id, question_code=question_id,
                             bank_version=item["bank_version"], logical_slot=slot,
                             concept_id=item["concept_id"],
                             subconcept_code=item["subconcept_code"],
                             difficulty_level=item["difficulty_level"],
                             question_type="multiple_choice", assessment_use="pre"))
        selections.append(Row(quiz_session_id=session.quiz_session_id,
                              question_order=order, question_id=question_id))
        for choice in item["options"]:
            options.append(Row(id=f"{question_id}-{choice['option_code']}",
                               question_id=question_id,
                               option_code=choice["option_code"],
                               is_correct=choice["is_correct"],
                               misconception_code=choice["misconception_code"]))
        # The *semantic* S01 inverse-operation distractor moves between letters.
        selected = next(choice for choice in item["options"]
                        if choice["misconception_code"] == "inverse_operation") \
            if slot == "S01" else next(choice for choice in item["options"]
                                       if choice["is_correct"])
        responses.append(Row(quiz_session_id=session.quiz_session_id,
                             question_id=question_id, question_order=order,
                             selected_option_id=f"{question_id}-{selected['option_code']}",
                             is_correct=selected["is_correct"],
                             misconception_code=selected["misconception_code"],
                             response_time_sec=float(order * 2),
                             confidence_level="high" if order <= 5 else "medium",
                             answered_at=started + timedelta(minutes=order)))
    return session, selections, questions, responses, options


def test_all_six_equivalent_variant_sets_produce_identical_features():
    outputs = [extract_dynamic_features(*_evidence(v)) for v in range(1, 7)]
    assert all(result["features"] == outputs[0]["features"] for result in outputs)
    assert outputs[0]["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert tuple(outputs[0]["features"]) == FEATURE_NAMES
    assert outputs[0]["features"]["option_inverse_operation_count"] == 1
    assert outputs[0]["features"]["correct_count"] == 9
    assert outputs[0]["features"]["slot_S01_correct"] == 0
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))


def test_mixed_variants_across_slots_keep_the_same_semantic_features():
    evidence = _evidence(1)
    for order in range(1, 11):
        replacement = _evidence((order % 6) + 1)
        index = order - 1
        evidence[1][index] = replacement[1][index]
        evidence[2][index] = replacement[2][index]
        evidence[3][index] = replacement[3][index]
        evidence[4][index * 4:index * 4 + 4] = replacement[4][index * 4:index * 4 + 4]
    assert extract_dynamic_features(*evidence)["features"] == \
        extract_dynamic_features(*_evidence(1))["features"]


@pytest.mark.parametrize("mutation", [
    "incomplete", "unsupported_bank", "missing_answer", "extra_answer",
    "wrong_question", "wrong_slot", "wrong_skill", "wrong_tier",
    "wrong_option", "wrong_correctness", "wrong_tag", "wrong_order",
    "missing_confidence", "missing_time", "missing_timestamp", "late_timestamp",
])
def test_rejects_incomplete_or_inconsistent_evidence(mutation):
    session, selections, questions, responses, options = _evidence()
    if mutation == "incomplete":
        session.status = "in_progress"
    elif mutation == "unsupported_bank":
        session.bank_version = "unknown"
    elif mutation == "missing_answer":
        responses.pop()
    elif mutation == "extra_answer":
        responses.append(responses[0])
    elif mutation == "wrong_question":
        responses[0].question_id = "not-in-plan"
    elif mutation == "wrong_slot":
        questions[0].logical_slot = "S02"
    elif mutation == "wrong_skill":
        questions[0].subconcept_code = "two_step_equations"
    elif mutation == "wrong_tier":
        questions[0].difficulty_level = "hard"
    elif mutation == "wrong_option":
        responses[0].selected_option_id = responses[1].selected_option_id
    elif mutation == "wrong_correctness":
        responses[0].is_correct = True
    elif mutation == "wrong_tag":
        responses[0].misconception_code = "sign_error"
    elif mutation == "wrong_order":
        responses[0].question_order = 2
    elif mutation == "missing_confidence":
        responses[0].confidence_level = None
    elif mutation == "missing_time":
        responses[0].response_time_sec = float("nan")
    elif mutation == "missing_timestamp":
        responses[0].answered_at = None
    elif mutation == "late_timestamp":
        responses[0].answered_at = session.completed_at + timedelta(seconds=1)
    with pytest.raises(DynamicFeatureError):
        extract_dynamic_features(session, selections, questions, responses, options)


def test_input_order_does_not_change_saved_question_sequence_features():
    evidence = _evidence()
    baseline = extract_dynamic_features(*evidence)["features"]
    evidence[1].reverse()
    evidence[2].reverse()
    evidence[3].reverse()
    evidence[4].reverse()
    assert extract_dynamic_features(*evidence)["features"] == baseline
