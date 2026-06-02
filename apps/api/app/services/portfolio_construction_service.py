from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Portfolio, Position, Security


def construct_target_weights(
    db: Session,
    portfolio_id: UUID,
    candidates: list[dict],
    *,
    max_turnover_pct: float = 40,
) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("组合不存在")
    if not candidates:
        return {"portfolio_id": str(portfolio_id), "targets": [], "cash_target_pct": 100.0}

    positions = db.scalars(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .options(joinedload(Position.security))
    ).all()
    current = {str(p.security_id): float(p.weight_pct or 0) for p in positions}

    score_sum = sum(max(float(c.get("score", 0)), 0) for c in candidates)
    if score_sum <= 0:
        even = round(100 / len(candidates), 4)
        raw = {str(c["security_id"]): even for c in candidates}
    else:
        raw = {str(c["security_id"]): max(float(c.get("score", 0)), 0) / score_sum * 100 for c in candidates}

    limits = portfolio.risk_limits or {}
    max_single = float(limits.get("max_single_name_pct", 10))
    min_cash = float(limits.get("min_cash_pct", 5))
    investable = max(0.0, 100 - min_cash)

    clipped = {k: min(v, max_single) for k, v in raw.items()}
    clipped_sum = sum(clipped.values())
    if clipped_sum > 0:
        factor = investable / clipped_sum
        targets = {k: round(v * factor, 4) for k, v in clipped.items()}
    else:
        targets = {}

    turnover = sum(abs(targets.get(k, 0.0) - current.get(k, 0.0)) for k in set(targets) | set(current))
    if turnover > max_turnover_pct and turnover > 0:
        shrink = max_turnover_pct / turnover
        for key in targets:
            base = current.get(key, 0.0)
            targets[key] = round(base + (targets[key] - base) * shrink, 4)

    securities = {
        str(s.id): s
        for s in db.scalars(select(Security).where(Security.id.in_([c["security_id"] for c in candidates])))
    }
    out_targets = [
        {
            "security_id": sid,
            "symbol": securities[sid].symbol if sid in securities else None,
            "target_weight_pct": weight,
            "current_weight_pct": round(current.get(sid, 0.0), 4),
        }
        for sid, weight in targets.items()
    ]
    allocated = sum(t["target_weight_pct"] for t in out_targets)
    return {
        "portfolio_id": str(portfolio_id),
        "targets": out_targets,
        "cash_target_pct": round(max(0.0, 100 - allocated), 4),
        "max_turnover_pct": max_turnover_pct,
    }
