from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database — PostgreSQL via asyncpg
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tenet"

    # JWT
    JWT_SECRET: str = "change-me-in-production-use-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 8

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # Anthropic (for AI agents)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # Storage
    STORAGE_BACKEND: str = "local"           # 'local' | 's3' | 'supabase'
    STORAGE_LOCAL_ROOT: str = "artifacts/uploads"
    STORAGE_BUCKET: str = "tenet-evidence"

    # Rate limits
    RATE_LIMIT_DEFAULT: str = "1000/hour"
    RATE_LIMIT_AUDITS: str = "10/minute"

    # Misc
    MAX_EVIDENCE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB


settings = Settings()
