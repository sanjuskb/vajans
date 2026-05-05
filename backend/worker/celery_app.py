"""
VAJANS — Celery Application
============================
Configured for reliable async task processing with Redis as broker.
All tasks are defined in worker/tasks/*.py and auto-discovered.
"""

import sys
from pathlib import Path

# Add parent directory to path so 'shared' module is importable
WORKER_DIR = Path(__file__).resolve().parent
BACKEND_DIR = WORKER_DIR.parent
PARENT_DIR = BACKEND_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from celery import Celery
from app.core.settings import settings

celery_app = Celery(
    "vajans",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "worker.tasks.ingestion",
        "worker.tasks.extraction",
        "worker.tasks.evaluation",
        "worker.tasks.ai_pipeline",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=["json"],

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,

    # Timeouts
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,

    # Result expiry (24 hours)
    result_expires=86400,

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Routing
    task_routes={
        "worker.tasks.ingestion.*":   {"queue": "ingestion"},
        "worker.tasks.extraction.*":  {"queue": "extraction"},
        "worker.tasks.ai_pipeline.*": {"queue": "extraction"},
        "worker.tasks.evaluation.*":  {"queue": "evaluation"},
    },
    task_default_queue="default",
)
