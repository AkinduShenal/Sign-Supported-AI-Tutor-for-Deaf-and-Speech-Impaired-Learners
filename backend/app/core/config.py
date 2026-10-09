from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env (backend/app/core/config.py -> backend/app/core -> backend/app
# -> backend -> repo root). Docker Compose already injects DATABASE_URL as a
# real environment variable, which always takes precedence over this file, so
# this only matters when running uvicorn/pytest/alembic directly rather than
# through `docker compose up`.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    app_name: str = "Sign-Supported AI Tutor API"

    database_url: str = (
        "postgresql+psycopg://"
        "sign_tutor:sign_tutor_dev@localhost:5432/sign_tutor_db"
    )

    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
