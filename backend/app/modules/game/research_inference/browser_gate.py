"""Game prediction for a just-completed session. Nothing is persisted.

The completion response carries a one-time receipt bound to the exact saved
session. The browser that completed the session presents it to receive that
session's prediction: no researcher key and no manifest entry are needed, but a
receipt only works for its own session, for five minutes, and once.
Single-process runtime only: restart/expiry fail closed.
"""

import hashlib
import ipaddress
import re
import secrets
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.db.session import get_db
from .access import HEADERS, ApprovedSession, ResearchAccess, ResearchMLSettings, get_research_settings, not_available, unavailable
from .contract import KNOWN_EXCLUDED
from .router import research_database
from .service import PredictionResponse, predict_saved_session

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

TTL_SECONDS = 300
MAX_RECEIPTS = 256


def failure(status, message="Research verification is unavailable.", retry=None):
    return HTTPException(status, message, headers={**HEADERS, **({"Retry-After": str(retry)} if retry else {})})


def config_key(settings):
    """Shared-key check used only by the development demo app."""
    if not settings.game_ml_experimental_enabled:
        raise unavailable()
    value = settings.game_researcher_verify_key.get_secret_value() if settings.game_researcher_verify_key else ""
    others = [item.get_secret_value().strip() for item in (settings.game_ml_research_token, settings.game_collection_export_key) if item]
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", value) or any(secrets.compare_digest(value.encode(), item.encode()) for item in others):
        raise unavailable()
    return value


def key_fingerprint(settings):
    ml = settings.game_ml_research_token.get_secret_value() if settings.game_ml_research_token else ""
    return hashlib.sha256((config_key(settings) + "\0" + ml).encode()).hexdigest()


def model_fingerprint(settings):
    """Receipts stop working if the enabled flag or the model/runtime changes."""
    if not settings.game_ml_experimental_enabled:
        raise unavailable()
    return hashlib.sha256(f"{settings.game_ml_model_archive}\0{settings.game_ml_python}".encode()).hexdigest()


def gate_access(session_id, settings, context):
    """The receipt (checked by acquire/valid) is the approval for its own session."""
    model_fingerprint(settings)
    if session_id in KNOWN_EXCLUDED or context.game_session_id != session_id:
        raise not_available()
    for configured in (settings.game_ml_python, settings.game_ml_model_archive):
        if configured is None or not configured.is_absolute() or not configured.is_file():
            raise unavailable()
    return ResearchAccess(settings, context, KNOWN_EXCLUDED)


@dataclass
class Receipt:
    binding: ApprovedSession
    expires: float
    fingerprint: str
    busy: bool = False
    used: bool = False
    revoked: bool = False


class VerificationStore:
    def __init__(self, clock=time.monotonic, fingerprint=key_fingerprint):
        self.clock = clock
        self.fingerprint = fingerprint
        self.lock = threading.RLock()
        self.receipts = {}
        self.failures = OrderedDict()
        self.global_failures = deque()

    def purge(self):
        now = self.clock()
        self.receipts = {key: value for key, value in self.receipts.items() if value.expires > now}
        for key in list(self.failures):
            self.failures[key] = deque(t for t in self.failures[key] if t > now - 60)
            if not self.failures[key]:
                del self.failures[key]
        while self.global_failures and self.global_failures[0] <= now - 60:
            self.global_failures.popleft()

    def issue(self, binding, settings):
        with self.lock:
            self.purge()
            if len(self.receipts) >= MAX_RECEIPTS or any(r.binding.game_session_id == binding.game_session_id for r in self.receipts.values()):
                return None
            token = secrets.token_urlsafe(32)
            self.receipts[hashlib.sha256(token.encode()).hexdigest()] = Receipt(binding, self.clock() + TTL_SECONDS, self.fingerprint(settings))
            return {"receipt": token, "expires_at": (datetime.now(UTC) + timedelta(seconds=TTL_SECONDS)).isoformat()}

    def authenticate(self, client, submitted, settings):
        """Shared-key throttling used only by the development demo app."""
        expected = config_key(settings)
        with self.lock:
            self.purge()
            attempts = self.failures.get(client, ())
            if len(attempts) >= 5 or len(self.global_failures) >= 20 or (client not in self.failures and len(self.failures) >= 128):
                raise failure(429, "Too many verification attempts. Wait before retrying.", 60)
            if not secrets.compare_digest(submitted.encode(), expected.encode()):
                self.failures.setdefault(client, deque()).append(self.clock())
                self.global_failures.append(self.clock())
                raise failure(401, "Researcher verification failed.")

    def acquire(self, token, binding, settings):
        with self.lock:
            self.purge()
            receipt = self.receipts.get(hashlib.sha256(token.encode()).hexdigest())
            if not receipt or receipt.revoked or receipt.binding != binding or receipt.fingerprint != self.fingerprint(settings):
                raise not_available()
            if receipt.used or receipt.busy:
                raise failure(409, "Verification has already been used or is in progress.")
            receipt.busy = True
            return receipt

    def valid(self, receipt, settings):
        with self.lock:
            if receipt.revoked or receipt.used or receipt.expires <= self.clock() or receipt.fingerprint != self.fingerprint(settings):
                raise not_available()

    def finish(self, receipt, success):
        with self.lock:
            receipt.busy = False
            receipt.used = success

    def revoke(self, token, session_id):
        with self.lock:
            self.purge()
            receipt = self.receipts.get(hashlib.sha256(token.encode()).hexdigest())
            if receipt and receipt.binding.game_session_id == session_id:
                receipt.revoked = True


store = VerificationStore(fingerprint=model_fingerprint)


def issue_completion_receipt(saved, newly_completed, request=None):
    if not newly_completed or saved.status != "completed":
        return None
    try:
        if request is not None:
            browser_transport(request)
        settings = get_research_settings()
        model_fingerprint(settings)
        UUID(saved.game_session_id)
        binding = ApprovedSession(game_session_id=saved.game_session_id, student_code=saved.student_id,
                                  concept_id=saved.concept_id, learning_cycle_id=saved.learning_cycle_id,
                                  assessment_phase=saved.assessment_phase)
        return store.issue(binding, settings)
    except (HTTPException, ValueError, TypeError):
        # Prediction configuration must never prevent ordinary completion saving.
        return None


def trusted_client(host):
    if host in LOCAL_HOSTS:
        return True
    if not get_research_settings().game_ml_container_network:
        return False
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def browser_transport(request):
    local_hosts = LOCAL_HOSTS
    local = request.client and trusted_client(request.client.host) and request.url.hostname in local_hosts
    if request.url.scheme != "https" and not local:
        raise failure(403)
    # No trusting browser-supplied forwarding headers or origin as identity.
    origin = request.headers.get("origin", "")
    if origin != app_settings.frontend_url.rstrip("/"):
        raise failure(403)
    if urlsplit(origin).scheme != "https" and not (urlsplit(origin).hostname in local_hosts):
        raise failure(403)
    if request.url.query:
        raise failure(400)


async def json_body(request):
    if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        raise failure(400)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8192:
            raise failure(413)
    try:
        import json
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise failure(400) from None


class VerificationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    receipt: str
    context: ApprovedSession


@dataclass
class BrowserAuthorization:
    access: ResearchAccess
    receipt: Receipt
    success: bool = False


async def require_browser_access(game_session_id: str, request: Request,
                                 settings: Annotated[ResearchMLSettings, Depends(get_research_settings)]):
    browser_transport(request)
    model_fingerprint(settings)
    data = await json_body(request)
    try:
        body = VerificationBody.model_validate(data)
        if body.context.game_session_id != game_session_id or len(body.receipt) > 128:
            raise ValueError()
        UUID(game_session_id)
    except (ValueError, TypeError):
        # Avoid FastAPI's validation errors echoing submitted request bodies.
        raise failure(400) from None
    access = gate_access(game_session_id, settings, body.context)
    receipt = store.acquire(body.receipt, access.binding, settings)
    authorized = BrowserAuthorization(access, receipt)
    del body, data
    try:
        yield authorized
    finally:
        store.finish(receipt, authorized.success)


def browser_database(authorized: Annotated[BrowserAuthorization, Depends(require_browser_access)],
                     database: Annotated[Session, Depends(get_db)]):
    yield from research_database(authorized.access, database)


router = APIRouter()


@router.post("/sessions/{game_session_id}/research-verification", response_model=PredictionResponse)
def verified_prediction(response: Response,
                        authorized: Annotated[BrowserAuthorization, Depends(require_browser_access)],
                        database: Annotated[Session, Depends(browser_database)]):
    response.headers["Cache-Control"] = "no-store"
    try:
        prediction = predict_saved_session(authorized.access, database)
    except HTTPException as error:
        error.headers = {**(error.headers or {}), **HEADERS}
        raise
    except Exception:
        raise unavailable() from None
    # Re-read configuration after the slow worker; a disabled flag discards the result.
    current = get_research_settings()
    store.valid(authorized.receipt, current)
    gate_access(authorized.access.binding.game_session_id, current, authorized.access.binding)
    authorized.success = True
    return prediction


@router.post("/sessions/{game_session_id}/research-verification/cancel", status_code=204)
async def cancel_verification(game_session_id: str, request: Request):
    browser_transport(request)
    data = await json_body(request)
    token = data.get("receipt")
    if isinstance(token, str) and len(token) <= 128:
        store.revoke(token, game_session_id)
    return Response(status_code=204, headers=HEADERS)
