import os, asyncio
os.environ["ENVIRONMENT"] = "production"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from app.db.session import engine

ENUMS = ["jobstatus", "filetype", "filestatus", "auditaction",
         "evaluationverdict", "trustlevel", "revieweraction", "reviewqueuestatus"]

async def go():
    async with engine.connect() as c:
        for e in ENUMS:
            try:
                r = await c.execute(text(f"SELECT enum_range(NULL::{e})::text"))
                print(f"{e:25s} = {r.scalar()}")
            except Exception as exc:
                print(f"{e:25s} = ERROR: {exc.__class__.__name__}")
    await engine.dispose()

asyncio.run(go())
