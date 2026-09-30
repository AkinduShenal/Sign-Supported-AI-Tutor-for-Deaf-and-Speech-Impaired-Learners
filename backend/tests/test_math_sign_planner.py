from fastapi.testclient import TestClient

from app.main import app
from app.modules.tutor.sign_planner import MathSignPlanner


client = TestClient(app)


def test_builds_ordered_signs_from_math_expression() -> None:
    plan = MathSignPlanner().plan(expression="4 + 3 = 7")

    assert plan.sign_actions == (
        "NUMBER_4",
        "ADDITION",
        "NUMBER_3",
        "EQUATION",
        "NUMBER_7",
    )
    assert plan.is_fully_supported is True


def test_adds_instruction_context_before_expression() -> None:
    plan = MathSignPlanner().plan(
        instruction="Substitute 4 for x to check the answer.",
        expression="4 + 3 = 7",
    )

    assert plan.sign_actions[:2] == ("SUBSTITUTION", "ALGEBRA")
    assert plan.sign_actions[2:] == (
        "NUMBER_4",
        "ADDITION",
        "NUMBER_3",
        "EQUATION",
        "NUMBER_7",
    )


def test_reports_actions_without_approved_animations() -> None:
    response = client.post(
        "/api/v1/tutor/sign-plan",
        json={"expression": "x / 5 = 12"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sign_actions": [
            "ALGEBRA",
            "DIVISION",
            "NUMBER_5",
            "EQUATION",
            "NUMBER_1",
            "NUMBER_2",
        ],
        "unsupported_actions": ["DIVISION", "NUMBER_1", "NUMBER_2"],
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
    assert "ALGEBRA" not in response.json()["sign_actions"]


def test_rejects_empty_sign_plan_request() -> None:
    response = client.post("/api/v1/tutor/sign-plan", json={})

    assert response.status_code == 422
