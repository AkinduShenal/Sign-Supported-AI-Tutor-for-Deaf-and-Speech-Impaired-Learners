"""Synthetic saved sessions only. A completion receipt is the only browser credential."""
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from test_game_ml_preview import evidence as evidence
from test_game_research_inference import harness as harness
from app.core.config import settings as app_settings
from app.modules.game.models import GameSession, GameResult, GameTaskAttempt, GameplayEvent
from app.modules.game.research_inference import browser_gate as gate, service
from app.modules.game.research_inference.access import ApprovedSession
from app.modules.game.service import _to_session_response


@pytest.fixture
def browser(harness, monkeypatch):
    h = harness
    clock = [100.0]
    memory = gate.VerificationStore(clock=lambda: clock[0], fingerprint=gate.model_fingerprint)
    monkeypatch.setattr(gate, "store", memory)
    monkeypatch.setattr(gate, "get_research_settings", lambda: h.settings)
    # No manifest is configured: the receipt alone approves its own session.
    h.settings.game_ml_session_manifest = None
    h.settings.game_ml_manifest_sha256 = None
    binding = ApprovedSession.model_validate(h.manifest["approved_sessions"][0])
    receipt = memory.issue(binding, h.settings)
    body = {"receipt": receipt["receipt"], "context": binding.model_dump(mode="json")}
    output = {"predicted_level": "Intermediate", "probabilities": {"Beginner": .2, "Intermediate": .6, "Advanced": .2},
              "model_metadata": {"model_name": "SYNTHETIC WORKER TEST ONLY"}, "runtime": {"python": "test"}}
    worker_calls = []
    real_worker = service.run_worker
    def worker(settings, features):
        worker_calls.append(copy.deepcopy(features))
        return copy.deepcopy(output)
    monkeypatch.setattr(service, "run_worker", worker)
    with TestClient(h.client.app, base_url="https://testserver", headers={"Origin": app_settings.frontend_url.rstrip("/")}) as client:
        yield SimpleNamespace(h=h, client=client, memory=memory, clock=clock, body=body, binding=binding,
                              calls=worker_calls, worker=worker, real_worker=real_worker,
                              url=h.url.replace("ml-prediction", "research-verification"), output=output)


def post(b, **changes):
    return b.client.post(b.url, json={**b.body, **changes})


def test_success_mapping_replay_and_no_writes(browser, caplog):
    b = browser
    models = (GameSession, GameResult, GameTaskAttempt, GameplayEvent)
    def snapshot():
        # Raw table values keep SQLite's timezone coercion out of the comparison.
        return [[dict(row) for row in b.h.db.execute(select(model.__table__)).mappings()] for model in models]
    before = snapshot()
    writes = []
    def audit(conn, cursor, statement, params, context, many):
        if statement.split()[0].upper() != "SELECT": writes.append(statement.split()[0])
    event.listen(b.h.db.get_bind(), "before_cursor_execute", audit)
    try:
        response = post(b)
        assert response.status_code == 200
        assert response.json()["predicted_level"] == "Intermediate"
        assert response.json()["probabilities"] == b.output["probabilities"]
        assert response.json()["teacher_verified"] is False
        assert response.headers["cache-control"] == "no-store"
        assert len(b.calls) == 1 and len(b.calls[0]) == 9
        assert snapshot() == before and writes == []
        assert post(b).status_code == 409
        assert b.body["receipt"] not in response.text and b.body["receipt"] not in caplog.text
    finally:
        event.remove(b.h.db.get_bind(), "before_cursor_execute", audit)


@pytest.mark.parametrize("change,status", [({"receipt": "unknown"}, 404), ({"researcher_key": "not used"}, 400),
    ({"confirmed": True}, 400), ({"extra": "not permitted"}, 400)])
def test_reject_before_db(browser, change, status):
    b = browser
    response = post(b, **change)
    assert response.status_code == status and b.h.calls == [] and b.calls == []
    assert response.headers["cache-control"] == "no-store"


def test_disabled_and_missing_runtime(browser):
    b = browser
    b.h.settings.game_ml_experimental_enabled = False
    assert post(b).status_code == 503
    b.h.settings.game_ml_experimental_enabled = True
    archive = b.h.settings.game_ml_model_archive
    b.h.settings.game_ml_model_archive = None
    assert post(b).status_code == 503 and b.calls == []
    b.h.settings.game_ml_model_archive = archive


def test_store_capacity_and_duplicate_flight(browser):
    b = browser
    lease = b.memory.acquire(b.body["receipt"], b.binding, b.h.settings)
    with pytest.raises(HTTPException) as failure:
        b.memory.acquire(b.body["receipt"], b.binding, b.h.settings)
    assert failure.value.status_code == 409
    b.memory.finish(lease, False)
    for index in range(gate.MAX_RECEIPTS - 1):
        binding = b.binding.model_copy(update={"game_session_id": str(__import__('uuid').UUID(int=index + 1))})
        assert b.memory.issue(binding, b.h.settings)
    assert len(b.memory.receipts) == gate.MAX_RECEIPTS
    assert b.memory.issue(b.binding.model_copy(update={"game_session_id": "capacity-overflow"}), b.h.settings) is None


def test_excluded_sessions_are_denied(browser, monkeypatch):
    b = browser
    monkeypatch.setattr(gate, "KNOWN_EXCLUDED", frozenset({b.binding.game_session_id}))
    assert post(b).status_code == 404 and b.calls == []


@pytest.mark.parametrize("field,value", [("student_code", "STU_998"), ("concept_id", "other"),
    ("learning_cycle_id", "00000000-0000-0000-0000-000000000000"), ("assessment_phase", "post_tutor")])
def test_exact_context_binding(browser, field, value):
    b = browser
    assert post(b, context={**b.body["context"], field: value}).status_code == 404
    assert b.h.calls == []


def test_malformed_code_and_wrong_session_receipt(browser):
    b = browser
    assert post(b, context={**b.body["context"], "student_code": "STU_0014"}).status_code == 400
    other = ApprovedSession.model_validate({**b.body["context"], "game_session_id": "00000000-0000-0000-0000-000000000000"})
    token = b.memory.issue(other, b.h.settings)
    assert post(b, receipt=token["receipt"]).status_code == 404 and b.h.calls == []


@pytest.mark.parametrize("kind", ["incomplete", "missing_outcome", "chronology", "aggregate", "missing_result"])
def test_strict_saved_validation(browser, kind):
    b = browser
    db, session, result, events, *_ = b.h.evidence
    if kind == "incomplete": session.status = "in_progress"
    elif kind == "missing_result": db.delete(result)
    elif kind == "aggregate": result.total_hint_count += 1
    elif kind == "missing_outcome": db.delete(next(e for e in events if e.event_type == "ANSWER_INCORRECT"))
    else:
        row = next(e for e in events if e.event_type == "ANSWER_CORRECT")
        row.event_payload = {**row.event_payload, "attempt_number": 99}
    db.commit()
    assert post(b).status_code == 422 and not b.calls


@pytest.mark.parametrize("kind", ["expired", "cancelled", "model_changed"])
def test_expired_revoked_or_stale_receipt(browser, kind):
    b = browser
    if kind == "expired": b.clock[0] += gate.TTL_SECONDS + 1
    elif kind == "cancelled":
        assert b.client.post(b.url + "/cancel", json={"receipt": b.body["receipt"]}).status_code == 204
    else: b.h.settings.game_ml_python = Path(__file__).resolve()
    assert post(b).status_code == 404 and b.h.calls == []


def test_failure_releases_lease_and_allows_retry(browser, monkeypatch):
    b = browser
    def fail(*args): raise HTTPException(503, "Model unavailable")
    monkeypatch.setattr(service, "run_worker", fail)
    assert post(b).status_code == 503
    monkeypatch.setattr(service, "run_worker", b.worker)
    assert post(b).status_code == 200


@pytest.mark.parametrize("kind", ["cancel", "disable"])
def test_revalidate_after_slow_worker(browser, monkeypatch, kind):
    b = browser
    def change(settings, features):
        if kind == "cancel": b.memory.revoke(b.body["receipt"], b.binding.game_session_id)
        else: b.h.settings.game_ml_experimental_enabled = False
        return b.worker(settings, features)
    monkeypatch.setattr(service, "run_worker", change)
    response = post(b)
    assert response.status_code in (404, 503) and "predicted_level" not in response.text


def test_remote_http_bad_origin_and_bad_json(browser):
    b = browser
    assert b.client.post(b.url, json=b.body, headers={"Origin": "https://attacker.invalid"}).status_code == 403
    with TestClient(b.h.client.app, base_url="http://remote.invalid", headers={"Origin": app_settings.frontend_url}) as client:
        assert client.post(b.url, json=b.body).status_code == 403
    assert b.client.post(b.url, content='{"receipt":', headers={"Content-Type": "application/json"}).status_code == 400
    assert b.h.calls == []


@pytest.mark.parametrize("client_host,container,status", [("172.17.0.1", False, 403), ("172.17.0.1", True, 200),
    ("192.168.65.1", True, 200), ("8.8.8.8", True, 403), ("not-an-ip", True, 403)])
def test_docker_bridge_client_needs_container_flag(browser, client_host, container, status):
    b = browser
    b.h.settings.game_ml_container_network = container
    with TestClient(b.h.client.app, base_url="http://localhost:8000", client=(client_host, 50000),
                    headers={"Origin": app_settings.frontend_url.rstrip("/")}) as client:
        assert client.post(b.url, json=b.body).status_code == status


def test_receipt_only_for_newly_acknowledged_completion(browser):
    b = browser
    # Existing historical completed sessions can never mint a fresh receipt.
    saved = _to_session_response(b.h.session)
    assert gate.issue_completion_receipt(saved, False) is None
    # The synthetic route can transition a fresh session; no genuine DB is used.
    b.h.session.status = "in_progress"
    b.h.db.commit()
    b.memory.receipts.clear()
    response = b.client.post(b.url.replace("research-verification", "complete"))
    assert response.status_code == 200 and response.json()["status"] == "completed"
    assert response.json()["research_verification"]["receipt"]
    again = b.client.post(b.url.replace("research-verification", "complete"))
    assert again.status_code == 200 and again.json()["research_verification"] is None


def test_no_receipt_when_prediction_is_disabled(browser):
    b = browser
    b.h.settings.game_ml_experimental_enabled = False
    b.h.session.status = "in_progress"
    b.h.db.commit()
    response = b.client.post(b.url.replace("research-verification", "complete"))
    assert response.status_code == 200 and response.json()["research_verification"] is None


def test_real_frozen_model_on_synthetic_session(browser, monkeypatch):
    b = browser
    if not b.h.settings.game_ml_model_archive.name.endswith("with_fixtures.zip"):
        pytest.skip("Private trusted model/runtime not installed")
    captured = []
    def actual(settings, features):
        captured.append(features)
        return b.real_worker(settings, features)
    monkeypatch.setattr(service, "run_worker", actual)
    response = post(b)
    assert response.status_code == 200
    offline = b.real_worker(b.h.settings, captured[0])
    assert response.json()["predicted_level"] == offline["predicted_level"]
    assert response.json()["probabilities"] == offline["probabilities"]
    assert offline["frozen_reproduction"]["maximum_probability_difference"] == 0.0
