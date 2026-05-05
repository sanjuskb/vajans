"""
VAJANS — FAISS Vector Store (Phase 3)
======================================
Per-job FAISS indexes for chunk retrieval.
Each job gets its own isolated index — no cross-job contamination.

Index files stored at: {FAISS_INDEX_PATH}/{job_id}/
  - index.faiss      → FAISS binary index
  - mapping.json     → embedding position → chunk_id
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
import structlog

from app.core.settings import settings

logger = structlog.get_logger("vajans.vector_store")

DIMENSIONS = 1536   # text-embedding-3-small


# ── Exceptions ───────────────────────────────────────────────────────────────

class VectorStoreError(Exception):
    def __init__(self, message: str, code: str = "VECTOR_STORE_ERROR"):
        self.code = code
        super().__init__(message)


# ── Path helpers ─────────────────────────────────────────────────────────────

def _job_index_dir(job_id: str | uuid.UUID) -> Path:
    base = Path(settings.FAISS_INDEX_PATH).resolve()
    return base / str(job_id)


def _index_path(job_id: str | uuid.UUID) -> Path:
    return _job_index_dir(job_id) / "index.faiss"


def _mapping_path(job_id: str | uuid.UUID) -> Path:
    return _job_index_dir(job_id) / "mapping.json"


# ── Index lifecycle ───────────────────────────────────────────────────────────

def create_index(job_id: str | uuid.UUID) -> faiss.IndexFlatIP:
    """
    Create a new empty FAISS index for a job.
    Uses Inner Product (cosine similarity after L2 normalization).
    """
    index = faiss.IndexFlatIP(DIMENSIONS)
    _job_index_dir(job_id).mkdir(parents=True, exist_ok=True)
    logger.info("FAISS index created", job_id=str(job_id))
    return index


def load_index(job_id: str | uuid.UUID) -> Tuple[faiss.IndexFlatIP, List[str]]:
    """
    Load an existing FAISS index + chunk_id mapping from disk.

    Returns:
        (faiss_index, chunk_ids_list)

    Raises:
        VectorStoreError if index files don't exist.
    """
    idx_path = _index_path(job_id)
    map_path = _mapping_path(job_id)

    if not idx_path.exists():
        raise VectorStoreError(
            f"No FAISS index found for job {job_id}",
            code="INDEX_NOT_FOUND",
        )

    try:
        index = faiss.read_index(str(idx_path))
        with open(map_path, "r") as f:
            chunk_ids = json.load(f)
        logger.info(
            "FAISS index loaded",
            job_id=str(job_id),
            vectors=index.ntotal,
        )
        return index, chunk_ids
    except Exception as exc:
        raise VectorStoreError(
            f"Failed to load FAISS index for job {job_id}: {exc}",
            code="INDEX_LOAD_FAILED",
        ) from exc


def save_index(
    job_id: str | uuid.UUID,
    index: faiss.IndexFlatIP,
    chunk_ids: List[str],
) -> None:
    """
    Persist FAISS index and chunk_id mapping to disk.
    Atomic write: writes to temp file first, then renames.
    """
    dir_path = _job_index_dir(job_id)
    dir_path.mkdir(parents=True, exist_ok=True)

    idx_path = _index_path(job_id)
    map_path = _mapping_path(job_id)

    # Write index
    tmp_idx = idx_path.with_suffix(".faiss.tmp")
    faiss.write_index(index, str(tmp_idx))
    tmp_idx.rename(idx_path)

    # Write mapping
    tmp_map = map_path.with_suffix(".json.tmp")
    with open(tmp_map, "w") as f:
        json.dump(chunk_ids, f)
    tmp_map.rename(map_path)

    logger.info(
        "FAISS index saved",
        job_id=str(job_id),
        vectors=index.ntotal,
        path=str(idx_path),
    )


def index_exists(job_id: str | uuid.UUID) -> bool:
    """Check if a FAISS index exists for the given job."""
    return _index_path(job_id).exists()


# ── Add embeddings ────────────────────────────────────────────────────────────

def add_embeddings(
    job_id: str | uuid.UUID,
    chunk_ids: List[str],
    embeddings: List[List[float]],
) -> None:
    """
    Add embeddings to the job's FAISS index.
    Creates the index if it doesn't exist yet.
    Appends if the index already exists.

    Args:
        job_id:     UUID of the evaluation job.
        chunk_ids:  List of chunk UUIDs (aligned with embeddings).
        embeddings: List of embedding vectors.
    """
    if len(chunk_ids) != len(embeddings):
        raise VectorStoreError(
            f"chunk_ids ({len(chunk_ids)}) and embeddings ({len(embeddings)}) length mismatch",
            code="LENGTH_MISMATCH",
        )

    if not embeddings:
        logger.warning("add_embeddings called with empty list", job_id=str(job_id))
        return

    # Load existing or create new
    if index_exists(job_id):
        index, existing_chunk_ids = load_index(job_id)
    else:
        index = create_index(job_id)
        existing_chunk_ids = []

    # Convert to numpy float32 (required by FAISS)
    vectors = np.array(embeddings, dtype=np.float32)

    # L2 normalize for cosine similarity via inner product
    faiss.normalize_L2(vectors)

    # Add to index
    index.add(vectors)
    existing_chunk_ids.extend(chunk_ids)

    # Persist
    save_index(job_id, index, existing_chunk_ids)

    logger.info(
        "Embeddings added to FAISS index",
        job_id=str(job_id),
        added=len(embeddings),
        total=index.ntotal,
    )


# ── Search ────────────────────────────────────────────────────────────────────

def search(
    job_id: str | uuid.UUID,
    query_embedding: List[float],
    top_k: int = 5,
) -> List[Tuple[str, float]]:
    """
    Search the job's FAISS index for the most similar chunks.

    Args:
        job_id:          UUID of the evaluation job.
        query_embedding: Embedding vector of the query.
        top_k:           Number of results to return.

    Returns:
        List of (chunk_id, similarity_score) tuples, sorted by score descending.

    Raises:
        VectorStoreError if no index exists for the job.
    """
    index, chunk_ids = load_index(job_id)

    if index.ntotal == 0:
        logger.warning("FAISS index is empty", job_id=str(job_id))
        return []

    # Normalize query vector
    query_vec = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query_vec)

    # Search
    actual_k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vec, actual_k)

    results: List[Tuple[str, float]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:   # FAISS returns -1 for empty slots
            continue
        if idx >= len(chunk_ids):
            logger.warning("FAISS index out of sync with mapping", idx=idx)
            continue
        results.append((chunk_ids[idx], float(score)))

    logger.debug(
        "FAISS search complete",
        job_id=str(job_id),
        top_k=top_k,
        returned=len(results),
    )

    return results


def delete_index(job_id: str | uuid.UUID) -> None:
    """Remove all FAISS index files for a job (cleanup on job deletion)."""
    import shutil
    dir_path = _job_index_dir(job_id)
    if dir_path.exists():
        shutil.rmtree(dir_path)
        logger.info("FAISS index deleted", job_id=str(job_id))
