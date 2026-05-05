"""VAJANS — Health Check Endpoints."""

from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.settings import settings
from app.db.session import engine

router = APIRouter()


@router.get("/health", summary="Basic liveness probe")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready", summary="Readiness probe — checks DB + Redis")
async def readiness():
    checks: dict[str, str] = {}
    overall = "ok"

    # ── Database ─────────────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall = "degraded"

    # ── Redis ─────────────────────────────────────────────────────────────
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall = "degraded"

    http_status = status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        content={
            "status": overall,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.APP_VERSION,
        },
        status_code=http_status,
    )
