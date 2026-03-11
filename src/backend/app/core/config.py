from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULTS = {"change-me-in-production", "change-me-internal-key", "", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/solvora"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "Solvora/1.0"

    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    SENTRY_DSN: str = ""
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ENVIRONMENT: str = "development"
    INTERNAL_API_KEY: str = "change-me-internal-key"

    @field_validator("SECRET_KEY", "INTERNAL_API_KEY")
    @classmethod
    def must_not_be_default(cls, v: str, info) -> str:
        if v in _INSECURE_DEFAULTS or len(v) < 16:
            import logging
            logging.warning(
                f"[SECURITY] {info.field_name} is using an insecure default value. "
                f"Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v


settings = Settings()
