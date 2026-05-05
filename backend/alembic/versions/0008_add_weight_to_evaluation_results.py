"""Add weight and weighted_score to evaluation_results (Phase 4 complete).

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluation_results",
                  sa.Column("weight",         sa.Float(), nullable=False, server_default="1.0"))
    op.add_column("evaluation_results",
                  sa.Column("weighted_score", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    op.drop_column("evaluation_results", "weighted_score")
    op.drop_column("evaluation_results", "weight")
