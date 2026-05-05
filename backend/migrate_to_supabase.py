import asyncio
import sys
import os

sys.path.insert(0, '/home/sanju/vajans/backend')
os.environ['ENVIRONMENT'] = 'production'


async def migrate():
    from app.db.session import engine, Base
    # Import all models to register with metadata
    from app.models import (  # noqa: F401
        Job, File, Chunk, ExtractedData, AuditLog,
        AuditChain, CriterionDB, ExtractionResultDB, Result,
        EvaluationResult, ReviewAction,
    )

    print("Connecting to Supabase...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ All tables created in Supabase")

    from sqlalchemy import text
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT current_database()"))
        print(f"✓ Connected to: {r.scalar()}")

        r = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in r.fetchall()]
        print(f"✓ Tables in Supabase ({len(tables)}): {tables}")


if __name__ == "__main__":
    asyncio.run(migrate())
