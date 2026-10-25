"""Local-only Game demo ASGI app. Never mounts the research/collection routers.

Run with one worker. Every startup creates a new, isolated SQLite namespace;
no configured DATABASE_URL, historic session, research manifest or export is used.
"""
import hashlib
import json
import os
import secrets
import threading
import time
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Column, JSON, MetaData, String, Table, create_engine, select
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE
from app.db.base import Base
from . import service
from .models import GameResult, GameSession, GameTaskAttempt, GameplayEvent
from .schemas import CreateGameSessionRequest, GameplayEventRequest, GameTaskAttemptRequest
from .ml_preview import read_ml_input_preview
from .research_inference.browser_gate import VerificationStore, config_key, json_body
from .research_inference.contract import KNOWN_EXCLUDED, MODEL_SHA256
from .research_inference.legacy_adapter import adapt_saved_session
from .research_inference.service import PredictionResponse, run_worker

LABEL = "Development Demo — Not Student Assessment"
IDENTITY = "DEMO_TEAM"
SCOPE = "DEVELOPMENT_DEMO_NOT_RESEARCH"
PREFIX = "/api/v1/game/development-demo"
LOCAL = {"localhost", "127.0.0.1", "::1"}
metadata = MetaData()
designations = Table("demo_designations", metadata, Column("session_id", String, primary_key=True),
                     Column("cap_hash", String, nullable=False), Column("cycle", String, nullable=False),
                     Column("created_at", String, nullable=False), Column("classification", String, nullable=False))
audits = Table("demo_approval_audit", metadata, Column("id", String, primary_key=True),
               Column("session_id", String, nullable=False), Column("payload", JSON, nullable=False))


class DemoSettings(BaseSettings):
    game_ml_dev_demo_enabled: bool = False
    game_researcher_verify_key: SecretStr | None = None
    game_ml_research_token: SecretStr | None = None
    game_collection_export_key: SecretStr | None = None
    game_ml_model_archive: Path | None = None
    game_ml_python: Path | None = None
    game_ml_timeout_sec: int = Field(default=60, ge=1, le=60)
    frontend_url: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    @property
    def game_ml_experimental_enabled(self):
        # Only the separate receipt/key primitive sees this alias. This app
        # never calls genuine require_research_access or changes its settings.
        return self.game_ml_dev_demo_enabled


class DemoContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    game_session_id: str
    student_code: str
    concept_id: str
    learning_cycle_id: UUID
    assessment_phase: str


def deny(status=503):
    return HTTPException(status, "Private development demo is unavailable.", headers={"Cache-Control": "no-store"})


def fingerprint(settings):
    return (str(settings.game_ml_model_archive), str(settings.game_ml_python), settings.game_ml_timeout_sec,
            settings.frontend_url, settings.game_ml_dev_demo_enabled)


class DemoRepository:
    def __init__(self, directory):
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        self.lock_file = (directory / "active.lock").open("a+b")
        try:
            self.lock_file.seek(0)
            if os.name == "nt":
                import msvcrt
                self.lock_file.write(b"0"); self.lock_file.flush(); self.lock_file.seek(0)
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.lock_file.close()
            raise RuntimeError("Only one private demo worker may run") from None
        self.path = directory / ("development-only-" + str(uuid4()) + ".sqlite3")
        with self.path.open("xb"):
            pass
        self.engine = create_engine("sqlite:///" + str(self.path), connect_args={"check_same_thread": False}, echo=False, hide_parameters=True)
        Base.metadata.create_all(self.engine, tables=[m.__table__ for m in (GameSession, GameplayEvent, GameTaskAttempt, GameResult)])
        metadata.create_all(self.engine)
        self.capabilities = {}
        self.start_times = deque()
        self.receipts = VerificationStore()
        self.lock = threading.RLock()

    def close(self):
        self.engine.dispose()
        self.lock_file.close()

    def bootstrap(self):
        with self.lock:
            now = time.monotonic()
            self.capabilities = {k: v for k, v in self.capabilities.items() if v["expires"] > now}
            while self.start_times and self.start_times[0] < now - 60:
                self.start_times.popleft()
            if len(self.start_times) >= 20 or len(self.capabilities) >= 64:
                raise deny(429)
            self.start_times.append(now)
            token = secrets.token_urlsafe(32)
            ids = [str(uuid4()) for _ in range(16)]
            record = {"cycle": uuid4(), "ids": ids, "expires": now + 7200}
            self.capabilities[hashlib.sha256(token.encode()).hexdigest()] = record
            return {"capability": token, "session_ids": ids, "student_id": IDENTITY,
                    "learning_cycle_id": str(record["cycle"]), "concept_id": "linear_equations",
                    "assessment_phase": "pre_tutor", "classification": SCOPE, "label": LABEL}

    def audit(self, session_id, decision, **extra):
        with self.engine.begin() as connection:
            connection.execute(audits.insert().values(id=str(uuid4()), session_id=session_id,
                payload={"decision": decision, "at_utc": datetime.now(UTC).isoformat(),
                         "classification": SCOPE, "method": "shared_researcher_key_exact_demo_confirmation",
                         "model_sha256": MODEL_SHA256, **extra}))

    @contextmanager
    def database(self, readonly=False):
        with self.engine.connect() as connection:
            if readonly:
                connection.exec_driver_sql("PRAGMA query_only = ON")
            try:
                with Session(bind=connection, autoflush=False, expire_on_commit=False) as database:
                    yield database
            finally:
                connection.rollback()
                if readonly:
                    connection.exec_driver_sql("PRAGMA query_only = OFF")
                    connection.rollback()


def create_app(settings_provider=DemoSettings, storage_root=None):
    root = Path(storage_root) if storage_root else ENV_FILE.parent / "local_ml_artifacts/development_demo"

    @asynccontextmanager
    async def lifespan(application):
        settings = settings_provider()
        repository = None
        if settings.game_ml_dev_demo_enabled:
            config_key(settings)
            for path in (settings.game_ml_python, settings.game_ml_model_archive):
                if path is None or not path.is_absolute() or not path.is_file():
                    raise RuntimeError("Configure the trusted frozen model and compatible interpreter")
            repository = DemoRepository(root)
        application.state.demo = repository
        try:
            yield
        finally:
            if repository:
                repository.close()

    application = FastAPI(title=LABEL, lifespan=lifespan)
    application.add_middleware(CORSMiddleware, allow_origins=[settings_provider().frontend_url],
        allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Game-Demo-Capability"], allow_credentials=False)

    @application.middleware("http")
    async def local_only(request, call_next):
        settings = settings_provider()
        if (not request.client or request.client.host not in LOCAL or request.url.hostname not in LOCAL
                or request.url.query and request.url.path != PREFIX + "/variant-usage"):
            return Response(status_code=403, headers={"Cache-Control": "no-store"})
        if request.url.path != "/api/v1/health":
            if (not settings.game_ml_dev_demo_enabled or getattr(application.state, "demo", None) is None):
                return Response(status_code=503, headers={"Cache-Control": "no-store"})
            origin = request.headers.get("origin", "")
            if origin != settings.frontend_url.rstrip("/") or urlsplit(origin).hostname not in LOCAL:
                return Response(status_code=403, headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def capability(request, session_id=None):
        repository = application.state.demo
        token = request.headers.get("x-game-demo-capability", "")
        if len(token) > 128:
            raise deny(404)
        hashed = hashlib.sha256(token.encode()).hexdigest()
        record = repository.capabilities.get(hashed)
        if not record or record["expires"] <= time.monotonic() or (session_id is not None and session_id not in record["ids"]):
            raise deny(404)
        if session_id in KNOWN_EXCLUDED:
            raise deny(404)
        return repository, hashed, record

    def designated(database, sid, hashed, record):
        row = database.execute(select(designations).where(designations.c.session_id == sid)).mappings().first()
        parent = database.scalar(select(GameSession).where(GameSession.game_session_id == sid))
        if (row is None or row["cap_hash"] != hashed or row["classification"] != SCOPE or parent is None
                or parent.student_id != IDENTITY or parent.learning_cycle_id != record["cycle"]
                or parent.concept_id != "linear_equations" or parent.assessment_phase != "pre_tutor"):
            raise deny(404)
        return parent

    @application.get("/api/v1/health")
    def health():
        return {"status": "ok", "mode": SCOPE, "enabled": settings_provider().game_ml_dev_demo_enabled}

    @application.post(PREFIX + "/bootstrap")
    async def bootstrap(request: Request):
        data = await json_body(request)
        if data != {"development_demo": True}:
            raise deny(400)
        return application.state.demo.bootstrap()

    @application.post(PREFIX + "/sessions", status_code=201)
    def create(request: Request, body: CreateGameSessionRequest):
        repository, hashed, record = capability(request, str(body.client_session_id))
        if (body.student_id != IDENTITY or body.learning_cycle_id != record["cycle"]
                or body.concept_id != "linear_equations" or body.assessment_phase.value != "pre_tutor"):
            raise deny(400)
        with repository.database() as database:
            prior = database.scalar(select(GameSession).where(GameSession.game_session_id == str(body.client_session_id)))
            if prior:
                designated(database, str(body.client_session_id), hashed, record)
            else:
                database.execute(designations.insert().values(session_id=str(body.client_session_id), cap_hash=hashed,
                    cycle=str(record["cycle"]), created_at=datetime.now(UTC).isoformat(), classification=SCOPE))
            return service.create_game_session(body, database)

    @application.post(PREFIX + "/events", status_code=201)
    def event(request: Request, body: GameplayEventRequest):
        repository, hashed, record = capability(request, body.game_session_id)
        with repository.database() as database:
            designated(database, body.game_session_id, hashed, record)
            try:
                return service.record_game_event(body, database)
            except service.GameEvidenceConflictError:
                raise deny(409) from None

    @application.post(PREFIX + "/task-attempts", status_code=201)
    def attempt(request: Request, body: GameTaskAttemptRequest):
        repository, hashed, record = capability(request, body.game_session_id)
        with repository.database() as database:
            designated(database, body.game_session_id, hashed, record)
            try:
                return service.save_task_attempt(body, database)
            except service.GameEvidenceConflictError:
                raise deny(409) from None

    @application.post(PREFIX + "/sessions/{sid}/complete")
    def complete(sid: str, request: Request):
        repository, hashed, record = capability(request, sid)
        with repository.database() as database:
            parent = designated(database, sid, hashed, record)
            was_completed = parent.status == "completed"
            try:
                saved = service.complete_game_session(sid, database)
            except service.GameEvidenceConflictError:
                raise deny(409) from None
            binding = DemoContext(game_session_id=sid, student_code=IDENTITY, concept_id="linear_equations",
                                  learning_cycle_id=record["cycle"], assessment_phase="pre_tutor")
            receipt = repository.receipts.issue(binding, settings_provider()) if saved.status == "completed" and not was_completed else None
            return {**saved.model_dump(mode="json"), "development_demo": True, "classification": SCOPE,
                    "research_verification": receipt}

    @application.get(PREFIX + "/variant-usage")
    def usage(request: Request):
        repository, _, _ = capability(request)
        with repository.database(readonly=True) as database:
            return {"usage_counts": service.get_variant_usage_counts(IDENTITY, "linear_equations", database)}

    @application.get(PREFIX + "/results/{sid}")
    def result(sid: str, request: Request):
        repository, hashed, record = capability(request, sid)
        with repository.database(readonly=True) as database:
            designated(database, sid, hashed, record)
            try:
                return service.get_game_result(sid, database)
            except service.GameResultNotFoundError:
                raise deny(404) from None

    @application.get(PREFIX + "/results/{sid}/ml-inputs")
    def inputs(sid: str, request: Request):
        repository, hashed, record = capability(request, sid)
        with repository.database(readonly=True) as database:
            designated(database, sid, hashed, record)
            try:
                return read_ml_input_preview(sid, database)
            except service.GameResultNotFoundError:
                raise deny(404) from None

    @application.post(PREFIX + "/sessions/{sid}/research-verification/cancel", status_code=204)
    async def cancel(sid: str, request: Request):
        repository, _, _ = capability(request, sid)
        data = await json_body(request)
        token = data.get("receipt")
        if isinstance(token, str) and len(token) <= 128:
            repository.receipts.revoke(token, sid)
        return Response(status_code=204)

    @application.post(PREFIX + "/sessions/{sid}/research-verification")
    async def verify(sid: str, request: Request):
        repository, hashed, record = capability(request, sid)
        settings = settings_provider()
        data = await json_body(request)
        submitted = data.get("researcher_key", "")
        repository.receipts.authenticate(request.client.host, submitted if isinstance(submitted, str) and len(submitted) <= 256 else "", settings)
        try:
            if (set(data) != {"researcher_key", "receipt", "confirmed", "context", "development_demo"}
                    or data["confirmed"] is not True or data["development_demo"] is not True
                    or not isinstance(data["receipt"], str) or len(data["receipt"]) > 128):
                raise ValueError()
            binding = DemoContext.model_validate(data["context"])
            expected = DemoContext(game_session_id=sid, student_code=IDENTITY, concept_id="linear_equations",
                                   learning_cycle_id=record["cycle"], assessment_phase="pre_tutor")
            if binding != expected:
                raise deny(404)
        except (ValueError, TypeError, KeyError):
            raise deny(400) from None
        receipt = repository.receipts.acquire(data["receipt"], binding, settings)
        del submitted, data
        success = False
        try:
            with repository.database(readonly=True) as database:
                designated(database, sid, hashed, record)
                try:
                    features = adapt_saved_session(sid, database)
                except (ValueError, TypeError, KeyError, ArithmeticError):
                    raise deny(422) from None
            repository.audit(sid, "DEVELOPMENT_APPROVED", context=binding.model_dump(mode="json"),
                             expires_in_seconds=max(0, receipt.expires - time.monotonic()),
                             feature_sha256=hashlib.sha256(json.dumps(features, sort_keys=True).encode()).hexdigest())
            # Slow model execution must not block receipt cancellation/other requests.
            from starlette.concurrency import run_in_threadpool
            output = await run_in_threadpool(run_worker, settings, features)
            current = settings_provider()
            if fingerprint(current) != fingerprint(settings):
                raise deny()
            repository.receipts.valid(receipt, current)
            prediction = PredictionResponse(predicted_level=output["predicted_level"], probabilities=output["probabilities"],
                model_name=output["model_metadata"]["model_name"], model_metadata=output["model_metadata"], runtime=output["runtime"])
            repository.audit(sid, "DEVELOPMENT_INFERENCE_SUCCEEDED", context=binding.model_dump(mode="json"))
            success = True
            return {**prediction.model_dump(mode="json"), "development_demo": True, "classification": SCOPE, "demo_label": LABEL}
        except HTTPException:
            raise
        except Exception:
            raise deny() from None
        finally:
            repository.receipts.finish(receipt, success)

    return application


app = create_app()
