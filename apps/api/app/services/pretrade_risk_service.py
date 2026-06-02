from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Portfolio, Position, Security


def _as_decimal(v: float | Decimal | None, default: str = "0") -> Decimal:
    if v is None:
        return Decimal(default)
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def run_pretrade_checks(
    db: Session,
    portfolio_id: UUID,
    security_id: UUID,
    *,
    target_weight_pct: float,
    order_notional: float,
    corr_value: float | None = None,
) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("组合不存在")
    security = db.get(Security, security_id)
    if not security:
        raise ValueError("标的不存在")

    positions = db.scalars(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .options(joinedload(Position.security))
    ).all()

    limits = portfolio.risk_limits or {}
    max_single = float(limits.get("max_single_name_pct", 10))
    max_sector = float(limits.get("max_sector_pct", 25))
    min_cash = float(limits.get("min_cash_pct", 5))
    max_adv_pct = float(limits.get("max_adv_pct", 20))
    max_corr = float(limits.get("max_correlation", 0.85))

    order_notional_dec = _as_decimal(order_notional)
    nav = _as_decimal(portfolio.cash_balance) + sum(_as_decimal(p.market_value) for p in positions)
    cash_after = _as_decimal(portfolio.cash_balance) - order_notional_dec
    cash_pct_after = float((cash_after / nav * 100)) if nav > 0 else 100.0

    sector_weights = defaultdict(float)
    for p in positions:
        key = p.security.sector or "unknown"
        sector_weights[key] += float(p.weight_pct or 0)
    target_sector_weight = sector_weights[security.sector or "unknown"] + target_weight_pct

    adv = (security.meta or {}).get("avg_daily_turnover")
    adv_value = float(adv) if adv else None
    adv_pct = (float(order_notional_dec) / adv_value * 100) if adv_value and adv_value > 0 else None

    checks = [
        {
            "gate_name": "position_limit_gate",
            "metric": target_weight_pct,
            "threshold": max_single,
            "passed": target_weight_pct <= max_single,
            "reason": "单票目标权重超过上限" if target_weight_pct > max_single else "",
            "action": "reject" if target_weight_pct > max_single else "allow",
        },
        {
            "gate_name": "sector_limit_gate",
            "metric": round(target_sector_weight, 4),
            "threshold": max_sector,
            "passed": target_sector_weight <= max_sector,
            "reason": "行业集中度超过上限" if target_sector_weight > max_sector else "",
            "action": "reject" if target_sector_weight > max_sector else "allow",
        },
        {
            "gate_name": "cash_buffer_gate",
            "metric": round(cash_pct_after, 4),
            "threshold": min_cash,
            "passed": cash_pct_after >= min_cash,
            "reason": "交易后现金占比低于下限" if cash_pct_after < min_cash else "",
            "action": "reject" if cash_pct_after < min_cash else "allow",
        },
        {
            "gate_name": "liquidity_gate",
            "metric": round(adv_pct, 4) if adv_pct is not None else None,
            "threshold": max_adv_pct,
            "passed": (adv_pct is None) or (adv_pct <= max_adv_pct),
            "reason": "订单金额占 ADV 比例过高" if adv_pct is not None and adv_pct > max_adv_pct else "",
            "action": "reject" if adv_pct is not None and adv_pct > max_adv_pct else "allow",
        },
        {
            "gate_name": "correlation_gate",
            "metric": corr_value,
            "threshold": max_corr,
            "passed": (corr_value is None) or (corr_value <= max_corr),
            "reason": "相关性超限" if corr_value is not None and corr_value > max_corr else "",
            "action": "reject" if corr_value is not None and corr_value > max_corr else "allow",
        },
    ]

    allowed = all(c["passed"] for c in checks)
    failed = [c["gate_name"] for c in checks if not c["passed"]]
    return {"allowed": allowed, "checks": checks, "failed_gates": failed}
