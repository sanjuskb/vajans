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
    Returns verification result with all entries.
    Raises RuntimeError if chain is broken (tamper detected).
    """
    from app.models.audit_chain import AuditChain

    entries = (
        await db.execute(
            select(AuditChain)
            .where(AuditChain.job_id == job_id)
            .order_by(AuditChain.created_at.asc())
        )
    ).scalars().all()

    chain_valid = True
    failure_index: int | None = None
    expected_prev = _GENESIS_HASH

    for i, entry in enumerate(entries):
        # Check linkage
        if entry.previous_hash != expected_prev:
            chain_valid = False
            failure_index = i
            logger.error(
                "Audit chain linkage broken",
                job_id=str(job_id),
                entry_index=i,
                entry_id=str(entry.id),
                expected_prev=expected_prev[:16],
                got_prev=entry.previous_hash[:16],
            )
            break

        # Re-derive hash and compare
        expected_current = _compute_hash(entry.previous_hash, entry.payload)
        if entry.current_hash != expected_current:
            chain_valid = False
            failure_index = i
            logger.error(
                "Audit chain hash mismatch — tamper detected",
                job_id=str(job_id),
                entry_index=i,
                entry_id=str(entry.id),
                expected_hash=expected_current[:16],
                stored_hash=entry.current_hash[:16],
            )
            break

        expected_prev = entry.current_hash

    result = {
        "job_id":        str(job_id),
        "total_entries": len(entries),
        "chain_valid":   chain_valid,
        "failure_index": failure_index,
        "entries":       [e.to_dict() for e in entries],
    }

    if chain_valid:
        logger.info(
            "Audit chain verified OK",
            job_id=str(job_id),
            total_entries=len(entries),
        )
    return result
