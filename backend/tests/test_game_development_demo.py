"""Synthetic development evidence only; never opens the genuine Game database."""
import copy
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.modules.game import development_demo as demo
from app.modules.game.models import GameSession, GameResult, GameplayEvent, GameTaskAttempt
from test_game_ml_preview import evidence  # noqa: F401 -- two-mode synthetic fixture

ROOT = Path(__file__).resolve().parents[2]
KEY = "synthetic_demo_verification_key_1234567890"
ARCHIVE = ROOT / "local_ml_artifacts/game_ml_model_export_with_fixtures.zip"
PYTHON = ROOT / "local_ml_artifacts/compatibility_audit/env/Scripts/python.exe"


@pytest.fixture
def runtime(tmp_path):
    settings = demo.DemoSettings(_env_file=None, game_ml_dev_demo_enabled=True,
        game_researcher_verify_key=SecretStr(KEY),
        game_ml_model_archive=ARCHIVE if ARCHIVE.is_file() else Path(sys.executable),
        game_ml_python=PYTHON if PYTHON.is_file() else Path(sys.executable), frontend_url="http://localhost:5173")
    app = demo.create_app(lambda: settings, tmp_path / "demo-only")
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 51000),
                    headers={"Origin": settings.frontend_url}) as client:
        response = client.post(demo.PREFIX + "/bootstrap", json={"development_demo": True})
        assert response.status_code == 200, response.text
        descriptor = response.json()
        client.headers["X-Game-Demo-Capability"] = descriptor["capability"]
        yield client, descriptor, app.state.demo, settings


def start(runtime):
    client, descriptor, _, _ = runtime
    sid = descriptor["session_ids"][0]
    body = {key: descriptor[key] for key in ("student_id", "concept_id", "learning_cycle_id", "assessment_phase")}
    body["client_session_id"] = sid
    response = client.post(demo.PREFIX + "/sessions", json=body)
    assert response.status_code == 201, response.text
    return sid, body


def save(runtime, evidence):
    client, _, _, _ = runtime
    sid, _ = start(runtime)
    _, _, _, events, attempts, _ = evidence
    for event in events:
        response = client.post(demo.PREFIX + "/events", json={
            "game_session_id": sid, "task_id": event.task_id, "event_type": event.event_type,
            "event_timestamp": datetime.now(UTC).isoformat(), "event_payload": event.event_payload})
        assert response.status_code == 201, response.text
    fields = ("task_id", "attempt_number", "attempts_count", "wrong_attempts", "hints_used",
              "skipped_steps", "time_taken_sec", "is_completed", "is_successful", "score",
              "activity_id", "variant_id", "difficulty_level")
    for attempt in attempts:
        response = client.post(demo.PREFIX + "/task-attempts", json={
            "game_session_id": sid, **{name: getattr(attempt, name) for name in fields}})
        assert response.status_code == 201, response.text
    response = client.post(demo.PREFIX + f"/sessions/{sid}/complete")
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["status"] == "completed" and saved["development_demo"] is True
    return sid, {"researcher_key": KEY, "receipt": saved["research_verification"]["receipt"],
                 "confirmed": True, "development_demo": True, "context": {
                     "game_session_id": sid, "student_code": saved["student_id"],
                     **{k: saved[k] for k in ("concept_id", "learning_cycle_id", "assessment_phase")}}}


def snapshot(repository):
    with repository.database(readonly=True) as db:
        return copy.deepcopy([[tuple(getattr(row, c.name) for c in model.__table__.columns)
            for row in db.scalars(select(model).order_by(model.id))]
            for model in (GameSession, GameResult, GameplayEvent, GameTaskAttempt)])


def test_real_frozen_worker_both_modes_and_replay(runtime, evidence):
    if not ARCHIVE.is_file() or not PYTHON.is_file():
        pytest.skip("Local frozen model/runtime unavailable")
    client, _, repository, _ = runtime
    sid, body = save(runtime, evidence)
    before = snapshot(repository)
    response = client.post(demo.PREFIX + f"/sessions/{sid}/research-verification", json=body)
    assert response.status_code == 200, response.text
    prediction = response.json()
    assert prediction["predicted_level"] in {"Beginner", "Intermediate", "Advanced"}
    assert sum(prediction["probabilities"].values()) == pytest.approx(1)
    assert prediction["demo_label"] == demo.LABEL
    assert prediction["classification"] == demo.SCOPE
    assert prediction["model_checksum"] == demo.MODEL_SHA256
    assert snapshot(repository) == before
    with repository.database(readonly=True) as db:
        assert len(db.execute(select(demo.audits)).all()) == 2
    assert client.post(demo.PREFIX + f"/sessions/{sid}/research-verification", json=body).status_code == 409
    assert client.post(demo.PREFIX + f"/sessions/{sid}/complete").json()["research_verification"] is None


def test_disabled_creates_no_storage(tmp_path):
    app = demo.create_app(lambda: demo.DemoSettings(_env_file=None), tmp_path / "absent")
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 51000)) as client:
        assert client.get("/api/v1/health").json()["enabled"] is False
        assert client.post(demo.PREFIX + "/bootstrap", json={"development_demo": True}).status_code == 503
    assert not (tmp_path / "absent").exists()


def test_designation_origin_identity_and_export_boundary(runtime):
    client, _, repository, _ = runtime
    sid, body = start(runtime)
    assert repository.path.name.startswith("development-only-")
    assert client.post(demo.PREFIX + "/sessions", json={**body, "student_id": "STU_037"}).status_code == 400
    assert client.post(demo.PREFIX + "/sessions", json={**body, "client_session_id": str(uuid4())}).status_code == 404
    assert client.get(demo.PREFIX + f"/results/{sid}", headers={"Origin": "https://attacker.example"}).status_code == 403
    assert client.get(demo.PREFIX + f"/results/{sid}", headers={"X-Game-Demo-Capability": "invalid"}).status_code == 404
    assert client.get("/api/v1/game/exports/collection").status_code == 404
    assert client.post(demo.PREFIX + f"/sessions/{sid}/complete").status_code == 409
    assert client.get("/api/v1/game/sessions").status_code == 404


@pytest.mark.parametrize("failure", ["wrong_key", "confirmation", "binding", "expired", "cancelled", "key_rotation", "evidence"])
def test_auth_and_evidence_fail_closed(runtime, evidence, failure, monkeypatch):
    client, _, repository, settings = runtime
    sid, body = save(runtime, evidence)
    def forbidden_worker(*args):
        pytest.fail("Invalid authorization/evidence reached the model")
    monkeypatch.setattr(demo, "run_worker", forbidden_worker)
    expected = 404
    if failure == "wrong_key":
        body["researcher_key"] = "incorrect"
        expected = 401
    elif failure == "confirmation":
        body["confirmed"] = False
        expected = 400
    elif failure == "binding":
        body["context"]["student_code"] = "STU_037"
    elif failure == "expired":
        for receipt in repository.receipts.receipts.values():
            receipt.expires = 0
    elif failure == "cancelled":
        assert client.post(demo.PREFIX + f"/sessions/{sid}/research-verification/cancel",
                           json={"receipt": body["receipt"]}).status_code == 204
    elif failure == "key_rotation":
        settings.game_researcher_verify_key = SecretStr("rotated_demo_verification_key_1234567890")
        body["researcher_key"] = settings.game_researcher_verify_key.get_secret_value()
    else:
        with repository.database() as db:
            result = db.scalar(select(GameResult).where(GameResult.game_session_id == sid))
            result.retry_count += 1
            db.commit()
        expected = 422
    response = client.post(demo.PREFIX + f"/sessions/{sid}/research-verification", json=body)
    assert response.status_code == expected, response.text
    assert KEY not in response.text


def test_remote_client_and_wrong_host_rejected(tmp_path):
    app = demo.create_app(lambda: demo.DemoSettings(_env_file=None), tmp_path / "absent")
    with TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.1", 51000)) as client:
        assert client.get("/api/v1/health").status_code == 403
    with TestClient(app, base_url="http://attacker.example", client=("127.0.0.1", 51000)) as client:
        assert client.get("/api/v1/health").status_code == 403


def test_rate_limit(runtime):
    client, _, _, _ = runtime
    sid, _ = start(runtime)
    endpoint = demo.PREFIX + f"/sessions/{sid}/research-verification"
    for _ in range(5):
        assert client.post(endpoint, json={"researcher_key": "wrong"}).status_code == 401
    assert client.post(endpoint, json={"researcher_key": "wrong"}).status_code == 429
