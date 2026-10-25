"""No production database. Real frozen artifact tests use the isolated local runtime."""

import copy
import hashlib
import importlib.metadata
import json
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, select

from test_game_ml_preview import evidence as evidence
from app.db.session import get_db
from app.modules.game.models import GameResult, GameSession, GameTaskAttempt, GameplayEvent
from app.modules.game.research_inference.access import ResearchMLSettings, get_research_settings
from app.modules.game.research_inference.contract import CONTRACT, DEPENDENCIES, FEATURE_ORDER, KNOWN_EXCLUDED, MODEL_SHA256, VALIDATED_PYTHON
from app.modules.game.research_inference.legacy_adapter import adapt_saved_session, matches_saved, project_legacy
from app.modules.game.research_inference.service import run_worker
from app.modules.game.research_inference.worker import WorkerUnavailable, check_metadata, check_runtime
from app.modules.game.router import router

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "local_ml_artifacts/game_ml_model_export_with_fixtures.zip"
PYTHON = ROOT / "local_ml_artifacts/compatibility_audit/env/Scripts/python.exe"
TOKEN = "synthetic-research-token-only-for-tests-123456789"


def test_invalid_environment_configuration_is_non_disclosing(monkeypatch):
    def invalid_settings():
        raise ValueError("private internal configuration path")
    monkeypatch.setattr("app.modules.game.research_inference.access.ResearchMLSettings", invalid_settings)
    with pytest.raises(HTTPException) as caught:
        get_research_settings()
    assert caught.value.status_code == 503
    assert caught.value.headers["Cache-Control"] == "no-store"
    assert "private" not in caught.value.detail


@pytest.fixture
def harness(evidence, tmp_path):
    db, session, *_ = evidence
    manifest = {
        "schema_version": "game-ml-research-access-v1", "feature_contract": CONTRACT,
        "approved_by": "SYNTHETIC TEST OPERATOR", "approval_reference": "SYNTHETIC FIXTURE ONLY",
        "approved_at": "2026-10-22T00:00:00Z", "legacy_contract_accepted": True,
        "excluded_session_ids": [], "quarantined_session_ids": [],
        "approved_sessions": [{"game_session_id": session.game_session_id, "student_code": session.student_id,
                               "concept_id": session.concept_id, "learning_cycle_id": str(session.learning_cycle_id),
                               "assessment_phase": session.assessment_phase}],
    }
    path = tmp_path / "synthetic-approvals.json"
    placeholder = tmp_path / "unloadable-artifact.zip"
    placeholder.write_bytes(b"not a model; access-control tests never load this")
    settings = ResearchMLSettings(_env_file=None, game_ml_experimental_enabled=True,
                                  game_ml_research_token=TOKEN, game_ml_session_manifest=path,
                                  game_ml_model_archive=ARCHIVE if ARCHIVE.exists() else placeholder,
                                  game_ml_python=PYTHON if PYTHON.exists() else Path(sys.executable),
                                  game_ml_timeout_sec=60)
    def approve():
        data = json.dumps(manifest).encode()
        path.write_bytes(data)
        settings.game_ml_manifest_sha256 = hashlib.sha256(data).hexdigest()
    approve()
    calls = []
    def database():
        calls.append("database dependency")
        yield db
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_research_settings] = lambda: settings
    with TestClient(app) as client:
        yield SimpleNamespace(db=db, session=session, settings=settings, manifest=manifest, approve=approve,
                              calls=calls, client=client, evidence=evidence,
                              url=f"/api/v1/game/sessions/{session.game_session_id}/ml-prediction")


def request(harness, token=TOKEN):
    return harness.client.get(harness.url, headers={"Authorization": f"Bearer {token}"} if token else {})


def test_disabled_before_lookup(harness):
    harness.settings.game_ml_experimental_enabled = False
    response = request(harness)
    assert response.status_code == 503 and response.headers["Cache-Control"] == "no-store"
    assert harness.calls == []


@pytest.mark.parametrize("token", [None, "incorrect-research-token"])
def test_authentication_before_lookup(harness, token):
    response = request(harness, token)
    assert response.status_code == 401 and response.headers["Cache-Control"] == "no-store"
    assert harness.calls == [] and harness.session.game_session_id not in response.text


@pytest.mark.parametrize("padding", ["", "  "])
def test_export_token_cannot_be_reused(harness, padding):
    harness.settings.game_collection_export_key = SecretStr(padding + TOKEN + padding)
    assert request(harness).status_code == 503
    assert harness.calls == []


@pytest.mark.parametrize("failure", ["missing", "bad_pin", "invalid_student", "wrong_contract", "not_accepted", "duplicate"])
def test_invalid_approval_configuration_before_lookup(harness, failure):
    if failure == "missing":
        harness.settings.game_ml_session_manifest = None
    elif failure == "bad_pin":
        harness.settings.game_ml_manifest_sha256 = "0" * 64
    else:
        if failure == "invalid_student":
            harness.manifest["approved_sessions"][0]["student_code"] = "STU_0014"
        elif failure == "wrong_contract":
            harness.manifest["feature_contract"] = "unverified-contract"
        elif failure == "not_accepted":
            harness.manifest["legacy_contract_accepted"] = False
        else:
            harness.manifest["approved_sessions"].append(harness.manifest["approved_sessions"][0].copy())
        harness.approve()
    response = request(harness)
    assert response.status_code == 503 and response.headers["Cache-Control"] == "no-store"
    assert harness.calls == []


@pytest.mark.parametrize("failure", ["unapproved", "excluded", "quarantined", "known_quarantine"])
def test_denied_sessions_before_lookup(harness, failure):
    sid = harness.session.game_session_id
    if failure == "unapproved":
        harness.manifest["approved_sessions"] = []
    elif failure == "known_quarantine":
        sid = sorted(KNOWN_EXCLUDED)[0]
        harness.manifest["approved_sessions"][0]["game_session_id"] = sid
        harness.url = f"/api/v1/game/sessions/{sid}/ml-prediction"
    else:
        harness.manifest["excluded_session_ids" if failure == "excluded" else "quarantined_session_ids"] = [sid]
    harness.approve()
    response = request(harness)
    assert response.status_code == 404 and response.headers["Cache-Control"] == "no-store"
    assert harness.calls == []


@pytest.mark.parametrize("field", ["student_code", "concept_id", "learning_cycle_id", "assessment_phase"])
def test_manifest_context_mismatch(harness, field):
    replacements = {"student_code": "STU_998", "concept_id": "other-concept",
                    "learning_cycle_id": "00000000-0000-0000-0000-000000000000", "assessment_phase": "post_tutor"}
    harness.manifest["approved_sessions"][0][field] = replacements[field]
    harness.approve()
    response = request(harness)
    assert response.status_code == 404 and response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("failure", ["incomplete", "missing_result", "missing_outcome", "chronology", "aggregate", "malformed_payload"])
def test_invalid_saved_evidence_never_invokes_worker(harness, failure, monkeypatch):
    db, session, result, events, *_ = harness.evidence
    if failure == "incomplete":
        session.status = "in_progress"
    elif failure == "missing_result":
        db.delete(result)
    elif failure == "missing_outcome":
        db.delete(next(e for e in events if e.event_type == "ANSWER_INCORRECT"))
    elif failure == "chronology":
        next(e for e in events if e.event_type == "ANSWER_INCORRECT").event_timestamp += timedelta(hours=1)
    elif failure == "aggregate":
        result.total_hint_count = 15
    else:
        events[0].event_payload = []
    db.commit()
    def prohibit(*args):
        raise AssertionError("Invalid evidence must not invoke a model")
    monkeypatch.setattr("app.modules.game.research_inference.service.run_worker", prohibit)
    response = request(harness)
    assert response.status_code == 422 and response.headers["Cache-Control"] == "no-store"


def test_saved_float_precision_is_not_a_conflict():
    # PostgreSQL returned 2.33333333333333 for a saved 14/6 average.
    assert matches_saved(2.33333333333333, 14 / 6)
    assert not matches_saved(14 / 6 + 0.001, 14 / 6)
    assert not matches_saved(15, 14) and matches_saved(6, 6)


@pytest.mark.parametrize("offset,status", [(None, 200), (0.001, 422)])
def test_storage_rounded_average_still_predicts(harness, offset, status, monkeypatch):
    db, session, result, *_ = harness.evidence
    exact = result.game_avg_attempts_per_task
    result.game_avg_attempts_per_task = float(f"{exact:.15g}") if offset is None else exact + offset
    db.commit()
    if status == 422:
        def prohibit(*args):
            raise AssertionError("Invalid evidence must not invoke a model")
        monkeypatch.setattr("app.modules.game.research_inference.service.run_worker", prohibit)
    assert request(harness).status_code == status


@pytest.fixture(scope="session")
def actual_settings():
    if not ARCHIVE.is_file() or not PYTHON.is_file():
        pytest.skip("Trusted local frozen archive/isolated runtime not installed; never download or replace them")
    return ResearchMLSettings(_env_file=None, game_ml_model_archive=ARCHIVE, game_ml_python=PYTHON, game_ml_timeout_sec=60)


@pytest.fixture(scope="session")
def actual_verification(actual_settings):
    return run_worker(actual_settings, None)


def test_ten_frozen_predictions_and_probabilities(actual_verification):
    with ZipFile(ARCHIVE) as archive:
        frozen = json.loads(archive.read("frozen_predictions.json"))
    actual = actual_verification["frozen_reproduction"]
    assert actual["records"] == 10
    assert actual["predictions"] == [r["expected_prediction"] for r in frozen["records"]]
    assert actual["probabilities"] == [[r["expected_probabilities"][c] for c in frozen["class_order"]] for r in frozen["records"]]
    assert actual["maximum_probability_difference"] == 0.0
    assert actual_verification["model_checksum"] == MODEL_SHA256
    assert actual_verification["runtime"]["dependencies"] == DEPENDENCIES


def database_snapshot(db):
    # Table values avoid identity-map timezone differences after rollback in SQLite.
    return copy.deepcopy({cls.__tablename__: [dict(row) for row in db.execute(select(cls.__table__)).mappings()]
                          for cls in (GameSession, GameResult, GameTaskAttempt, GameplayEvent)})


def test_full_real_model_path_matches_offline_and_does_not_write(harness, actual_settings):
    harness.settings.game_ml_python = actual_settings.game_ml_python
    harness.settings.game_ml_model_archive = actual_settings.game_ml_model_archive
    features = adapt_saved_session(harness.session.game_session_id, harness.db)
    offline = run_worker(actual_settings, features)
    before = database_snapshot(harness.db)
    statements = []
    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(harness.db.get_bind(), "before_cursor_execute", record)
    try:
        response = request(harness)
    finally:
        event.remove(harness.db.get_bind(), "before_cursor_execute", record)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["predicted_level"] == offline["predicted_level"]
    assert result["probabilities"] == offline["probabilities"]
    assert result["model_metadata"] == offline["model_metadata"]
    assert result["model_status"] == "EXPERIMENTAL_NOT_PRODUCTION_APPROVED"
    assert result["status"] == "experimental_prediction" and result["teacher_verified"] is False
    assert result["feature_source"] == "validated_saved_game_session" and result["feature_contract"] == CONTRACT
    assert response.headers["Cache-Control"] == "no-store"
    assert before == database_snapshot(harness.db)
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
    assert TOKEN not in response.text and harness.session.game_session_id not in response.text
    assert harness.session.student_id not in response.text and str(ARCHIVE) not in response.text


def test_missing_model_and_checksum_failure(actual_settings, tmp_path):
    settings = actual_settings.model_copy()
    settings.game_ml_model_archive = tmp_path / "missing-model.zip"
    with pytest.raises(HTTPException) as missing:
        run_worker(settings, None)
    assert missing.value.status_code == 503
    broken = tmp_path / "invalid-checksum-test-only.zip"
    with ZipFile(ARCHIVE) as source, ZipFile(broken, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            target.writestr(name, data + b"invalid-checksum" if name.endswith(".joblib") else data)
    settings.game_ml_model_archive = broken
    with pytest.raises(HTTPException) as mismatch:
        run_worker(settings, None)
    assert mismatch.value.status_code == 503 and str(broken) not in mismatch.value.detail


def test_unverified_backend_runtime_cannot_load_model(actual_settings):
    installed = {name: importlib.metadata.version(name) for name in DEPENDENCIES}
    if installed == DEPENDENCIES:
        pytest.skip("Backend runtime already matches pins; version rejection is covered directly")
    settings = actual_settings.model_copy(update={"game_ml_python": Path(sys.executable)})
    with pytest.raises(HTTPException) as mismatch:
        run_worker(settings, None)
    assert mismatch.value.status_code == 503


@pytest.mark.parametrize("failure", ["features", "classes", "dependency", "python"])
def test_order_class_and_runtime_fail_closed(failure):
    if failure in ("features", "classes"):
        if not ARCHIVE.is_file():
            pytest.skip("Frozen metadata unavailable")
        with ZipFile(ARCHIVE) as archive:
            metadata = json.loads(archive.read("model_metadata.json"))
        metadata["feature_names" if failure == "features" else "classes"].reverse()
        with pytest.raises(WorkerUnavailable):
            check_metadata(metadata)
    else:
        versions = DEPENDENCIES.copy()
        if failure == "dependency":
            versions["numpy"] = "unverified-version"
        with pytest.raises(WorkerUnavailable):
            check_runtime(versions, "0.0.0" if failure == "python" else VALIDATED_PYTHON)


def test_eighteen_legacy_workbook_vectors_match_integrated_projection():
    folder = ROOT / "local_ml_artifacts/legacy_adapter_prototype"
    if not (folder / "compare_workbook.py").is_file():
        pytest.skip("Private historical workbook/export fixture unavailable")
    sys.path.insert(0, str(folder))
    try:
        from compare_workbook import inputs
        cases, _ = inputs()
        for session, results, answers, events, code, excluded, expected in cases:
            first = [a for a in answers if a["attempt_number"] == "1"]
            source = results[0]
            values = {name: float(source[name]) if name in ("game_success_rate", "game_hint_rate", "game_avg_attempts_per_task")
                      else int(source[name]) for name in FEATURE_ORDER if name != "first_attempt_accuracy"}
            values["first_attempt_accuracy"] = sum(a["is_correct"] == "True" for a in first) / len(first)
            assert project_legacy(values, int(source["tasks_total"])) == {name: expected[name] for name in FEATURE_ORDER}
        assert len(cases) == 18
    finally:
        sys.path.remove(str(folder))
