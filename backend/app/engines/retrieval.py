"""
VAJANS — RAG Retrieval Engine (Phase 3)
=========================================
Accepts a query string, converts it to an embedding,
searches the job's FAISS index, and returns the relevant
chunk texts with their source metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List

import structlog

from app.engines.embedding import generate_embeddings
from app.engines.vector_store import search, VectorStoreError

logger = structlog.get_logger("vajans.retrieval")


# ── Data contracts ────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    chunk_id:   str
    text:       str
    score:      float       # cosine similarity (0–1, higher = more relevant)
    page:       int
    file_id:    str


@dataclass
class RetrievalResult:
    query:          str
    job_id:         str
    chunks:         List[RetrievedChunk]
    total_searched: int


# ── Exceptions ────────────────────────────────────────────────────────────────

class RetrievalError(Exception):
    def __init__(self, message: str, code: str = "RETRIEVAL_ERROR"):
        self.code = code
        super().__init__(message)


# ── Core retrieval ────────────────────────────────────────────────────────────

async def retrieve_chunks(
    query: str,
    job_id: str | uuid.UUID,
    db,                          # AsyncSession — for fetching chunk text from DB
    top_k: int = 5,
    min_score: float = 0.3,      # discard results below this similarity
) -> RetrievalResult:
    """
    Full RAG retrieval pipeline:
    1. Embed the query
    2. Search FAISS index for the job
    3. Fetch chunk texts from DB
    4. Filter by minimum similarity score
    5. Return ranked results

    Args:
        query:     The natural language query (criterion description).
        job_id:    UUID of the evaluation job.
        db:        AsyncSession for DB lookups.
        top_k:     Maximum number of chunks to retrieve.
        min_score: Minimum cosine similarity to include a result.

    Returns:
        RetrievalResult containing ranked RetrievedChunk objects.
    """
    job_id_str = str(job_id)
    log = logger.bind(job_id=job_id_str, query=query[:80])
    log.info("Starting RAG retrieval")

    if not query.strip():
        raise RetrievalError("Query cannot be empty", code="EMPTY_QUERY")

    # ── Step 1: Embed query ──────────────────────────────────────────────
    try:
        query_embeddings = await generate_embeddings([query])
        query_vector = query_embeddings[0]
    except Exception as exc:
        raise RetrievalError(
            f"Query embedding failed: {exc}",
            code="EMBEDDING_FAILED",
        ) from exc

    # ── Step 2: FAISS search ─────────────────────────────────────────────
    try:
        raw_results = search(
            job_id=job_id,
            query_embedding=query_vector,
            top_k=top_k,
        )
    except VectorStoreError as exc:
        raise RetrievalError(str(exc), code=exc.code) from exc

    if not raw_results:
        log.warning("No results from FAISS search")
        return RetrievalResult(
            query=query,
            job_id=job_id_str,
            chunks=[],
            total_searched=0,
        )

    # ── Step 3: Filter by minimum score ─────────────────────────────────
    filtered = [(cid, score) for cid, score in raw_results if score >= min_score]

    if not filtered:
        log.warning(
            "All results below min_score threshold",
            min_score=min_score,
            best_score=raw_results[0][1] if raw_results else None,
        )

    # ── Step 4: Fetch chunk texts from DB ────────────────────────────────
    chunk_ids = [cid for cid, _ in filtered]
    score_map = {cid: score for cid, score in filtered}

    retrieved: List[RetrievedChunk] = []

    if chunk_ids:
        from sqlalchemy import select
        from app.models.chunk import Chunk

        chunk_uuids = [uuid.UUID(cid) for cid in chunk_ids]
        result = await db.execute(
            select(Chunk).where(Chunk.id.in_(chunk_uuids))
        )
        db_chunks = result.scalars().all()

        # Build map for ordering preservation
        chunk_map = {str(c.id): c for c in db_chunks}

        for cid in chunk_ids:
            chunk = chunk_map.get(cid)
            if not chunk:
                log.warning("Chunk in FAISS index but not in DB", chunk_id=cid)
                continue
            retrieved.append(RetrievedChunk(
                chunk_id=cid,
                text=chunk.text,
                score=score_map[cid],
                page=chunk.page,
                file_id=str(chunk.file_id),
            ))

    log.info(
        "Retrieval complete",
        returned=len(retrieved),
        top_score=retrieved[0].score if retrieved else None,
    )

    return RetrievalResult(
        query=query,
        job_id=job_id_str,
        chunks=retrieved,
        total_searched=len(raw_results),
    )


def retrieve_chunks_sync(
    query: str,
    job_id: str | uuid.UUID,
    db_session,
    top_k: int = 5,
    min_score: float = 0.3,
) -> RetrievalResult:
    """Sync wrapper for Celery task usage."""
    import asyncio
    return asyncio.run(retrieve_chunks(query, job_id, db_session, top_k, min_score))
