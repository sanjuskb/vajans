"""
VAJANS — Application Settings
Loaded once at startup. All config comes from environment / .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────
    APP_NAME:     str = "VAJANS"
    APP_VERSION:  str = "0.1.0"
    DEBUG:        bool = False
    ENVIRONMENT:  str = Field(default="development",
                              pattern=r"^(development|staging|production)$")
    SECRET_KEY:   str = "change-me-in-production-please"
    ALLOWED_HOSTS: List[str] = ["*"]

    # ── Database ───────────────────────────────────────────────────────────
    # EITHER: Use DATABASE_URL directly (takes precedence for Supabase, etc.)
    DATABASE_URL: Optional[str] = None
    # OR: Compose from individual components
    DB_HOST:     str = "localhost"
    DB_PORT:     int = 5432
    DB_NAME:     str = "vajans"
    DB_USER:     str = "vajans"
    DB_PASSWORD: str = "vajans"
    DB_SSL_MODE: str = Field(default="disable",
                             pattern=r"^(disable|allow|prefer|require)$")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False  # Log SQL statements
    DB_SSL_CERTIFICATE: Optional[str] = None  # Path to custom SSL certificate

    def get_database_url(self) -> str:
        """
        Build asyncpg connection URL with SSL support.
        Prioritizes explicit DATABASE_URL env var (for Supabase, etc.).
        Falls back to composition from DB_* fields.
        
        For Supabase:
          DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?ssl=require
        """
        if self.DATABASE_URL:
            # User provided explicit DATABASE_URL (e.g., from Supabase)
            url = self.DATABASE_URL.strip()
            
            # Ensure it uses asyncpg driver
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            
            # Ensure SSL is set for Supabase (if not already in URL)
            if "supabase.co" in url and "ssl=" not in url:
                separator = "&" if "?" in url else "?"
                url += f"{separator}ssl=require"
            
            return url

        # Compose from fields, add SSL params for production
        url = f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        if self.DB_SSL_MODE != "disable":
            url += f"?ssl={self.DB_SSL_MODE}"
        return url

    def get_database_url_sync(self) -> str:
        """
        Build psycopg2 connection URL (for Alembic migrations).
        Always uses sync driver regardless of DATABASE_URL format.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL.strip()
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("sqlite+aiosqlite://"):
                url = url.replace("sqlite+aiosqlite://", "sqlite://", 1)
            return url.split("?")[0]

        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # ── Redis ──────────────────────────────────────────────────────────────
    REDIS_HOST:     str = "localhost"
    REDIS_PORT:     int = 6379
    REDIS_DB:       int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Celery ─────────────────────────────────────────────────────────────
    CELERY_BROKER_URL:  str = ""      # populated below via validator
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def set_broker(cls, v: str, info) -> str:
        if v:
            return v
        data = info.data
        auth = f":{data.get('REDIS_PASSWORD')}@" if data.get("REDIS_PASSWORD") else ""
        return f"redis://{auth}{data.get('REDIS_HOST','localhost')}:{data.get('REDIS_PORT',6379)}/1"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def set_result_backend(cls, v: str, info) -> str:
        if v:
            return v
        data = info.data
        auth = f":{data.get('REDIS_PASSWORD')}@" if data.get("REDIS_PASSWORD") else ""
        return f"redis://{auth}{data.get('REDIS_HOST','localhost')}:{data.get('REDIS_PORT',6379)}/2"

    CELERY_TASK_SERIALIZER:   str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TASK_TIME_LIMIT:   int = 3600   # 1 hour hard limit
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3300

    # ── Storage ────────────────────────────────────────────────────────────
    STORAGE_BACKEND:   str = Field(default="local",
                                   pattern=r"^(local|s3)$")
    STORAGE_LOCAL_PATH: str = "./data/storage"

    # S3 (populated if STORAGE_BACKEND=s3)
    AWS_ACCESS_KEY_ID:     Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION:            str = "ap-south-1"
    S3_BUCKET_NAME:        Optional[str] = None
    S3_PREFIX:             str = "vajans/"

    # ── OpenRouter / LLM ───────────────────────────────────────────────────
    OPENROUTER_API_KEY:  str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL:           str = "anthropic/claude-3.5-sonnet"
    LLM_TEMPERATURE:     float = Field(default=0.0, ge=0.0, le=2.0)
    LLM_MAX_TOKENS:      int = Field(default=4096, ge=256, le=32768)
    LLM_TIMEOUT_SECONDS: int = 120

    # ── Embedding ──────────────────────────────────────────────────────────
    EMBEDDING_MODEL:      str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    CHUNK_SIZE:           int = 500
    CHUNK_OVERLAP:        int = 100

    # ── FAISS ──────────────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "./data/faiss"

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL:  str = "INFO"
    LOG_FORMAT: str = "json"   # "json" | "text"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
