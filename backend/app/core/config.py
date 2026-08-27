"""
Centralized application configuration.

Uses pydantic-settings so every config value is:
  - typed (fails fast on startup if misconfigured)
  - overridable via environment variables / .env file
  - never hardcoded across the codebase (single source of truth)
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # --- PostgreSQL ---
    # Local Docker defaults
    # Production values will be supplied through Render environment variables.
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "zeroday"
    POSTGRES_PASSWORD: str = "zeroday_pw"
    POSTGRES_DB: str = "zeroday_db"
    DATABASE_URL_ENV: str | None = Field(None, alias="DATABASE_URL")

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_ENV:
            url = self.DATABASE_URL_ENV
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # If connecting to remote PostgreSQL (e.g. Render), ensure ssl=require is appended
            if "sqlite" not in url and "ssl=" not in url:
                if not any(local_host in url for local_host in ["@localhost", "@127.0.0.1", "@postgres:"]):
                    url += "?ssl=require" if "?" not in url else "&ssl=require"
            return url

        # Fallback to SQLite if no external DATABASE_URL is set and default 'postgres' host is unresolvable
        if self.POSTGRES_HOST in ("postgres", "localhost", "127.0.0.1"):
            import socket
            try:
                socket.gethostbyname(self.POSTGRES_HOST)
            except Exception:
                return "sqlite+aiosqlite:///./zeroday.db"

        url = (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

        if self.ENVIRONMENT == "production":
            url += "?ssl=require"

        return url

    # --- MongoDB ---
    # Local Docker default
    # Production MONGO_URI will be supplied through Render.
    MONGO_URI: str = "mongodb://mongo:27017"
    MONGO_DB_NAME: str = "zeroday_docs"

    # --- Redis ---
    # Local Docker defaults
    # Production values can be supplied via REDIS_URL OR REDIS_HOST/PORT/PASSWORD.
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_URL_ENV: str | None = Field(None, alias="REDIS_URL")

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_ENV:
            return self.REDIS_URL_ENV

        if self.REDIS_PASSWORD:
            return (
                f"rediss://default:{self.REDIS_PASSWORD}"
                f"@{self.REDIS_HOST}:{self.REDIS_PORT}"
                f"/{self.REDIS_DB}"
            )

        return (
            f"redis://{self.REDIS_HOST}:"
            f"{self.REDIS_PORT}/{self.REDIS_DB}"
        )

    # --- File storage ---
    UPLOAD_DIR: str = Field("./data/uploads", alias="UPLOAD_DIR")
    PROCESSED_DIR: str = Field("./data/processed", alias="PROCESSED_DIR")
    MAX_UPLOAD_SIZE_MB: int = 2048

    # --- ML ---
    MODEL_ARTIFACT_DIR: str = Field("./data/model_artifacts", alias="MODEL_ARTIFACT_DIR")


@lru_cache
def get_settings() -> Settings:
    """
    Cached so the .env file is only parsed once per process.
    """
    return Settings()


settings = get_settings()