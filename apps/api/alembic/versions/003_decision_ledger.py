"""add decision ledger table

Revision ID: 003_decision_ledger
Revises: 002_quality_memory
"""

from alembic import op
import sqlalchemy as sa

revision = "003_decision_ledger"
down_revision = "002_quality_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_ledger",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("portfolio_id", sa.UUID(), nullable=False),
        sa.Column("security_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "risk_rejected",
                "approved",
                "submitted",
                "partially_filled",
                "filled",
                "cancelled",
                "reviewed",
                name="decisionledgerstatus",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("input_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("proposal_json", sa.JSON(), nullable=False),
        sa.Column("risk_result_json", sa.JSON(), nullable=False),
        sa.Column("execution_plan_json", sa.JSON(), nullable=False),
        sa.Column("execution_result_json", sa.JSON(), nullable=False),
        sa.Column("postmortem_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.ForeignKeyConstraint(["security_id"], ["securities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_ledger_portfolio_id", "decision_ledger", ["portfolio_id"])
    op.create_index("ix_decision_ledger_security_id", "decision_ledger", ["security_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_ledger_security_id", table_name="decision_ledger")
    op.drop_index("ix_decision_ledger_portfolio_id", table_name="decision_ledger")
    op.drop_table("decision_ledger")
    op.execute("DROP TYPE IF EXISTS decisionledgerstatus")
