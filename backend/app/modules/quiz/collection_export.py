"""Researcher-key-protected, read-only Quiz CSV download."""

import secrets
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE
from scripts.export_quiz_collection import export_quiz_data


class QuizExportSettings(BaseSettings):
    quiz_collection_export_key: SecretStr | None = None
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


export_bearer = HTTPBearer(auto_error=False)


def require_quiz_export_access(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(export_bearer)],
) -> None:
    configured = QuizExportSettings().quiz_collection_export_key
    expected = configured.get_secret_value().strip() if configured else ""
    if len(expected) < 16:
        raise HTTPException(503, "Researcher Quiz export has not been configured.")
    if credentials is None:
        raise HTTPException(401, "Researcher export key required.", headers={"WWW-Authenticate": "Bearer"})
    if not secrets.compare_digest(credentials.credentials.encode(), expected.encode()):
        raise HTTPException(403, "Researcher export key is incorrect.")


def quiz_collection_zip(database: Session) -> tuple[bytes, str]:
    if database.get_bind().dialect.name == "postgresql":
        database.connection().exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    buffer = BytesIO()
    with TemporaryDirectory(prefix="quiz-csv-export-") as temporary:
        folder = Path(temporary)
        export_quiz_data(database, folder)
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            for name in ("quiz_sessions.csv", "quiz_responses.csv", "manifest.json"):
                archive.writestr(name, (folder / name).read_bytes())
    return buffer.getvalue(), datetime.now(UTC).strftime("quiz-collection-%Y%m%dT%H%M%SZ.zip")
