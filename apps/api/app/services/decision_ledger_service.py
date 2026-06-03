from collections import Counter
from datetime import datetime
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


def list_ledgers_by_run(
    db: Session,
    *,
    portfolio_id: UUID,
    run_id: str,
    limit: int = 100,
) -> list[DecisionLedger]:
    return list(
        db.scalars(
            select(DecisionLedger)
            .where(
                DecisionLedger.portfolio_id == portfolio_id,
                DecisionLedger.run_id == run_id,
            )
            .order_by(DecisionLedger.created_at.desc())
            .limit(limit)
        )
    )


def list_run_summaries(db: Session, portfolio_id: UUID, limit: int = 30) -> list[dict]:
    ledgers = list_ledgers(db, portfolio_id=portfolio_id, limit=500)
    by_run: dict[str, dict] = {}
    for ledger in ledgers:
        rid = ledger.run_id or ""
        if not rid.startswith("fm-"):
            continue
        row = by_run.get(rid)
        if not row:
            row = {
                "run_id": rid,
                "portfolio_id": str(ledger.portfolio_id),
                "ledger_count": 0,
                "decision_count": 0,
                "risk_rejected": 0,
                "filled": 0,
                "reviewed": 0,
                "created_at": ledger.created_at,
            }
            by_run[rid] = row
        row["ledger_count"] += 1
        if ledger.decision_id:
            row["decision_count"] += 1
        if ledger.status == DecisionLedgerStatus.risk_rejected:
            row["risk_rejected"] += 1
        if ledger.status in (DecisionLedgerStatus.filled, DecisionLedgerStatus.partially_filled):
            row["filled"] += 1
        if ledger.status == DecisionLedgerStatus.reviewed:
            row["reviewed"] += 1
        if ledger.created_at and (row["created_at"] is None or ledger.created_at > row["created_at"]):
            row["created_at"] = ledger.created_at

    out = sorted(by_run.values(), key=lambda x: x["created_at"] or datetime.min, reverse=True)[:limit]
    for row in out:
        ts = row.pop("created_at")
        row["created_at"] = ts.isoformat() if ts else None
        total = row["ledger_count"] or 1
        row["rejection_rate_pct"] = round(row["risk_rejected"] / total * 100, 1)
    return out


def gate_failure_stats(db: Session, portfolio_id: UUID, *, limit: int = 200) -> dict[str, int]:
    ledgers = list_ledgers(db, portfolio_id=portfolio_id, limit=limit)
    counter: Counter[str] = Counter()
    for ledger in ledgers:
        if not ledger.run_id:
            continue
        failed = (ledger.risk_result_json or {}).get("failed_gates") or []
        for gate in failed:
            counter[str(gate)] += 1
    return dict(counter.most_common(10))


def write_postmortem_for_decision(
    db: Session,
    *,
    decision_id: UUID,
    postmortem_json: dict,
) -> DecisionLedger | None:
    ledger = get_latest_ledger_by_decision(db, decision_id)
    if not ledger:
        return None
    ledger.postmortem_json = postmortem_json
    if ledger.status == DecisionLedgerStatus.filled:
        allowed = ALLOWED_TRANSITIONS.get(ledger.status, set())
        if DecisionLedgerStatus.reviewed in allowed:
            ledger.status = DecisionLedgerStatus.reviewed
    db.flush()
    return ledger


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
