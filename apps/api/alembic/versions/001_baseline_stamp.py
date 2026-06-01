"""Baseline stamp for existing deployments using create_all.

Revision ID: 001_baseline
Revises:
Create Date: 2026-06-01

New installs: run `alembic revision --autogenerate` after first boot if schema drifts.
"""

from typing import Sequence, Union

revision: str = "001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
