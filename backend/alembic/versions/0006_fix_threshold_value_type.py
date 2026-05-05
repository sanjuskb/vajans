"""Change criteria.threshold_value from VARCHAR to DOUBLE PRECISION.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-27

threshold_value was created as String(255) but the AI pipeline receives
numeric values (int/float) from the LLM.  asyncpg raises
"invalid input for query argument: expected str, got int" on every insert.

The USING clause converts any existing string rows that look like numbers
(e.g. "5", "100.0") and NULLs out anything that cannot be parsed as a float.
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "criteria",
        "threshold_value",
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "  WHEN threshold_value ~ '^[0-9]+(\\.[0-9]+)?$' "
            "  THEN threshold_value::DOUBLE PRECISION "
            "  ELSE NULL "
            "END"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "criteria",
        "threshold_value",
        type_=sa.String(255),
        existing_nullable=True,
        postgresql_using="threshold_value::TEXT",
    )
