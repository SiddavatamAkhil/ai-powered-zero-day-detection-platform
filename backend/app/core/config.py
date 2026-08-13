"""
Centralized application configuration.

Uses pydantic-settings so every config value is:
  - typed (fails fast on startup if misconfigured, not at 2am in prod)
  - overridable via environment variables / .env file
  - never hardcoded across the codebase (single source of truth)
"""
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    PROJECT_NAME: str = "Zero-Day Attack Detection Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # --- PostgreSQL (relational: users, models, training runs, metrics) ---
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "zeroday"
    POSTGRES_PASSWORD: str = "zeroday_pw"
    POSTGRES_DB: str = "zeroday_db"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- MongoDB (semi-structured: raw dataset samples, SHAP blobs, live events) ---
    MONGO_URI: str = "mongodb://mongo:27017"
    MONGO_DB_NAME: str = "zeroday_docs"

    # --- Redis (session cache, JWT blacklist, pub/sub for live dashboard) ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- File storage ---
    UPLOAD_DIR: str = "/data/uploads"
    PROCESSED_DIR: str = "/data/processed"
    MAX_UPLOAD_SIZE_MB: int = 2048

    # --- ML ---
    MODEL_ARTIFACT_DIR: str = "/data/model_artifacts"


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is only parsed once per process."""
    return Settings()


settings = get_settings()
