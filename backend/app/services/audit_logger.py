"""
VAJANS — Phase 5 Audit Logger
==============================
Cryptographic hash chain for tamper-evident audit trail.

Hash formula:
    current_hash = sha256(previous_hash + json.dumps(payload, sort_keys=True))

First entry genesis:
    previous_hash = sha256(b"GENESIS").hexdigest()

Rules:
- Always fetch the last hash before inserting (per-job chain)
- Chain is broken if any entry's previous_hash != prior entry's current_hash
- Verification re-derives all hashes from genesis and compares
"""

import hashlib
import json
import uuid as uuid_mod
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("vajans.audit_logger")

_GENESIS_HASH = hashlib.sha256(b"GENESIS").hexdigest()


def _compute_hash(previous_hash: str, payload: dict) -> str:
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = (previous_hash + payload_str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def log_action(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
    action_type: str,
    payload: dict[str, Any],
) -> "AuditChain":  # noqa: F821
    """
    Append one entry to the job's audit chain.
    Fetches the last entry's current_hash to build the chain.
    Raises RuntimeError if unable to establish chain integrity.
    """
    from app.models.audit_chain import AuditChain

    # Find the TAIL of the chain: the entry whose current_hash is not
    # referenced as any other entry's previous_hash.  Ordering by created_at
    # is unreliable because multiple entries within the same DB transaction
    # share the same server timestamp.
    last = (
        await db.execute(
            select(AuditChain)
            .where(AuditChain.job_id == job_id)
            .where(
                AuditChain.current_hash.not_in(
                    select(AuditChain.previous_hash)
                    .where(AuditChain.job_id == job_id)
                    .scalar_subquery()
                )
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    previous_hash = last.current_hash if last else _GENESIS_HASH
    current_hash = _compute_hash(previous_hash, payload)

    entry = AuditChain(
        job_id=job_id,
        action_type=action_type,
        payload=payload,
        previous_hash=previous_hash,
        current_hash=current_hash,
    )
    db.add(entry)

    # Flush immediately so the next log_action call within the same session
    # can read this entry's current_hash and build the chain correctly.
    # (autoflush=False in the session factory, so we must flush explicitly.)
    await db.flush()

    logger.info(
        "Audit chain entry appended",
        job_id=str(job_id),
        action_type=action_type,
        current_hash=current_hash[:16] + "...",
    )
    return entry


async def verify_chain(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
) -> dict[str, Any]:
    """
    Verify the cryptographic integrity of a job's entire audit chain.

    The chain is walked by FOLLOWING the `previous_hash -> current_hash`
    linkage starting from GENESIS, NOT by `created_at`.  Multiple entries
    inserted in a single DB transaction share an identical `created_at`
    timestamp; a created_at-ordered walk would therefore traverse them in
    arbitrary order and falsely report the chain as broken.  Following the
    structural linkage is both deterministic and correct regardless of
    timestamp ties or row-physical layout in Postgres.
    """
    from app.models.audit_chain import AuditChain

    # Pull every entry once. We index by previous_hash to walk the chain.
    entries = (
        await db.execute(
            select(AuditChain).where(AuditChain.job_id == job_id)
        )
    ).scalars().all()

    # Stable response order (independent of physical row order)
    entries_sorted = sorted(
        entries,
        key=lambda e: (e.created_at, str(e.id)),
    )
    entries_dicts = [e.to_dict() for e in entries_sorted]

    if not entries:
        return {
            "job_id":        str(job_id),
            "total_entries": 0,
            "chain_valid":   True,
            "failure_index": None,
            "entries":       [],
        }

    # ---------------------------------------------------------------------
    # Walk the chain by linkage: GENESIS -> entry whose previous_hash is
    # GENESIS -> entry whose previous_hash is that one's current_hash, ...
    # ---------------------------------------------------------------------
    by_prev: dict[str, list[AuditChain]] = {}
    for e in entries:
        by_prev.setdefault(e.previous_hash, []).append(e)

    chain_valid = True
    failure_index: int | None = None
    walked: list[AuditChain] = []
    visited_ids: set = set()
    expected_prev = _GENESIS_HASH

    while True:
        next_candidates = by_prev.get(expected_prev, [])
        # Filter out entries we've already walked (defensive against cycles)
        next_candidates = [c for c in next_candidates if c.id not in visited_ids]
        if not next_candidates:
            break

        # If multiple entries claim the same previous_hash, the chain has
        # forked -- pick the lowest-id deterministically and flag the chain
        # as broken at this point. (A correctly built chain has at most one
        # entry per previous_hash.)
        if len(next_candidates) > 1:
            chain_valid = False
            failure_index = len(walked)
            logger.error(
                "Audit chain forked at previous_hash",
                job_id=str(job_id),
                previous_hash=expected_prev[:16],
                fork_count=len(next_candidates),
            )
            next_candidates.sort(key=lambda c: str(c.id))

        entry = next_candidates[0]

        # Re-derive current_hash and compare
        expected_current = _compute_hash(entry.previous_hash, entry.payload)
        if entry.current_hash != expected_current:
            chain_valid = False
            if failure_index is None:
                failure_index = len(walked)
            logger.error(
                "Audit chain hash mismatch -- tamper detected",
                job_id=str(job_id),
                entry_id=str(entry.id),
                expected_hash=expected_current[:16],
                stored_hash=entry.current_hash[:16],
            )
            walked.append(entry)
            visited_ids.add(entry.id)
            break

        walked.append(entry)
        visited_ids.add(entry.id)
        expected_prev = entry.current_hash

    # If we couldn't walk every entry, some are orphaned -- chain is broken.
    if len(walked) != len(entries):
        chain_valid = False
        if failure_index is None:
            failure_index = len(walked)
        logger.error(
            "Audit chain has orphaned entries",
            job_id=str(job_id),
            walked=len(walked),
            total=len(entries),
        )

    result = {
        "job_id":        str(job_id),
        "total_entries": len(entries),
        "chain_valid":   chain_valid,
        "failure_index": failure_index,
        "entries":       entries_dicts,
    }

    if chain_valid:
        logger.info(
            "Audit chain verified OK",
            job_id=str(job_id),
            total_entries=len(entries),
        )
    return result
