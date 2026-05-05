"""Add criteria and extraction_results tables (Phase 3).

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-27

criteria            — one row per eligibility criterion extracted from a tender
extraction_results  — one row per extracted field per bidder per criterion
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "criteria",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id",           postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id",  ondelete="CASCADE"), nullable=False),
        sa.Column("tender_file_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_key",    sa.String(255),  nullable=False),
        sa.Column("label",            sa.String(512),  nullable=False),
        sa.Column("criterion_type",   sa.String(64),   nullable=False, server_default="technical"),
        sa.Column("description",      sa.Text,         nullable=False, server_default=""),
        sa.Column("mandatory",        sa.Boolean,      nullable=False, server_default=sa.true()),
        sa.Column("threshold_value",  sa.String(255),  nullable=True),
        sa.Column("threshold_unit",   sa.String(128),  nullable=True),
        sa.Column("time_window_years",sa.Float,        nullable=True),
        sa.Column("operator",         sa.String(32),   nullable=True),
        sa.Column("ambiguous",        sa.Boolean,      nullable=False, server_default=sa.false()),
        sa.Column("source_snippet",   sa.Text,         nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_criteria_job_id",         "criteria", ["job_id"])
    op.create_index("ix_criteria_tender_file_id", "criteria", ["tender_file_id"])

    op.create_table(
        "extraction_results",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id",               postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id",     ondelete="CASCADE"), nullable=False),
        sa.Column("file_id",              postgresql.UUID(as_uuid=True), sa.ForeignKey("files.id",    ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name",           sa.String(255), nullable=False),
        sa.Column("raw_value",            sa.Text,        nullable=True),
        sa.Column("parsed_value",         sa.Text,        nullable=True),
        sa.Column("unit",                 sa.String(128), nullable=True),
        sa.Column("source_snippet",       sa.Text,        nullable=True),
        sa.Column("extraction_confidence",sa.Float,       nullable=False, server_default="0.0"),
        sa.Column("not_found",            sa.Boolean,     nullable=False, server_default=sa.false()),
        sa.Column("raw_llm_output",       sa.Text,        nullable=False, server_default=""),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_results_job_id",       "extraction_results", ["job_id"])
    op.create_index("ix_extraction_results_file_id",      "extraction_results", ["file_id"])
    op.create_index("ix_extraction_results_criterion_id", "extraction_results", ["criterion_id"])


def downgrade() -> None:
    op.drop_table("extraction_results")
    op.drop_table("criteria")
