#!/usr/bin/env bash
# VAJANS — Render service entrypoint.
# Runs the Supabase schema migration once, then launches uvicorn + celery
# in the same container via honcho (reads the adjacent Procfile).
#
# Why one container? Render disks are not shared across services, but both
# the FastAPI web process and the Celery worker need to read/write the
# `data/storage` (uploaded PDFs) and `data/faiss` (vector indexes)
# directories on the persistent disk. Co-locating both processes is the
# only way to share a Render disk.
set -euo pipefail

echo "[start.sh] env=${ENVIRONMENT:-unset}"
echo "[start.sh] python=$(python3 --version)"

# Ensure data directories exist on the persistent disk
mkdir -p "${STORAGE_LOCAL_PATH:-./data/storage}"
mkdir -p "${FAISS_INDEX_PATH:-./data/faiss}"

# One-shot schema migration (idempotent: create_all skips existing tables).
# Runs only when ENVIRONMENT=production so dev never touches Supabase here.
if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "[start.sh] running Supabase schema migration"
    python3 migrate_to_supabase.py || {
        echo "[start.sh] migration failed — aborting boot" >&2
        exit 1
    }
fi

echo "[start.sh] launching honcho (web + worker)"
exec honcho start
