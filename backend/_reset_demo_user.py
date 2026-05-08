#!/usr/bin/env python3
"""
VAJANS — Production officer user reset / verify.

Why this exists:
  `create_demo_user.py` uses `settings.get_database_url()` which reads
  `DATABASE_URL` from local `.env`. The Railway runtime uses
  `app.db.session._build_engine_url()` which HARDCODES the Supabase pooler
  URL when `ENVIRONMENT=production`. The two paths can resolve to different
  databases, so a "user exists locally" message is no guarantee the user
  exists on Railway's DB.

  This script forces `ENVIRONMENT=production` BEFORE importing the session
  module, so it talks to the exact same Supabase that Railway uses, and
  performs an upsert (always writes a fresh bcrypt hash of the demo
  password) so a stale hash cannot survive.

Run from anywhere (project root or backend/):
    python3 backend/_reset_demo_user.py
"""

import os
import sys
from pathlib import Path

# Force production DB resolution BEFORE importing session.py
os.environ["ENVIRONMENT"] = "production"

# Make `app` importable regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio  # noqa: E402

from sqlalchemy import func, select  # noqa: E402

import app.models  # noqa: F401,E402  — register ORM models
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import hash_password, verify_password  # noqa: E402

DEMO_USERNAME = "officer"
DEMO_PASSWORD = "vajans2024"
DEMO_EMAIL    = "officer@crpf.gov.in"
DEMO_ROLE     = "officer"


async def main() -> int:
    print("=" * 60)
    print("VAJANS — production demo user reset")
    print("=" * 60)
    print(f"Engine URL host : {engine.url.host}")
    print(f"Engine URL port : {engine.url.port}")
    print(f"Engine URL db   : {engine.url.database}")
    print(f"Engine driver   : {engine.url.drivername}")
    print()

    async with AsyncSessionLocal() as db:
        # 1. Total users
        total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        print(f"[diag] users table row count: {total}")

        # 2. Look up the officer
        existing = (
            await db.execute(select(User).where(User.username == DEMO_USERNAME))
        ).scalar_one_or_none()

        if existing is None:
            print(f"[diag] '{DEMO_USERNAME}' NOT found — creating fresh row")
            user = User(
                username=DEMO_USERNAME,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                role=DEMO_ROLE,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"[ok]   created user id={user.id}")
            target = user
        else:
            print(f"[diag] '{DEMO_USERNAME}' exists (id={existing.id})")
            print(f"[diag]   is_active     = {existing.is_active}")
            print(f"[diag]   role          = {existing.role}")
            print(f"[diag]   email         = {existing.email}")
            print(f"[diag]   hash prefix   = {existing.password_hash[:7]}…")
            current_ok = verify_password(DEMO_PASSWORD, existing.password_hash)
            print(f"[diag]   current pwd   = '{DEMO_PASSWORD}' valid? {current_ok}")

            existing.password_hash = hash_password(DEMO_PASSWORD)
            existing.is_active = True
            existing.role = DEMO_ROLE
            existing.email = DEMO_EMAIL
            await db.commit()
            await db.refresh(existing)
            print(f"[ok]   reset password + flags for id={existing.id}")
            target = existing

        # 3. Re-verify after write
        confirm = verify_password(DEMO_PASSWORD, target.password_hash)
        print(f"[ok]   post-write verify_password('{DEMO_PASSWORD}', stored_hash) = {confirm}")
        if not confirm:
            print("[FAIL] hash failed self-verification — bcrypt mismatch?")
            await engine.dispose()
            return 2

        # 4. Final state
        recount = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        print(f"[diag] users table row count (post): {recount}")

    await engine.dispose()
    print()
    print("=" * 60)
    print(f"DONE. Login with: username={DEMO_USERNAME!r}  password={DEMO_PASSWORD!r}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
