from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    app_name: str = "Sign-Supported AI Tutor API"

    database_url: str = (
        "postgresql+psycopg://"
        "sign_tutor:sign_tutor_dev@localhost:5432/sign_tutor_db"
    )

    frontend_url: str = "http://localhost:5173"
    rag_enabled: bool = True
    rag_generation_enabled: bool = False
    rag_top_k: int = Field(default=3, ge=1, le=5)
    rag_timeout_sec: int = Field(default=15, ge=1, le=60)
    rag_model: str = "gpt-4.1-mini"
    openai_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=(ENV_FILE, ".env", "../.env"),
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
