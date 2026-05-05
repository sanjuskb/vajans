"""Fix Phase 5 enum label casing — SQLAlchemy uses member .name (uppercase).

Migration 0009 added lowercase labels ('review_needed', 'approve', etc.)
but SQLAlchemy serialises enum members by .name, so the DB labels must be
uppercase ('REVIEW_NEEDED', 'APPROVE', etc.) to match what the ORM inserts.

PostgreSQL does not allow removing enum labels, so we add the correct uppercase
labels alongside the now-unused lowercase ones.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-28
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # auditaction: add uppercase variants for the two Phase 5 values
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'REVIEW_NEEDED'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'REVIEW_SUBMITTED'")

    # revieweraction: add uppercase variants (0009 added lowercase ones)
    op.execute("ALTER TYPE revieweraction ADD VALUE IF NOT EXISTS 'APPROVE'")
    op.execute("ALTER TYPE revieweraction ADD VALUE IF NOT EXISTS 'EDIT'")
    op.execute("ALTER TYPE revieweraction ADD VALUE IF NOT EXISTS 'REJECT'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — no-op.
    pass
