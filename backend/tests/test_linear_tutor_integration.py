"""
Integration tests for the Linear Equation AI Tutor service within the main FastAPI backend.
"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_main_backend_health():
    """Verify standard backend health check."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_linear_tutor_health():
    """Verify linear equation tutor health check endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_linear_tutor_categories():
    """Verify categories endpoint."""
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert len(data["categories"]) == 6


def test_linear_tutor_quiz():
    """Verify quiz generation for a category."""
    resp = client.get("/api/quiz/single_variable?count=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "single_variable"
    assert len(data["questions"]) == 3


def test_linear_tutor_evaluation():
    """Verify evaluation endpoint from the main backend app."""
    payload = {
        "user_id": "test_integration_user",
        "questions": [
            {
                "question_id": "q1",
                "question": "x + 2 = 5",
                "correct_answer": "x = 3",
                "user_answer": "x = 3",
                "category": "single_variable"
            }
        ]
    }
    resp = client.post("/api/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "test_integration_user"
    assert data["is_perfect"] is True
    assert data["overall_accuracy"] == 100.0
