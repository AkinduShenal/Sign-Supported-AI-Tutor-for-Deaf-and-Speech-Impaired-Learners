from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_returns_linear_equation_balancing_lesson() -> None:
    response = client.get("/api/v1/tutor/lessons/linear_equation_balancing")

    assert response.status_code == 200
    body = response.json()
    assert body["concept_id"] == "linear_equation_balancing"
    assert body["simple_explanation"]["sign_actions"] == [
        "EQUATION",
        "BOTH_SIDES",
    ]
    assert body["worked_examples"][0]["answer"] == "x = 4"
    assert body["practice_questions"][0]["expected_answer"] == "x = 7"


def test_lesson_contains_expected_pdf_sign_references() -> None:
    response = client.get("/api/v1/tutor/lessons/linear_equation_balancing")

    signs = {
        sign["sign_id"]: (sign["source_page"], sign["source_entry"])
        for sign in response.json()["sign_glossary"]
    }
    assert signs == {
        "ADDITION": (1, 1),
        "SUBTRACTION": (1, 2),
        "MULTIPLICATION": (1, 3),
        "DIVISION": (1, 4),
        "BALANCE": (7, 38),
        "BOTH_SIDES": (7, 38),
        "ALGEBRA": (16, 94),
        "VARIABLE": (16, 94),
        "EQUATION": (17, 97),
        "SUBSTITUTION": (17, 101),
        "NUMBER_3": (2, 11),
        "NUMBER_4": (2, 11),
        "NUMBER_5": (2, 11),
        "NUMBER_7": (2, 11),
    }


def test_equation_steps_have_distinct_ordered_sign_sequences() -> None:
    response = client.get("/api/v1/tutor/lessons/linear_equation_balancing")
    steps = response.json()["worked_examples"][0]["steps"]

    assert steps[2]["expression"] == "x = 4"
    assert steps[2]["sign_actions"] == ["BOTH_SIDES"]
    assert steps[3]["expression"] == "4 + 3 = 7"
    assert steps[3]["sign_actions"] == [
        "SUBSTITUTION",
        "NUMBER_4",
        "VARIABLE",
    ]


def test_all_lesson_sign_actions_have_glossary_entries() -> None:
    response = client.get("/api/v1/tutor/lessons/linear_equation_balancing")
    body = response.json()

    known_signs = {sign["sign_id"] for sign in body["sign_glossary"]}
    used_signs = set(body["simple_explanation"]["sign_actions"])
    for example in body["worked_examples"]:
        for step in example["steps"]:
            used_signs.update(step["sign_actions"])
    for question in body["practice_questions"]:
        used_signs.update(question["hint"]["sign_actions"])

    assert used_signs <= known_signs


def test_unknown_lesson_returns_not_found() -> None:
    response = client.get("/api/v1/tutor/lessons/unknown_concept")

    assert response.status_code == 404
    assert response.json() == {"detail": "Lesson 'unknown_concept' was not found"}
