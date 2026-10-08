from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sign-Supported AI Tutor API"

    database_url: str = (
        "postgresql+psycopg://"
        "sign_tutor:sign_tutor_dev@localhost:5432/sign_tutor_db"
    )

    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
