"""Equation alignment regressions; these do not certify SLSL fluency."""
import pytest

from app.modules.tutor.adaptive_lesson import preview_lesson
from app.modules.tutor.teaching_explanations import expression_segment


@pytest.mark.parametrize("expression", ["x + 3 = 7", "x=4", "x + 3 - 3 = 7 - 3", "2x = -5/2", "(x + 12) / 3 = 0.5"])
def test_tokens_reconstruct_expression_with_stable_action_positions(expression):
    segment = expression_segment(expression)
    cursor, reconstructed, action_indices = 0, "", []
    for token in segment.expression_tokens:
        reconstructed += expression[cursor:token.start] + token.text
        assert token.text == expression[token.start:token.end]
        cursor = token.end
        if token.action_index is not None:
            action_indices.append(token.action_index)
        else:
            assert token.text in segment.unsupported_tokens
    reconstructed += expression[cursor:]
    assert reconstructed == expression
    assert action_indices == list(range(len(segment.sign_actions)))


def test_each_worked_step_reads_its_own_expression_including_final_answer():
    lesson = preview_lesson("foundation")
    for example in lesson.worked_examples:
        for step in example.steps:
            readings = [part for part in step.avatar_segments if part.support_kind == "expression"]
            assert len(readings) == 1
            assert readings[0].expression == step.expression
    solved = next(step for step in lesson.worked_examples[0].steps if step.expression == "x = 4")
    reading = next(part for part in solved.avatar_segments if part.support_kind == "expression")
    assert reading.sign_actions == ["VARIABLE", "EQUATION", "NUMBER_4"]


def test_glossary_references_are_slsl_and_never_certify_prototype_motion():
    references = preview_lesson("foundation").sign_glossary
    seven = next(ref for ref in references if ref.sign_id == "NUMBER_7")
    assert seven.validation_status == "pending"
    assert {video["source"] for video in seven.reference_videos} == {"SLSL Dictionary", "Sign Math"}
    assert all(video["language"] == "sqs" for video in seven.reference_videos)


def test_introduction_readings_stay_with_the_selected_example_or_practice():
    lesson = preview_lesson("foundation")
    examples = lesson.worked_examples + [q.worked_solution for q in lesson.practice_questions]
    for example in examples:
        readings = [part for part in example.avatar_intro_segments if part.support_kind == "expression"]
        assert len(readings) == 1
        assert readings[0].expression == example.problem
        assert readings[0].expression != example.answer
