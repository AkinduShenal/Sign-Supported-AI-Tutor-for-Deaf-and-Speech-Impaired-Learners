import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.tutor.sign_planner import (
    BUNDLED_MANIFEST_ROOT,
    CANONICAL_MANIFEST_ROOT,
    MANIFEST_PATH,
    MathSignPlanner,
)


client = TestClient(app)


@pytest.mark.parametrize(
    ("instruction", "expected_actions"),
    [
        (
            "Subtract 3 from both sides",
            ("SUBTRACTION", "NUMBER_3", "BOTH_SIDES"),
        ),
        (
            "Add 4 to both sides",
            ("ADDITION", "NUMBER_4", "BOTH_SIDES"),
        ),
        (
            "Substitute 5 for x",
            ("SUBSTITUTION", "NUMBER_5", "VARIABLE"),
        ),
        (
            "Solve the equation",
            ("SOLVE", "EQUATION"),
        ),
    ],
)
def test_plans_required_teaching_phrases(
    instruction: str,
    expected_actions: tuple[str, ...],
) -> None:
    plan = MathSignPlanner().plan(instruction=instruction)

    assert plan.sign_actions == expected_actions
    assert plan.playable_actions == ()
    assert plan.unavailable_actions == expected_actions
    assert plan.is_fully_supported is False


def test_instruction_is_preferred_over_raw_expression() -> None:
    plan = MathSignPlanner().plan(
        instruction="Subtract 3 from both sides",
        expression="x + 3 - 3 = 7 - 3",
    )

    assert plan.sign_actions == ("SUBTRACTION", "NUMBER_3", "BOTH_SIDES")
    assert len(plan.sign_actions) <= 4


def test_api_reports_unvalidated_actions_without_marking_them_playable() -> None:
    response = client.post(
        "/api/v1/tutor/sign-plan",
        json={"instruction": "Add 4 to both sides"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sign_actions": ["ADDITION", "NUMBER_4", "BOTH_SIDES"],
        "playable_actions": [],
        "unavailable_actions": ["ADDITION", "NUMBER_4", "BOTH_SIDES"],
        "unsupported_actions": [],
        "unsupported_tokens": [],
        "is_fully_supported": False,
    }


def test_reports_unknown_expression_tokens_without_inventing_signs() -> None:
    response = client.post(
        "/api/v1/tutor/sign-plan",
        json={"expression": "y + 3 = 7"},
    )

    assert response.status_code == 200
    assert response.json()["unsupported_tokens"] == ["y"]
    assert response.json()["sign_actions"] == ["ADDITION", "EQUATION"]


def test_manifest_is_loaded_from_avatar_sign_package() -> None:
    assert MANIFEST_PATH.parts[-3:] == (
        "avatar-sign-package",
        "manifest",
        "signs.json",
    )
    assert MANIFEST_PATH.is_file()


def test_bundled_deployment_manifests_match_canonical_package() -> None:
    for filename in ("signs.json", "phrase_map.json"):
        canonical = (CANONICAL_MANIFEST_ROOT / filename).read_bytes()
        bundled = (BUNDLED_MANIFEST_ROOT / filename).read_bytes()
        assert bundled == canonical


def test_rejects_empty_sign_plan_request() -> None:
    response = client.post("/api/v1/tutor/sign-plan", json={})

    assert response.status_code == 422
