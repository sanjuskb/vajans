"""Phase 5 — Review system, audit chain, and new AuditAction values.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend existing auditaction enum with Phase 5 values ──────────────
    # ALTER TYPE … ADD VALUE cannot run inside a transaction on PG < 12.
    # On PG 12+ it is safe inside a transaction. We use IF NOT EXISTS to make
    # the migration re-runnable without error.
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'review_needed'")
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'review_submitted'")

    # ── 2. Create revieweraction enum ─────────────────────────────────────────
    revieweraction_enum = postgresql.ENUM(
        "approve", "edit", "reject",
        name="revieweraction",
        create_type=False,
    )
    revieweraction_enum.create(op.get_bind(), checkfirst=True)

    # ── 3. Create review_actions table ────────────────────────────────────────
    op.create_table(
        "review_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("criterion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "reviewer_action",
            postgresql.ENUM("approve", "edit", "reject", name="revieweraction", create_type=False),
            nullable=False,
        ),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("updated_value",  sa.Text(), nullable=True),
        sa.Column("reason",         sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"],               ["jobs.id"],               ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["criterion_id"],          ["criteria.id"],           ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_result_id"],  ["evaluation_results.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_actions_job_id",              "review_actions", ["job_id"])
    op.create_index("ix_review_actions_criterion_id",        "review_actions", ["criterion_id"])
    op.create_index("ix_review_actions_evaluation_result_id","review_actions", ["evaluation_result_id"])
    op.create_index("ix_review_actions_created_at",          "review_actions", ["created_at"])

    # ── 4. Create audit_chain table ───────────────────────────────────────────
    op.create_table(
        "audit_chain",
        sa.Column("id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type",   sa.String(128), nullable=False),
        sa.Column("payload",       postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("current_hash",  sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("current_hash", name="uq_audit_chain_current_hash"),
    )
    op.create_index("ix_audit_chain_job_id",     "audit_chain", ["job_id"])
    op.create_index("ix_audit_chain_created_at", "audit_chain", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_chain")
    op.drop_index("ix_review_actions_created_at",           table_name="review_actions")
    op.drop_index("ix_review_actions_evaluation_result_id", table_name="review_actions")
    op.drop_index("ix_review_actions_criterion_id",         table_name="review_actions")
    op.drop_index("ix_review_actions_job_id",               table_name="review_actions")
    op.drop_table("review_actions")

    op.execute("DROP TYPE IF EXISTS revieweraction")

    # Note: PostgreSQL does not support removing values from an enum type.
    # The 'review_needed' and 'review_submitted' values remain in auditaction.
