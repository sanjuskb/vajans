"""VAJANS — ASGI entry point."""

import sys
from pathlib import Path

# ── Add parent directory to path so 'shared' module is importable
# This allows: from shared.contracts.schemas import ...
BACKEND_DIR = Path(__file__).resolve().parent
PARENT_DIR = BACKEND_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

import uvicorn
from app.main import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # structlog handles logging
    )
