"""add embedding_id to chunks

Revision ID: 0001
Revises:
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column("embedding_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chunks", "embedding_id")
