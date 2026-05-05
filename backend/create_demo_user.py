#!/usr/bin/env python3
"""
Create the default demo officer user.
Run once: python3 backend/create_demo_user.py
  (from the project root, with the venv activated)
"""

import asyncio
import sys
from pathlib import Path

# Allow running from project root or backend/
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings
from app.db.session import Base
import app.models  # noqa: F401 — register all ORM models


DEMO_USERNAME = "officer"
DEMO_PASSWORD = "vajans2024"
DEMO_EMAIL    = "officer@crpf.gov.in"
DEMO_ROLE     = "officer"


async def main() -> None:
    from app.models.user import User
    from app.services.auth_service import hash_password

    engine = create_async_engine(settings.get_database_url(), echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        existing = (await db.execute(select(User).where(User.username == DEMO_USERNAME))).scalar_one_or_none()

        if existing:
            print(f"User '{DEMO_USERNAME}' already exists (id={existing.id}). Skipping.")
        else:
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
            print(f"Created user '{DEMO_USERNAME}' (id={user.id})")
            print(f"  email   : {DEMO_EMAIL}")
            print(f"  role    : {DEMO_ROLE}")
            print(f"  password: {DEMO_PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
