"""Add job_id FK constraints to extracted_data and results tables.

Revision ID: 0003
Revises: e392a01fa753
Create Date: 2026-04-27

Previously job_id in these two tables was a bare UUID column with no
referential integrity constraint.  Deleting a Job would leave orphaned
rows because no CASCADE rule existed.  This migration adds the missing
foreign keys.

NOTE: Run `DELETE FROM extracted_data WHERE job_id NOT IN (SELECT id FROM jobs)`
and the same for `results` if your database already contains orphaned rows,
otherwise this migration will fail with a FK violation error.
"""

from alembic import op

revision = "0003"
down_revision = "e392a01fa753"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_extracted_data_job_id",
        "extracted_data", "jobs",
        ["job_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_results_job_id",
        "results", "jobs",
        ["job_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_results_job_id",       "results",        type_="foreignkey")
    op.drop_constraint("fk_extracted_data_job_id", "extracted_data", type_="foreignkey")
