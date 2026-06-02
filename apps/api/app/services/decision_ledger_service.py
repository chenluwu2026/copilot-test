from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DecisionLedger, DecisionLedgerStatus, Portfolio, Security

ALLOWED_TRANSITIONS: dict[DecisionLedgerStatus, set[DecisionLedgerStatus]] = {
    DecisionLedgerStatus.draft: {
        DecisionLedgerStatus.risk_rejected,
        DecisionLedgerStatus.approved,
        DecisionLedgerStatus.cancelled,
    },
    DecisionLedgerStatus.risk_rejected: {DecisionLedgerStatus.draft, DecisionLedgerStatus.cancelled},
    DecisionLedgerStatus.approved: {
        DecisionLedgerStatus.submitted,
        DecisionLedgerStatus.cancelled,
    },
    DecisionLedgerStatus.submitted: {
        DecisionLedgerStatus.partially_filled,
        DecisionLedgerStatus.filled,
        DecisionLedgerStatus.cancelled,
    },
    DecisionLedgerStatus.partially_filled: {
        DecisionLedgerStatus.filled,
        DecisionLedgerStatus.cancelled,
    },
    DecisionLedgerStatus.filled: {DecisionLedgerStatus.reviewed},
    DecisionLedgerStatus.cancelled: set(),
    DecisionLedgerStatus.reviewed: set(),
}


def create_ledger(
    db: Session,
    *,
    portfolio_id: UUID,
    security_id: UUID,
    run_id: str | None = None,
    decision_id: UUID | None = None,
    input_snapshot_json: dict | None = None,
    proposal_json: dict | None = None,
    risk_result_json: dict | None = None,
    execution_plan_json: dict | None = None,
) -> DecisionLedger:
    if not db.get(Portfolio, portfolio_id):
        raise ValueError("组合不存在")
    if not db.get(Security, security_id):
        raise ValueError("标的不存在")
    ledger = DecisionLedger(
        portfolio_id=portfolio_id,
        security_id=security_id,
        decision_id=decision_id,
        run_id=run_id,
        input_snapshot_json=input_snapshot_json or {},
        proposal_json=proposal_json or {},
        risk_result_json=risk_result_json or {},
        execution_plan_json=execution_plan_json or {},
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return ledger


def get_ledger(db: Session, ledger_id: UUID) -> DecisionLedger | None:
    return db.get(DecisionLedger, ledger_id)


def get_latest_ledger_by_decision(db: Session, decision_id: UUID) -> DecisionLedger | None:
    return db.scalar(
        select(DecisionLedger)
        .where(DecisionLedger.decision_id == decision_id)
        .order_by(DecisionLedger.created_at.desc())
        .limit(1)
    )


def list_ledgers(db: Session, portfolio_id: UUID | None = None, limit: int = 50) -> list[DecisionLedger]:
    q = select(DecisionLedger).order_by(DecisionLedger.created_at.desc()).limit(limit)
    if portfolio_id:
        q = q.where(DecisionLedger.portfolio_id == portfolio_id)
    return list(db.scalars(q))


def transition_ledger(
    db: Session,
    *,
    ledger_id: UUID,
    to_status: DecisionLedgerStatus,
    execution_result_json: dict | None = None,
    postmortem_json: dict | None = None,
    risk_result_json: dict | None = None,
) -> DecisionLedger:
    ledger = db.get(DecisionLedger, ledger_id)
    if not ledger:
        raise ValueError("ledger 不存在")
    allowed = ALLOWED_TRANSITIONS.get(ledger.status, set())
    if to_status not in allowed:
        raise ValueError(f"不能从 {ledger.status.value} 转到 {to_status.value}")

    ledger.status = to_status
    if execution_result_json is not None:
        ledger.execution_result_json = execution_result_json
    if postmortem_json is not None:
        ledger.postmortem_json = postmortem_json
    if risk_result_json is not None:
        ledger.risk_result_json = risk_result_json

    db.commit()
    db.refresh(ledger)
    return ledger
