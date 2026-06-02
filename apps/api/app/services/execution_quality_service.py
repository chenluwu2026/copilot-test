"""执行质量：决策时点 vs 成交价滞后（模拟盘）。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Decision, DecisionStatus, Trade


def execution_quality_report(db: Session, portfolio_id: UUID, limit: int = 20) -> dict:
    decisions = db.scalars(
        select(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            Decision.status == DecisionStatus.executed,
        )
        .options(joinedload(Decision.security))
        .order_by(Decision.executed_at.desc())
        .limit(limit)
    ).all()

    items = []
    for d in decisions:
        trade = db.scalar(
            select(Trade)
            .where(Trade.portfolio_id == portfolio_id, Trade.security_id == d.security_id)
            .order_by(Trade.executed_at.desc())
            .limit(1)
        )
        summary = d.cio_summary or {}
        entry = summary.get("entry_price")
        exec_price = float(trade.price) if trade and trade.price else None
        slippage_pct = None
        if entry and exec_price and float(entry) > 0:
            slippage_pct = round((exec_price - float(entry)) / float(entry) * 100, 2)

        items.append(
            {
                "decision_id": str(d.id),
                "symbol": d.security.symbol if d.security else "",
                "action": d.action.value,
                "executed_at": d.executed_at.isoformat() if d.executed_at else None,
                "entry_price_hint": entry,
                "execution_price": exec_price,
                "slippage_vs_hint_pct": slippage_pct,
                "quality_flag": (
                    "ok"
                    if slippage_pct is None or abs(slippage_pct) < 2
                    else "review"
                ),
            }
        )

    flagged = sum(1 for i in items if i["quality_flag"] == "review")
    return {
        "portfolio_id": str(portfolio_id),
        "items": items,
        "flagged_count": flagged,
        "summary": f"{flagged}/{len(items)} 笔执行偏离决策价提示超过 2%" if items else "无已执行决策",
    }
