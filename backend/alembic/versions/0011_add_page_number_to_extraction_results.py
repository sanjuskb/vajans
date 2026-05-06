"""Add page_number to extraction_results (Phase 6 PDF deep-link).

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-06

Stores the 1-indexed PDF page where the extracted source_snippet was found.
Populated post-extraction by matching snippet text against the bidder's chunks
(each chunk already carries its source page in `chunks.page`).

Nullable so existing rows remain valid until backfill.
"""

import sqlalchemy as sa
from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extraction_results",
        sa.Column("page_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extraction_results", "page_number")
