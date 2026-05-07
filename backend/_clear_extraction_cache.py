"""Truncate extraction history so the next verification run regenerates with the
current extraction engine (post-denial-override). Audit chain rows for completed
jobs are preserved; only ExtractionResultDB and downstream evaluation Result rows
are cleared so the cache cannot serve pre-override values."""
import asyncio, sys
sys.path.insert(0, ".")

from sqlalchemy import delete
from app.db.session import AsyncSessionLocal
from app.models.result import ExtractionResultDB, Result


async def main():
    async with AsyncSessionLocal() as db:
        for cls in (Result, ExtractionResultDB):
            r = await db.execute(delete(cls))
            print(f"  deleted {r.rowcount} rows from {cls.__tablename__}")
        await db.commit()
asyncio.run(main())
