"""
Centralized application configuration.

Uses pydantic-settings so every config value is:
  - typed
  - overridable via environment variables / .env file
  - never hardcoded across the codebase
"""

from functools import lru_cache
from typing import List
from urllib.parse import quote, quote_plus, unquote

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------
    # App
    # --------------------------------------------------

    PROJECT_NAME: str = "Zero-Day Attack Detection Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --------------------------------------------------
    # Security / JWT
    # --------------------------------------------------

    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --------------------------------------------------
    # CORS
    # --------------------------------------------------

    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []

            if not v.startswith("["):
                return [
                    i.strip()
                    for i in v.split(",")
                    if i.strip()
                ]

        return v

    # --------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "zeroday"
    POSTGRES_PASSWORD: str = "zeroday_pw"
    POSTGRES_DB: str = "zeroday_db"

    DATABASE_URL_ENV: str | None = Field(
        None,
        alias="DATABASE_URL"
    )

    @property
    def DATABASE_URL(self) -> str:

        def _clean_url(raw_url: str) -> str:

            # SQLite URLs should remain unchanged
            if "sqlite" in raw_url:
                return raw_url

            prefix_found = None

            for prefix in [
                "postgresql+asyncpg://",
                "postgresql://",
                "postgres://",
            ]:
                if raw_url.startswith(prefix):
                    prefix_found = prefix
                    break

            # Unknown URL type
            if not prefix_found:
                return raw_url

            # Remove original prefix
            rest = raw_url[len(prefix_found):]

            # Separate query string
            query = ""

            if "?" in rest:
                rest, query_str = rest.split("?", 1)
                query = "?" + query_str

            # Separate database path
            path = ""

            if "/" in rest:
                authority, path_str = rest.split("/", 1)
                path = "/" + path_str
            else:
                authority = rest

            # Encode username/password safely
            if "@" in authority:

                parts = authority.split("@")

                host_port = parts[-1]
                user_pwd = "@".join(parts[:-1])

                if ":" in user_pwd:

                    user, pwd = user_pwd.split(":", 1)

                    clean_u = quote(
                        unquote(user),
                        safe=""
                    )

                    clean_p = quote(
                        unquote(pwd),
                        safe=""
                    )

                    authority = (
                        f"{clean_u}:{clean_p}"
                        f"@{host_port}"
                    )

            # Always use asyncpg
            url = (
                f"postgresql+asyncpg://"
                f"{authority}"
                f"{path}"
                f"{query}"
            )

            # Render/external PostgreSQL connections require SSL.
            # Local Docker/localhost should not automatically get SSL.
            local_hosts = [
                "@localhost",
                "@127.0.0.1",
                "@postgres:",
            ]

            is_local = any(
                local_host in url
                for local_host in local_hosts
            )

            if not is_local and "ssl=" not in url:

                if "?" in url:
                    url += "&ssl=require"
                else:
                    url += "?ssl=require"

            return url

        # Use Render DATABASE_URL when available
        if self.DATABASE_URL_ENV:
            return _clean_url(
                self.DATABASE_URL_ENV
            )

        # Local/Docker fallback logic
        if self.POSTGRES_HOST in (
            "postgres",
            "localhost",
            "127.0.0.1",
        ):

            import socket

            try:
                socket.gethostbyname(
                    self.POSTGRES_HOST
                )

            except Exception:

                # SQLite fallback
                return (
                    "sqlite+aiosqlite:///./zeroday.db"
                )

        # Generate PostgreSQL connection URL
        raw_generated = (
            "postgresql+asyncpg://"
            f"{quote_plus(self.POSTGRES_USER)}:"
            f"{quote_plus(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

        return _clean_url(raw_generated)

    # --------------------------------------------------
    # MongoDB
    # --------------------------------------------------

    MONGO_URI_ENV: str | None = Field(
        None,
        alias="MONGO_URI"
    )

    MONGO_DB_NAME: str = "zeroday_docs"

    @property
    def MONGO_URI(self) -> str:

        raw_url = (
            self.MONGO_URI_ENV
            or "mongodb://mongo:27017"
        )

        prefix_found = None

        for prefix in [
            "mongodb+srv://",
            "mongodb://",
        ]:
            if raw_url.startswith(prefix):
                prefix_found = prefix
                break

        # Unknown Mongo URL
        if not prefix_found:
            return raw_url

        rest = raw_url[len(prefix_found):]

        query = ""

        if "?" in rest:

            rest, query_str = rest.split(
                "?",
                1
            )

            query = "?" + query_str

        path = ""

        if "/" in rest:

            authority, path_str = rest.split(
                "/",
                1
            )

            path = "/" + path_str

        else:
            authority = rest

        # Safely encode MongoDB username/password
        if "@" in authority:

            parts = authority.split("@")

            host_port = parts[-1]

            user_pwd = "@".join(
                parts[:-1]
            )

            if ":" in user_pwd:

                user, pwd = user_pwd.split(
                    ":",
                    1
                )

                clean_u = quote(
                    unquote(user),
                    safe=""
                )

                clean_p = quote(
                    unquote(pwd),
                    safe=""
                )

                authority = (
                    f"{clean_u}:{clean_p}"
                    f"@{host_port}"
                )

        return (
            f"{prefix_found}"
            f"{authority}"
            f"{path}"
            f"{query}"
        )

    # --------------------------------------------------
    # Redis
    # --------------------------------------------------

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    REDIS_URL_ENV: str | None = Field(
        None,
        alias="REDIS_URL"
    )

    @property
    def REDIS_URL(self) -> str:

        # Use production REDIS_URL when available
        if self.REDIS_URL_ENV:
            return self.REDIS_URL_ENV

        # Password-protected Redis
        if self.REDIS_PASSWORD:

            return (
                f"rediss://default:"
                f"{self.REDIS_PASSWORD}"
                f"@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}"
                f"/{self.REDIS_DB}"
            )

        # Local Redis
        return (
            f"redis://{self.REDIS_HOST}:"
            f"{self.REDIS_PORT}"
            f"/{self.REDIS_DB}"
        )

    # --------------------------------------------------
    # Seed Admin
    # --------------------------------------------------

    ADMIN_EMAIL: str = "admin@zeroday.ai"
    ADMIN_PASSWORD: str = "Admin@1234"
    ADMIN_NAME: str = "Admin"

    # --------------------------------------------------
    # File Storage
    # --------------------------------------------------

    UPLOAD_DIR: str = Field(
        "./data/uploads",
        alias="UPLOAD_DIR"
    )

    PROCESSED_DIR: str = Field(
        "./data/processed",
        alias="PROCESSED_DIR"
    )

    MAX_UPLOAD_SIZE_MB: int = 2048

    # --------------------------------------------------
    # ML
    # --------------------------------------------------

    MODEL_ARTIFACT_DIR: str = Field(
        "./data/model_artifacts",
        alias="MODEL_ARTIFACT_DIR"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached so the .env file is only parsed once
    per process.
    """
    return Settings()


settings = get_settings()