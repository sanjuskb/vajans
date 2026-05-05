"""VAJANS — Shared Celery task base class and async runner."""

import asyncio

import structlog
from celery import Task

logger = structlog.get_logger("vajans.worker")


class BaseTask(Task):
    abstract = True
    max_retries = 3
    default_retry_delay = 30

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("Task failed",
                     task_id=task_id, exc_type=type(exc).__name__, exc_msg=str(exc))

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("Task retrying",
                       task_id=task_id, attempt=self.request.retries)


def run_async(coro):
    """Run a coroutine from a synchronous Celery task."""
    return asyncio.run(coro)
