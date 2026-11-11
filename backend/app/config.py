from __future__ import annotations
import sys
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "FinSight AI"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Auth
    SECRET_KEY: str = "change-this-to-a-very-secure-random-secret-key-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "finsight"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Google AI (Gemini 2.5 Flash via langchain-google-genai)
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Langfuse (optional)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # File handling
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 20
    MAX_PAGES: int = 50
    MIN_TEXT_CHARS: int = 50

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate_production(self) -> None:
        """Call at startup. Refuses default secret in non-DEBUG mode."""
        if not self.DEBUG and (
            self.SECRET_KEY in ("__CHANGE_ME__", "change-this-to-a-very-secure-random-secret-key-32-chars")
            or len(self.SECRET_KEY) < 32
        ):
            raise RuntimeError(
                "SECRET_KEY must be set to a strong random value (at least 32 characters) in production. "
                "Set DEBUG=true for local development or configure a secure SECRET_KEY."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
