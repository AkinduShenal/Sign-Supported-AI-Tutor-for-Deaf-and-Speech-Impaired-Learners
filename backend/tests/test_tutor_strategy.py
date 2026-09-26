from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def make_request_payload() -> dict:
    return {
        "student_id": "STU001",
        "concept_id": "linear_equations",
        "quiz": {
            "quiz_session_id": "QUIZ-001",
            "questions_total": 10,
            "questions_attempted": 10,
            "correct_answers": 4,
            "quiz_accuracy": 0.4,
            "quiz_avg_response_time_sec": 42.5,
            "quiz_hint_rate": 0.7,
            "misconception_code": "inverse_operation",
            "quiz_difficulty_level": "beginner",
            "quiz_attempt_count": 2,
            "completed_at": "2026-09-26T10:30:00Z",
        },
        "game": {
            "game_session_id": "GAME-001",
            "tasks_total": 10,
            "tasks_attempted": 8,
            "tasks_completed": 7,
            "successful_tasks": 4,
            "game_success_rate": 0.5,
            "game_completion_rate": 0.7,
            "game_avg_attempts_per_task": 2.5,
            "game_hint_rate": 0.6,
            "game_difficulty_level": "beginner",
            "game_active_time_sec": 420,
            "completed_at": "2026-09-26T11:00:00Z",
        },
        "learner": {
            "prior_mastery_score": 0.35,
            "preferred_mode": "visual",
            "sign_support_required": True,
        },
    }


def test_recommends_step_by_step_for_low_performance() -> None:
    response = client.post("/api/v1/tutor/strategy", json=make_request_payload())

    assert response.status_code == 200
    assert response.json() == {
        "student_id": "STU001",
        "concept_id": "linear_equations",
        "recommended_strategy": "step_by_step",
        "confidence": 1.0,
        "preferred_mode": "visual",
        "sign_support_required": True,
        "model_version": "rule-based-v0",
    }


def test_recommends_advanced_challenge_for_high_performance() -> None:
    payload = make_request_payload()
    payload["quiz"].update(
        {
            "correct_answers": 9,
            "quiz_accuracy": 0.9,
            "quiz_avg_response_time_sec": 15,
            "quiz_hint_rate": 0.1,
            "misconception_code": "none",
            "quiz_difficulty_level": "advanced",
        }
    )
    payload["game"].update(
        {
            "successful_tasks": 7,
            "game_success_rate": 0.9,
            "game_completion_rate": 0.9,
            "game_avg_attempts_per_task": 1.2,
            "game_hint_rate": 0.1,
            "game_difficulty_level": "advanced",
        }
    )
    payload["learner"]["prior_mastery_score"] = 0.9

    response = client.post("/api/v1/tutor/strategy", json=payload)

    assert response.status_code == 200
    assert response.json()["recommended_strategy"] == "advanced_challenge"


def test_rejects_inconsistent_quiz_counts() -> None:
    payload = make_request_payload()
    payload["quiz"]["correct_answers"] = 11

    response = client.post("/api/v1/tutor/strategy", json=payload)

    assert response.status_code == 422
