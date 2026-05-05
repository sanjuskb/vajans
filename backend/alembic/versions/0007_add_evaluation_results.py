"""Add evaluation_results table (Phase 4).

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_results",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id",     ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_id",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bidder_file_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("files.id",    ondelete="CASCADE"), nullable=True),
        sa.Column("verdict",        sa.String(16), nullable=False),
        sa.Column("score",          sa.Float,      nullable=False, server_default="0.0"),
        sa.Column("explanation",    sa.Text,       nullable=False, server_default=""),
        sa.Column("created_at",     sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evaluation_results_job_id",       "evaluation_results", ["job_id"])
    op.create_index("ix_evaluation_results_criterion_id", "evaluation_results", ["criterion_id"])


def downgrade() -> None:
    op.drop_table("evaluation_results")
