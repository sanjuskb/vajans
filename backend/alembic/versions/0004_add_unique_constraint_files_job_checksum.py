"""Add UNIQUE(job_id, checksum_sha256) to files table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-27

Prevents the same physical file from being uploaded more than once to the
same job.  The API now returns HTTP 409 on a duplicate before reaching the
DB, but this constraint is the authoritative safety net at the storage layer.

NOTE: If the database already contains duplicate (job_id, checksum_sha256)
pairs, remove them first:

    DELETE FROM files a
    USING files b
    WHERE a.id > b.id
      AND a.job_id = b.job_id
      AND a.checksum_sha256 = b.checksum_sha256;
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_files_job_checksum",
        "files",
        ["job_id", "checksum_sha256"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_files_job_checksum", "files", type_="unique")
