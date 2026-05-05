"""Alembic migration environment — sync SQLAlchemy (stable for local dev)."""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ─────────────────────────────────────────────────────────────
# PATH SETUP (so imports work)
# ─────────────────────────────────────────────────────────────
ALEMBIC_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ALEMBIC_DIR.parent
PARENT_DIR = BACKEND_DIR.parent

if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ─────────────────────────────────────────────────────────────
# IMPORT MODELS
# ─────────────────────────────────────────────────────────────
from app.models import job, file, chunk, extracted_data, result, audit, evaluation, review, audit_chain  # noqa: F401
from app.db.session import Base

# ─────────────────────────────────────────────────────────────
# ALEMBIC CONFIG
# ─────────────────────────────────────────────────────────────
config = context.config

from app.core.settings import settings  # noqa: E402

if settings.ENVIRONMENT == "development":
    # Supabase uses pgBouncer in transaction-pooling mode (port 6543).
    # That pooler rejects the SET commands, advisory locks, and
    # multi-statement transactions that Alembic requires, so migrations
    # fail with "tenant/user not found" or similar pooler errors.
    # In development, bypass the pooler and connect directly to the
    # local PostgreSQL instance instead.
    DATABASE_URL = "postgresql://vajans:vajans123@localhost:5432/vajans"
else:
    # Staging / production: use the configured sync URL (psycopg2 driver).
    DATABASE_URL = settings.get_database_url_sync()

# configparser (used internally by Alembic) treats "%" as an interpolation
# marker.  URL-encoded characters such as "%40" (→ @) in Supabase passwords
# trigger a ValueError at parse time.  Doubling every "%" escapes them so
# configparser passes the string through verbatim; the actual DB driver
# receives the original URL unchanged.  For the local dev URL this is a no-op.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ─────────────────────────────────────────────────────────────
# OFFLINE MODE
# ─────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ─────────────────────────────────────────────────────────────
# ONLINE MODE (SYNC ENGINE)
# ─────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()