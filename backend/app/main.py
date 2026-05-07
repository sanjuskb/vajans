"""
VAJANS — FastAPI Application Entry Point
"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.logging import setup_logging
from app.core.settings import settings
from app.db.session import init_db

# API Routers
from app.api.v1.endpoints import jobs, files, health, analyze, auth, analytics

setup_logging()
logger = structlog.get_logger("vajans.app")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VAJANS starting up", version=settings.APP_VERSION, env=settings.ENVIRONMENT)
    
    # Log database configuration for debugging
    db_url = settings.get_database_url()
    # Mask password for security
    masked_url = db_url.split("@")[0] + "@***:***@" + db_url.split("@")[1] if "@" in db_url else db_url
    logger.info("Attempting database connection", url=masked_url)

    # Initialize database tables in development mode
    # Wrapped in try-except so startup doesn't crash if DB is unavailable
    if settings.ENVIRONMENT == "development":
        try:
            await init_db()
            logger.info("✓ Database tables initialised (dev mode)")
        except ConnectionRefusedError as e:
            logger.error(
                "✗ Database connection refused",
                error=str(e),
                host=settings.DB_HOST if not settings.DATABASE_URL else "Supabase",
                port=settings.DB_PORT,
                note="Verify DATABASE_URL is correct and database is running",
            )
        except Exception as e:
            logger.error(
                "✗ Database initialization failed",
                error_type=type(e).__name__,
                error=str(e),
                note="App will continue running; DB operations may fail",
            )

    yield

    logger.info("VAJANS shutting down")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Automated Government Tender Evaluation System",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request ID + timing middleware ──────────────────────────────────
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Global exception handler ─────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", exc_type=type(exc).__name__, exc=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred.",
                "request_id": structlog.contextvars.get_contextvars().get("request_id"),
            },
        )

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router,   prefix="/api/v1", tags=["auth"])
    app.include_router(jobs.router,   prefix="/api/v1", tags=["jobs"])
    app.include_router(files.router,  prefix="/api/v1", tags=["files"])
    app.include_router(analyze.router,    prefix="/api/v1", tags=["analyze"])
    app.include_router(analytics.router,  prefix="/api/v1", tags=["analytics"])

    return app

app = create_app()
