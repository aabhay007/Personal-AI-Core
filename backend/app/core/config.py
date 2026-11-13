"""Application configuration using Pydantic Settings."""
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Personal AI Core"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # CORS configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Database configuration (Neon PostgreSQL or local)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_ai_core"
    DATABASE_CONNECT_TIMEOUT_SECONDS: int = 5

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            # Normalize scheme: postgresql:// or postgres:// -> postgresql+asyncpg://
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
            # Normalize sslmode for asyncpg
            if "sslmode=" in v:
                v = v.replace("sslmode=require", "ssl=require").replace("sslmode=prefer", "ssl=prefer").replace("sslmode=disable", "ssl=disable")
            # Strip channel_binding (libpq specific param that asyncpg handles internally)
            if "&channel_binding=" in v:
                import re
                v = re.sub(r"&channel_binding=[^&]*", "", v)
            elif "?channel_binding=" in v:
                import re
                v = re.sub(r"\?channel_binding=[^&]*(&)?", "?", v)
                if v.endswith("?"):
                    v = v[:-1]
        return v

    # AI & LLM Provider Configuration
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "groq"
    DEFAULT_MODEL_NAME: str = "qwen/qwen3.8-27b"
    MAX_CONTEXT_MESSAGES: int = 20
    MAX_TOKENS_PER_REQUEST: int = 4096

    # Security placeholders for Phase 1
    SECRET_KEY: str = "insecure-secret-key-change-in-production-for-phase-1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
