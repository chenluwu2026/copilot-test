"""复盘到期判断与待沉淀记忆列表。"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Decision, DecisionOutcome, MemoryEntry, OutcomeStatus
from app.services.memory_service import activate_memory


def _days_since(dt: datetime | None) -> int | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def review_due_meta(
    *,
    executed_at: datetime | None,
    return_pct: float | None,
    profile: dict,
) -> dict:
    due_days = int(profile.get("review_due_days", 30))
    material_pct = float(profile.get("review_material_move_pct", 8))
    days = _days_since(executed_at)
    material_move = return_pct is not None and abs(return_pct) >= material_pct
    time_due = days is not None and days >= due_days
    review_due = time_due or material_move
    if days is None:
        urgency = "unknown"
    elif days >= due_days * 1.5:
        urgency = "overdue"
    elif review_due:
        urgency = "due"
    else:
        urgency = "ok"
    return {
        "days_since_execution": days,
        "review_due_days": due_days,
        "review_due": review_due,
        "material_move": material_move,
        "urgency": urgency,
    }


def memories_for_decision(db: Session, decision_id: UUID) -> list[MemoryEntry]:
    did = str(decision_id)
    rows = db.scalars(select(MemoryEntry).order_by(MemoryEntry.created_at.desc())).all()
    return [m for m in rows if did in (m.evidence_decision_ids or [])]


def review_summary(db: Session, portfolio_id: UUID, profile: dict) -> dict:
    open_items = _collect_open_decisions(db, portfolio_id, profile)
    pending_mem = list_pending_memory_promotions(db, portfolio_id)
    due_count = sum(1 for x in open_items if x["review_due"])
    overdue_count = sum(1 for x in open_items if x["urgency"] == "overdue")
    return {
        "portfolio_id": str(portfolio_id),
        "open_count": len(open_items),
        "due_count": due_count,
        "overdue_count": overdue_count,
        "pending_memory_count": len(pending_mem),
        "review_due_days": int(profile.get("review_due_days", 30)),
    }


def _collect_open_decisions(db: Session, portfolio_id: UUID, profile: dict) -> list[dict]:
    from app.models import DecisionStatus
    from app.services.review_service import compute_decision_return

    q = (
        select(Decision)
        .where(
            Decision.status == DecisionStatus.executed,
            Decision.portfolio_id == portfolio_id,
        )
        .options(joinedload(Decision.security), joinedload(Decision.assumptions))
    )
    decisions = db.scalars(q).unique().all()
    items: list[dict] = []
    for d in decisions:
        outcome = db.scalar(
            select(DecisionOutcome).where(DecisionOutcome.decision_id == d.id)
        )
        if outcome and outcome.outcome_status == OutcomeStatus.closed:
            continue
        meta = compute_decision_return(db, d)
        due = review_due_meta(
            executed_at=d.executed_at,
            return_pct=meta.get("return_pct"),
            profile=profile,
        )
        linked = memories_for_decision(db, d.id)
        pending_memory_id = next(
            (str(m.id) for m in linked if m.pending and not m.active),
            None,
        )
        from app.services.decision_ledger_service import get_latest_ledger_by_decision

        ledger = get_latest_ledger_by_decision(db, d.id)
        ledger_status = ledger.status.value if ledger else None
        run_id = ledger.run_id if ledger else None
        has_postmortem = bool(ledger and (ledger.postmortem_json or {}))
        items.append(
            {
                "decision_id": str(d.id),
                "symbol": d.security.symbol,
                "name": d.security.name,
                "action": d.action.value,
                "executed_at": d.executed_at.isoformat() if d.executed_at else None,
                "return_since_decision_pct": meta.get("return_pct"),
                "price_source": meta.get("price_source"),
                "entry_price": meta.get("entry_price"),
                "exit_price": meta.get("exit_price"),
                "has_outcome": outcome is not None,
                "pending_memory_id": pending_memory_id,
                "ledger_status": ledger_status,
                "run_id": run_id,
                "has_postmortem": has_postmortem,
                **due,
            }
        )
    urgency_order = {"overdue": 0, "due": 1, "ok": 2, "unknown": 3}
    items.sort(
        key=lambda x: (
            urgency_order.get(x["urgency"], 9),
            -(x["days_since_execution"] or 0),
        )
    )
    return items


def list_open_decisions_enriched(
    db: Session, portfolio_id: UUID | None, profile: dict
) -> list[dict]:
    if not portfolio_id:
        from app.models import DecisionStatus
        from app.services.review_service import compute_decision_return

        q = (
            select(Decision)
            .where(Decision.status == DecisionStatus.executed)
            .options(joinedload(Decision.security), joinedload(Decision.assumptions))
        )
        decisions = db.scalars(q).unique().all()
        items = []
        for d in decisions:
            outcome = db.scalar(
                select(DecisionOutcome).where(DecisionOutcome.decision_id == d.id)
            )
            if outcome and outcome.outcome_status == OutcomeStatus.closed:
                continue
            meta = compute_decision_return(db, d)
            due = review_due_meta(
                executed_at=d.executed_at,
                return_pct=meta.get("return_pct"),
                profile=profile,
            )
            items.append(
                {
                    "decision_id": str(d.id),
                    "symbol": d.security.symbol,
                    "name": d.security.name,
                    "action": d.action.value,
                    "executed_at": d.executed_at.isoformat() if d.executed_at else None,
                    "return_since_decision_pct": meta.get("return_pct"),
                    "price_source": meta.get("price_source"),
                    "has_outcome": outcome is not None,
                    **due,
                }
            )
        return items
    return _collect_open_decisions(db, portfolio_id, profile)


def list_pending_memory_promotions(db: Session, portfolio_id: UUID) -> list[dict]:
    """已复盘但未激活记忆的决策。"""
    outcomes = db.scalars(
        select(DecisionOutcome)
        .join(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            DecisionOutcome.outcome_status == OutcomeStatus.closed,
        )
        .options(joinedload(DecisionOutcome.decision).joinedload(Decision.security))
    ).all()
    result = []
    for o in outcomes:
        decision = o.decision
        if not decision or not decision.security:
            continue
        linked = memories_for_decision(db, o.decision_id)
        if any(m.active for m in linked):
            continue
        pending = next((m for m in linked if m.pending), None)
        result.append(
            {
                "decision_id": str(o.decision_id),
                "symbol": decision.security.symbol,
                "name": decision.security.name,
                "action": decision.action.value,
                "return_pct": float(o.return_since_decision_pct or 0),
                "outcome_summary": o.outcome_summary,
                "pending_memory_id": str(pending.id) if pending else None,
            }
        )
    return result


def promote_or_activate_memory(
    db: Session,
    decision_id: UUID,
    title: str | None = None,
    activate: bool = False,
) -> dict:
    """沉淀记忆；若已有 pending 记忆则复用，避免重复创建。"""
    from app.services.review_service import promote_outcome_to_memory

    linked = memories_for_decision(db, decision_id)
    pending = next((m for m in linked if m.pending and not m.active), None)
    if pending:
        if activate:
            m = activate_memory(db, pending.id)
            return {"memory_id": str(m.id), "active": m.active, "pending": m.pending, "reused": True}
        return {
            "memory_id": str(pending.id),
            "active": pending.active,
            "pending": pending.pending,
            "reused": True,
        }
    if any(m.active for m in linked):
        m = linked[0]
        return {"memory_id": str(m.id), "active": m.active, "pending": m.pending, "reused": True}
    return {**promote_outcome_to_memory(db, decision_id, title, activate), "reused": False}
