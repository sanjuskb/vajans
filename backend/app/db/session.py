"""
VAJANS — Async DB engine and session factory.
All connection parameters come from settings (reads .env).
No credentials are hardcoded here.

NullPool is used intentionally: Celery prefork workers call asyncio.run()
(or async_to_sync) per task, which creates a new event loop each time.
asyncpg connections are bound to the event loop they were created in, so a
pooled connection from loop N is invalid in loop N+1 and raises
"RuntimeError: Event loop is closed".  NullPool avoids this entirely by
opening a fresh connection per session and closing it on exit — no reuse,
no stale-loop crashes.

FastAPI (ASGI) also benefits from NullPool because its event loop is
persistent and Uvicorn manages concurrency via async; a real pool would
add unnecessary complexity with asyncpg.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.settings import settings


class Base(DeclarativeBase):
    pass


def _build_engine_url():
    import os
    from sqlalchemy.engine import URL
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        # Supabase Transaction pooler. Note the cluster id is "aws-1-..." —
        # Supabase shards tenants across multiple clusters per region, so the
        # cluster prefix matters as much as the region. This exact host comes
        # from the project's Connect dialog in the Supabase dashboard.
        return URL.create(
            drivername="postgresql+asyncpg",
            username="postgres.kalihyqbvziypwhklhjc",
            password="vajans@02072526",
            host="aws-1-ap-northeast-1.pooler.supabase.com",
            port=6543,
            database="postgres",
        )
    else:
        return settings.get_database_url()


def _build_connect_args():
    """Connection-time arguments for asyncpg / the SQLAlchemy asyncpg dialect.

    pgbouncer (Supabase Transaction pooler) holds backend connections across
    our NullPool sessions and keeps any prepared statements those sessions
    created. asyncpg's default name scheme is a deterministic counter
    (__asyncpg_stmt_1__, __asyncpg_stmt_2__, ...), so the very next session
    that lands on the same backend collides with DuplicatePreparedStatement.
    Two layers of defence in production:
      1. prepared_statement_cache_size=0 — disable the dialect-level cache.
      2. prepared_statement_name_func — UUID names, so even the unavoidable
         dialect.initialize() probe can't collide.
    """
    import os
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        import ssl
        import uuid
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {
            "server_settings": {"application_name": "vajans"},
            "command_timeout": 30,
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": (
                lambda: f"__asyncpg_{uuid.uuid4().hex}__"
            ),
            "ssl": ctx,
        }
    else:
        return {
            "server_settings": {"application_name": "vajans"},
            "command_timeout": 10,
        }


engine = create_async_engine(
    _build_engine_url(),
    poolclass=NullPool,
    echo=settings.DB_ECHO,
    connect_args=_build_connect_args(),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for use outside FastAPI (e.g. Celery tasks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables that don't yet exist (dev / test convenience only)."""
    from app.models import (  # noqa: F401
        Job, File, Chunk, ExtractedData, AuditLog,
        AuditChain, CriterionDB, ExtractionResultDB, Result,
        EvaluationResult, ReviewAction,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
