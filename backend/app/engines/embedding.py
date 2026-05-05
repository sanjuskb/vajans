"""
VAJANS — Embedding Generation Engine (Phase 3)
===============================================
Converts text chunks into dense vector embeddings
using OpenAI-compatible API via OpenRouter.

Model: text-embedding-3-small (1536 dimensions)
"""

from __future__ import annotations

import asyncio
import time
from typing import List

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.settings import settings

logger = structlog.get_logger("vajans.embedding")

# ── Constants ────────────────────────────────────────────────────────────────
EMBEDDING_BATCH_SIZE = 100        # max chunks per API call
EMBEDDING_DIMENSIONS = 1536       # text-embedding-3-small output size
MAX_CHUNK_CHARS      = 6000       # truncate chunks longer than this


# ── Exceptions ───────────────────────────────────────────────────────────────

class EmbeddingError(Exception):
    def __init__(self, message: str, code: str = "EMBEDDING_ERROR"):
        self.code = code
        super().__init__(message)


# ── Core embedding call ───────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _call_embedding_api(
    texts: List[str],
    client: httpx.AsyncClient,
) -> List[List[float]]:
    """
    Single API call to OpenRouter embeddings endpoint.
    Returns list of vectors aligned with input texts.
    """
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": texts,
    }

    response = await client.post(
        f"{settings.OPENROUTER_BASE_URL}/embeddings",
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vajans.ai",
            "X-Title": "VAJANS",
        },
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise EmbeddingError(
            f"Embedding API returned {response.status_code}: {response.text}",
            code="API_ERROR",
        )

    data = response.json()

    # Validate response structure
    if "data" not in data:
        raise EmbeddingError(
            f"Unexpected API response structure: {list(data.keys())}",
            code="INVALID_RESPONSE",
        )

    # Extract embeddings in correct order
    embeddings = [None] * len(texts)
    for item in data["data"]:
        embeddings[item["index"]] = item["embedding"]

    if any(e is None for e in embeddings):
        raise EmbeddingError(
            "Some embeddings missing from API response",
            code="INCOMPLETE_RESPONSE",
        )

    return embeddings


# ── Batch processor ───────────────────────────────────────────────────────────

async def generate_embeddings(
    texts: List[str],
    chunk_ids: List[str] | None = None,
) -> List[List[float]]:
    """
    Generate embeddings for a list of text chunks.
    Processes in batches to respect API limits.

    Args:
        texts:      List of text strings to embed.
        chunk_ids:  Optional list of chunk IDs for logging correlation.

    Returns:
        List of embedding vectors (same length and order as input texts).

    Raises:
        EmbeddingError: If embedding generation fails after retries.
    """
    if not texts:
        return []

    log = logger.bind(total_chunks=len(texts))
    log.info("Starting embedding generation")

    # Truncate overly long chunks (avoids token limit errors)
    truncated_texts = [t[:MAX_CHUNK_CHARS] for t in texts]

    all_embeddings: List[List[float]] = []
    total_batches = (len(truncated_texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    async with httpx.AsyncClient() as client:
        for batch_idx in range(total_batches):
            start = batch_idx * EMBEDDING_BATCH_SIZE
            end   = start + EMBEDDING_BATCH_SIZE
            batch = truncated_texts[start:end]

            t0 = time.perf_counter()
            try:
                batch_embeddings = await _call_embedding_api(batch, client)
                elapsed = round((time.perf_counter() - t0) * 1000, 1)
                log.info(
                    "Batch embedded",
                    batch=f"{batch_idx + 1}/{total_batches}",
                    size=len(batch),
                    elapsed_ms=elapsed,
                )
                all_embeddings.extend(batch_embeddings)
            except Exception as exc:
                log.error(
                    "Embedding batch failed",
                    batch=f"{batch_idx + 1}/{total_batches}",
                    error=str(exc),
                )
                raise EmbeddingError(
                    f"Embedding batch {batch_idx + 1} failed: {exc}",
                    code="BATCH_FAILED",
                ) from exc

            # Small delay between batches to avoid rate limiting
            if batch_idx < total_batches - 1:
                await asyncio.sleep(0.2)

    log.info(
        "Embedding generation complete",
        total_embeddings=len(all_embeddings),
        dimensions=EMBEDDING_DIMENSIONS,
    )

    return all_embeddings


def generate_embeddings_sync(texts: List[str]) -> List[List[float]]:
    """Sync wrapper for use in Celery tasks."""
    return asyncio.run(generate_embeddings(texts))
