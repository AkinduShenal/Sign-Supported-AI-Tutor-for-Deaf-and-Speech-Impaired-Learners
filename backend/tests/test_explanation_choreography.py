"""Meaning demonstrations must cover all lesson surfaces with truthful context."""
import json
from pathlib import Path

import pytest

from app.modules.tutor.adaptive_lesson import LEVELS, preview_lesson
from app.modules.tutor.content_schemas import AvatarTeachingSegment
from app.modules.tutor.explanation_choreography import choreograph_segments
from app.modules.tutor.knowledge import KNOWLEDGE_PATH
from app.modules.tutor.schemas import TutoringStrategy
from app.modules.tutor.sign_planner import MathSignPlanner


@pytest.mark.parametrize("strategy", list(TutoringStrategy))
@pytest.mark.parametrize("level", LEVELS)
def test_all_authored_explanations_use_the_shared_motion_pipeline(strategy, level):
    lesson = preview_lesson(level, strategy)
    parts = list(lesson.simple_explanation.avatar_segments)
    for example in lesson.worked_examples + [q.worked_solution for q in lesson.practice_questions]:
        parts.extend(example.avatar_intro_segments)
        parts.extend(part for step in example.steps for part in step.avatar_segments)
    parts.extend(part for q in lesson.practice_questions for hint in q.progressive_hints for part in hint.avatar_segments)
    for part in parts:
        if part.support_kind == "expression":
            continue
        assert part.motion is not None, (level, strategy, part.text)
        assert part.text_si
        assert part.sign_actions == [part.motion.clip]
        assert part.motion.beats[0].start == 0
        assert all(b.start >= a.end - .00001 for a, b in zip(part.motion.beats, part.motion.beats[1:]))
        assert all(beat.end > beat.start and beat.text_si for beat in part.motion.beats)
        assert MathSignPlanner().manifest_entry(part.motion.clip)["validation_status"] == "needs_validation"
        if part.motion.clip == "FLOW_READ":
            assert part.text.startswith("Read "), part.text


def test_substitution_uses_original_x_positions_and_the_given_number():
    lesson = preview_lesson("foundation")
    example = lesson.worked_examples[0]
    step = next(s for s in example.steps if s.instruction.startswith("Substitute 4"))
    first = step.avatar_segments[0]
    assert first.motion.clip == "FLOW_SUBSTITUTE_4"
    assert first.motion.original_expression == "x + 3 = 7"
    assert first.motion.substituted_expression == "(4) + 3 = 7"
    assert first.text_si == "ඉහත දැක්වෙන මුල් සමීකරණයේ x වෙනුවට 4 ආදේශ කරන්න."
    assert [beat.role for beat in first.motion.beats] == ["original", "variable", "value", "place", "replaced"]
    assert "4" in first.motion.beats[2].text_si


def test_operation_amounts_have_distinct_numbered_flows():
    results = choreograph_segments([
        AvatarTeachingSegment(text=f"Subtract {n} from both sides.", text_si=f"{n} අඩු කරන්න.", sign_actions=[])
        for n in (2, 3, 4)
    ], original_expression="x + 3 = 7")
    assert [part.motion.clip for part in results] == ["FLOW_SUBTRACT_BOTH_2", "FLOW_SUBTRACT_BOTH_3", "FLOW_SUBTRACT_BOTH_4"]
    assert [part.motion.value for part in results] == ["2", "3", "4"]


def test_all_knowledge_explanation_parts_are_choreographed_without_rewriting_captions():
    corpus = json.loads(Path(KNOWLEDGE_PATH).read_text())
    for chunk in corpus["chunks"]:
        parts = [AvatarTeachingSegment(**part) for part in chunk["avatar_parts"]]
        results = choreograph_segments(parts)
        assert [(p.text, p.text_si) for p in results] == [(p.text, p.text_si) for p in parts]
        assert all(part.motion and part.motion.beats for part in results), chunk["id"]


def test_unreviewed_fraction_is_not_replaced_with_a_digit_gesture():
    part = choreograph_segments([AvatarTeachingSegment(
        text="Substitute -5/2 for x in the original equation.", sign_actions=[],
    )], original_expression="-2x + 3 = 8")[0]
    assert part.motion.clip == "FLOW_SUBSTITUTE"
    assert part.motion.value == "-5/2"
    assert part.motion.substituted_expression == "-2(-5/2) + 3 = 8"
    assert "NUMBER_5" not in part.sign_actions
