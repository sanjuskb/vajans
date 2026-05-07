"""Add review_queue_entries table and awaiting_review job status.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-07

Changes:
  1. Add 'awaiting_review' to jobstatus enum.
  2. Create reviewqueuestatus enum (pending / resolved).
  3. Create review_queue_entries table.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend jobstatus enum with new value ──────────────────────────────
    # ALTER TYPE … ADD VALUE is safe inside a transaction on PG 12+.
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'awaiting_review'")

    # ── 2. Create reviewqueuestatus enum ────────────────────────────────────
    reviewqueuestatus_enum = postgresql.ENUM(
        "pending", "resolved",
        name="reviewqueuestatus",
        create_type=False,
    )
    reviewqueuestatus_enum.create(op.get_bind(), checkfirst=True)

    # ── 3. Create review_queue_entries table ─────────────────────────────────
    op.create_table(
        "review_queue_entries",
        sa.Column("id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("criterion_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bidder_file_id",        postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evaluation_result_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "resolved", name="reviewqueuestatus", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("resolved_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by",       sa.String(128), nullable=True),
        sa.Column("review_action_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"],               ["jobs.id"],               ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"],          ["criteria.id"],           ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bidder_file_id"],        ["files.id"],              ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_result_id"],  ["evaluation_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["review_action_id"],      ["review_actions.id"],     ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_rqe_job_id",        "review_queue_entries", ["job_id"])
    op.create_index("ix_rqe_criterion_id",   "review_queue_entries", ["criterion_id"])
    op.create_index("ix_rqe_bidder_file_id", "review_queue_entries", ["bidder_file_id"])
    op.create_index("ix_rqe_status",         "review_queue_entries", ["status"])
    op.create_index("ix_rqe_created_at",     "review_queue_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_rqe_created_at",     table_name="review_queue_entries")
    op.drop_index("ix_rqe_status",         table_name="review_queue_entries")
    op.drop_index("ix_rqe_bidder_file_id", table_name="review_queue_entries")
    op.drop_index("ix_rqe_criterion_id",   table_name="review_queue_entries")
    op.drop_index("ix_rqe_job_id",         table_name="review_queue_entries")
    op.drop_table("review_queue_entries")
    op.execute("DROP TYPE IF EXISTS reviewqueuestatus")
    # Note: PostgreSQL does not support removing enum values from jobstatus.
