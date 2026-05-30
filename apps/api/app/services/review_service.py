"""Review Agent + 归因（Phase 4）。"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Decision,
    DecisionOutcome,
    DecisionStatus,
    MemoryType,
    OutcomeStatus,
    Security,
)
from app.services.memory_service import create_memory
from app.services.portfolio_service import get_portfolio_summary


def list_open_decisions(db: Session, portfolio_id: UUID | None = None) -> list:
    q = (
        select(Decision)
        .where(Decision.status == DecisionStatus.executed)
        .options(joinedload(Decision.security), joinedload(Decision.assumptions))
    )
    if portfolio_id:
        q = q.where(Decision.portfolio_id == portfolio_id)
    decisions = db.scalars(q).all()
    result = []
    for d in decisions:
        outcome = db.scalar(
            select(DecisionOutcome).where(DecisionOutcome.decision_id == d.id)
        )
        if outcome and outcome.outcome_status == OutcomeStatus.closed:
            continue
        ret = _estimate_return(db, d)
        result.append(
            {
                "decision_id": str(d.id),
                "symbol": d.security.symbol,
                "name": d.security.name,
                "action": d.action.value,
                "executed_at": d.executed_at.isoformat() if d.executed_at else None,
                "return_since_decision_pct": ret,
                "has_outcome": outcome is not None,
            }
        )
    return result


def _estimate_return(db: Session, decision: Decision) -> float | None:
    sec = decision.security
    if not sec or not sec.last_price:
        return None
    entry = decision.cio_summary.get("entry_price") if decision.cio_summary else None
    if entry:
        entry_price = float(entry)
    else:
        entry_price = float(sec.last_price) * 0.97
    current = float(sec.last_price)
    if decision.action.value in ("sell", "reduce"):
        return round((entry_price - current) / entry_price * 100, 2)
    return round((current - entry_price) / entry_price * 100, 2)


def review_decision(db: Session, decision_id: UUID) -> DecisionOutcome:
    decision = db.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(
            joinedload(Decision.security),
            joinedload(Decision.assumptions),
        )
    )
    if not decision:
        raise ValueError("决策不存在")

    ret = _estimate_return(db, decision) or 0.0
    assumption_results = []
    for a in decision.assumptions:
        result = "open"
        if ret > 5:
            result = "validated"
        elif ret < -5:
            result = "invalidated"
        assumption_results.append(
            {
                "assumption_text": a.assumption_text,
                "result": result,
                "evidence": f"决策后收益约 {ret}%",
            }
        )

    right, wrong = [], []
    if ret > 0:
        right.append("方向判断与股价表现一致")
    else:
        wrong.append("股价表现弱于预期，需检视假设")
    if decision.action.value in ("add", "buy") and ret < -8:
        wrong.append("加仓后回撤较大，可能违反安全边际原则")

    summary = (
        f"{decision.security.name} {decision.action.value} 决策复盘："
        f"迄今收益约 {ret}%。"
    )

    existing = db.scalar(
        select(DecisionOutcome).where(DecisionOutcome.decision_id == decision_id)
    )
    if existing:
        existing.return_since_decision_pct = Decimal(str(ret))
        existing.assumption_results = assumption_results
        existing.what_went_right = right
        existing.what_went_wrong = wrong
        existing.outcome_summary = summary
        existing.outcome_status = OutcomeStatus.closed
        existing.closed_at = datetime.now(timezone.utc)
        outcome = existing
    else:
        outcome = DecisionOutcome(
            decision_id=decision_id,
            outcome_status=OutcomeStatus.closed,
            return_since_decision_pct=Decimal(str(ret)),
            assumption_results=assumption_results,
            what_went_right=right,
            what_went_wrong=wrong,
            outcome_summary=summary,
            closed_at=datetime.now(timezone.utc),
        )
        db.add(outcome)

    if wrong:
        create_memory(
            db,
            MemoryType.lesson,
            title=f"复盘：{decision.security.symbol} {decision.action.value}",
            content="；".join(wrong),
            evidence_decision_ids=[str(decision_id)],
            active=False,
        )

    db.commit()
    db.refresh(outcome)
    return outcome


def attribution_report(db: Session, portfolio_id: UUID) -> dict:
    summary = get_portfolio_summary(db, portfolio_id)
    sector_pnl: dict[str, float] = {}
    sector_weight: dict[str, float] = {}
    for pos in summary["positions"]:
        sector = pos.get("sector") or "其他"
        sector_pnl[sector] = sector_pnl.get(sector, 0) + pos.get("unrealized_pnl", 0)
        sector_weight[sector] = sector_weight.get(sector, 0) + pos.get("weight_pct", 0)

    total_pnl = sum(sector_pnl.values()) or 1
    sectors = [
        {
            "sector": s,
            "unrealized_pnl": round(v, 2),
            "weight_pct": round(sector_weight.get(s, 0), 2),
            "contribution_pct": round(v / total_pnl * 100, 1) if total_pnl else 0,
        }
        for s, v in sorted(sector_pnl.items(), key=lambda x: -abs(x[1]))
    ]

    outcomes = db.scalars(
        select(DecisionOutcome)
        .join(Decision)
        .where(Decision.portfolio_id == portfolio_id)
    ).all()
    decision_stats = {
        "reviewed": len(outcomes),
        "avg_return_pct": round(
            sum(float(o.return_since_decision_pct or 0) for o in outcomes) / len(outcomes),
            2,
        )
        if outcomes
        else 0,
    }

    return {
        "portfolio_id": str(portfolio_id),
        "nav": summary["nav"],
        "cumulative_return_pct": summary["cumulative_return_pct"],
        "sector_attribution": sectors,
        "decision_stats": decision_stats,
    }


def backtest_decisions(db: Session, portfolio_id: UUID) -> list:
    """简化回测：已复盘决策的收益分布。"""
    rows = db.scalars(
        select(DecisionOutcome)
        .join(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            DecisionOutcome.outcome_status == OutcomeStatus.closed,
        )
    ).all()
    return [
        {
            "decision_id": str(o.decision_id),
            "return_pct": float(o.return_since_decision_pct or 0),
            "summary": o.outcome_summary,
        }
        for o in rows
    ]
