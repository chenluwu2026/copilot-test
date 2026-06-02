"""memory tier + embedding for MEM-VEC

Revision ID: 002_quality_memory
Revises: 001_baseline_stamp
"""
from alembic import op
import sqlalchemy as sa

revision = "002_quality_memory"
down_revision = "001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memory_entries",
        sa.Column("memory_tier", sa.String(32), server_default="lesson", nullable=False),
    )
    op.add_column("memory_entries", sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("memory_entries", "embedding")
    op.drop_column("memory_entries", "memory_tier")
