"""Review Agent + 归因（Phase 4）：基于真实 K 线的决策后收益。"""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Decision,
    DecisionAction,
    DecisionOutcome,
    DecisionStatus,
    MemoryType,
    OutcomeStatus,
)
from app.services.market_data_service import get_close_on_or_before, get_latest_close
from app.services.memory_service import create_memory
from app.services.portfolio_service import get_portfolio_summary


def compute_decision_return(db: Session, decision: Decision) -> dict:
    """
    计算决策后收益率。
    入场价优先：cio_summary.entry_price → 执行日 K 线 → 估算。
    出场价：最新 K 线收盘价。
    """
    sec = decision.security
    if not sec:
        return {"return_pct": None, "price_source": "missing"}

    entry_price: float | None = None
    entry_date: date | None = None
    entry_source = "estimate"

    summary = decision.cio_summary or {}
    if summary.get("entry_price"):
        entry_price = float(summary["entry_price"])
        entry_source = "execute_price"
        if decision.executed_at:
            entry_date = decision.executed_at.date()

    if entry_price is None and decision.executed_at:
        d = decision.executed_at.date()
        bar_close, bar_d = get_close_on_or_before(db, sec.id, d)
        if bar_close is not None:
            entry_price = bar_close
            entry_date = bar_d
            entry_source = "bars"

    if entry_price is None and sec.last_price:
        entry_price = float(sec.last_price) * 0.97
        entry_source = "estimate"

    exit_price, exit_date, exit_source = get_latest_close(db, sec.id)
    if entry_price is None or exit_price is None or entry_price <= 0:
        return {
            "return_pct": None,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_source": entry_source,
            "exit_source": exit_source,
            "price_source": "missing",
        }

    raw = (exit_price - entry_price) / entry_price * 100
    if decision.action in (DecisionAction.sell, DecisionAction.reduce):
        ret = round(-raw, 2)
    else:
        ret = round(raw, 2)

    price_source = "bars" if entry_source in ("bars", "execute_price") and exit_source == "bars" else "mixed"
    if entry_source == "estimate":
        price_source = "estimate"

    return {
        "return_pct": ret,
        "entry_price": round(entry_price, 4),
        "exit_price": round(exit_price, 4),
        "entry_date": entry_date.isoformat() if entry_date else None,
        "exit_date": exit_date.isoformat() if exit_date else None,
        "entry_source": entry_source,
        "exit_source": exit_source,
        "price_source": price_source,
    }


def _maybe_enrich_review_llm(db, decision, assumption_results, right, wrong, summary, ret, meta):
    from app.services.event_service import list_events
    from app.services.llm.client import use_llm_agents

    if not use_llm_agents():
        return assumption_results, right, wrong, summary
    try:
        from app.services.llm.client import complete_json

        events = list_events(db, security_id=decision.security_id, limit=3)
        ev_text = "; ".join((e.get("summary") or "")[:80] for e in events)
        user = (
            f"决策：{decision.security.symbol} {decision.action.value}\n"
            f"理由：{decision.decision_reason[:300]}\n"
            f"假设：{[a.assumption_text for a in decision.assumptions]}\n"
            f"收益{ret}%，入场{meta.get('entry_price')}现价{meta.get('exit_price')}\n"
            f"近期事件：{ev_text}\n"
            "输出 JSON: {assumption_results:[{assumption_text,result,measurable_evidence}], "
            "what_went_right:[], what_went_wrong:[], outcome_summary:''}"
        )
        raw = complete_json(
            "你是 Review Agent。结合价格与事件复盘，判断假设 validated/invalidated/open，中文简洁。",
            user,
        )
        if raw.get("assumption_results"):
            assumption_results = raw["assumption_results"]
        if raw.get("what_went_right"):
            right = raw["what_went_right"]
        if raw.get("what_went_wrong"):
            wrong = raw["what_went_wrong"]
        if raw.get("outcome_summary"):
            summary = raw["outcome_summary"]
    except Exception:
        pass
    return assumption_results, right, wrong, summary


def list_open_decisions(db: Session, portfolio_id: UUID | None = None) -> list:
    q = (
        select(Decision)
        .where(Decision.status == DecisionStatus.executed)
        .options(joinedload(Decision.security), joinedload(Decision.assumptions))
    )
    if portfolio_id:
        q = q.where(Decision.portfolio_id == portfolio_id)
    decisions = db.scalars(q).unique().all()
    result = []
    for d in decisions:
        outcome = db.scalar(
            select(DecisionOutcome).where(DecisionOutcome.decision_id == d.id)
        )
        if outcome and outcome.outcome_status == OutcomeStatus.closed:
            continue
        meta = compute_decision_return(db, d)
        result.append(
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
            }
        )
    return result


def review_decision(db: Session, decision_id: UUID) -> tuple[DecisionOutcome, str | None]:
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

    meta = compute_decision_return(db, decision)
    ret = meta.get("return_pct")
    if ret is None:
        ret = 0.0

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
                "evidence": (
                    f"入场 {meta.get('entry_price')} ({meta.get('entry_source')}) → "
                    f"现价 {meta.get('exit_price')} ({meta.get('exit_source')})，"
                    f"收益 {ret}%"
                ),
            }
        )

    right, wrong = [], []
    if ret > 0:
        right.append("方向判断与股价表现一致")
    else:
        wrong.append("股价表现弱于预期，需检视假设")
    if decision.action in (DecisionAction.add, DecisionAction.buy) and ret < -8:
        wrong.append("加仓后回撤较大，可能违反安全边际原则")

    summary = (
        f"{decision.security.name} {decision.action.value} 决策复盘："
        f"入场 {meta.get('entry_price')} → 现价 {meta.get('exit_price')}，"
        f"收益 {ret}%（数据源：{meta.get('price_source')}）。"
    )

    assumption_results, right, wrong, summary = _maybe_enrich_review_llm(
        db, decision, assumption_results, right, wrong, summary, ret, meta
    )

    existing = db.scalar(
        select(DecisionOutcome).where(DecisionOutcome.decision_id == decision_id)
    )
    price_meta = {
        "entry_price": meta.get("entry_price"),
        "exit_price": meta.get("exit_price"),
        "entry_source": meta.get("entry_source"),
        "exit_source": meta.get("exit_source"),
        "price_source": meta.get("price_source"),
    }
    if existing:
        existing.return_since_decision_pct = Decimal(str(ret))
        existing.assumption_results = assumption_results
        existing.what_went_right = right
        existing.what_went_wrong = wrong
        existing.outcome_summary = summary
        existing.outcome_status = OutcomeStatus.closed
        existing.closed_at = datetime.now(timezone.utc)
        existing.price_metadata = price_meta
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
            price_metadata=price_meta,
        )
        db.add(outcome)

    memory_id = None
    if wrong:
        mem = create_memory(
            db,
            MemoryType.lesson,
            title=f"复盘：{decision.security.symbol} {decision.action.value}",
            content="；".join(wrong) + f"（{summary}）",
            evidence_decision_ids=[str(decision_id)],
            active=False,
        )
        memory_id = str(mem.id)

    db.commit()
    db.refresh(outcome)
    return outcome, memory_id


def promote_outcome_to_memory(
    db: Session, decision_id: UUID, title: str | None = None, activate: bool = False
) -> dict:
    """从已复盘决策一键沉淀记忆。"""
    outcome = db.scalar(
        select(DecisionOutcome).where(DecisionOutcome.decision_id == decision_id)
    )
    if not outcome:
        raise ValueError("请先运行复盘")
    decision = db.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(joinedload(Decision.security))
    )
    if not decision:
        raise ValueError("决策不存在")
    mem_title = title or f"复盘沉淀：{decision.security.symbol}"
    content = outcome.outcome_summary or "；".join(outcome.what_went_wrong or outcome.what_went_right or [])
    mem = create_memory(
        db,
        MemoryType.lesson,
        mem_title,
        content,
        evidence_decision_ids=[str(decision_id)],
        active=activate,
    )
    return {"memory_id": str(mem.id), "active": mem.active, "pending": mem.pending}


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
        select(DecisionOutcome).join(Decision).where(Decision.portfolio_id == portfolio_id)
    ).all()
    returns = [float(o.return_since_decision_pct or 0) for o in outcomes]
    decision_stats = {
        "reviewed": len(outcomes),
        "avg_return_pct": round(sum(returns) / len(returns), 2) if returns else 0,
        "win_rate_pct": round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1) if returns else 0,
        "best_pct": max(returns) if returns else 0,
        "worst_pct": min(returns) if returns else 0,
    }

    return {
        "portfolio_id": str(portfolio_id),
        "nav": summary["nav"],
        "cumulative_return_pct": summary["cumulative_return_pct"],
        "sector_attribution": sectors,
        "decision_stats": decision_stats,
    }


def backtest_decisions(db: Session, portfolio_id: UUID) -> list:
    rows = db.scalars(
        select(DecisionOutcome)
        .join(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            DecisionOutcome.outcome_status == OutcomeStatus.closed,
        )
        .options(joinedload(DecisionOutcome.decision).joinedload(Decision.security))
    ).all()
    return [
        {
            "decision_id": str(o.decision_id),
            "symbol": o.decision.security.symbol if o.decision.security else "",
            "name": o.decision.security.name if o.decision.security else "",
            "action": o.decision.action.value if o.decision else "",
            "return_pct": float(o.return_since_decision_pct or 0),
            "summary": o.outcome_summary,
            "price_source": (o.price_metadata or {}).get("price_source"),
        }
        for o in rows
    ]
