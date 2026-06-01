"""Risk Agent：组合约束 + strategy_rules 检查。"""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Portfolio, Security, StrategyRule
from app.services.portfolio_service import get_portfolio_summary


def check_risk(
    db: Session,
    portfolio_id: UUID,
    proposed_weights: list[dict],
) -> dict:
    """
    proposed_weights: [{security_id, symbol, weight_pct}, ...]
    剩余权重视为现金。
    """
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("组合不存在")

    limits = portfolio.risk_limits or {}
    max_single = float(limits.get("max_single_name_pct", 10))
    max_sector = float(limits.get("max_sector_pct", 25))
    min_cash = float(limits.get("min_cash_pct", 5))

    total_weight = sum(float(p["weight_pct"]) for p in proposed_weights)
    cash_pct = 100 - total_weight
    violations = []
    suggestions = []

    if cash_pct < min_cash:
        violations.append(
            {
                "code": "MIN_CASH",
                "message": f"现金占比 {cash_pct:.1f}% 低于下限 {min_cash}%",
                "limit": min_cash,
                "actual": cash_pct,
            }
        )
        scale = (100 - min_cash) / total_weight if total_weight > 0 else 1
        for p in proposed_weights:
            p["weight_pct"] = float(p["weight_pct"]) * scale
        suggestions.append({"action": "scale_down_positions", "target_cash_pct": min_cash})

    sector_exposure: dict[str, float] = {}
    for p in proposed_weights:
        w = float(p["weight_pct"])
        if w > max_single:
            violations.append(
                {
                    "code": "SINGLE_NAME_CAP",
                    "security": p.get("symbol"),
                    "proposed": w,
                    "limit": max_single,
                }
            )
            p["weight_pct"] = max_single
            suggestions.append(
                {
                    "action": "reduce",
                    "symbol": p.get("symbol"),
                    "target_weight": max_single,
                }
            )
        sec = db.get(Security, UUID(p["security_id"]))
        sector = sec.sector if sec else "其他"
        sector_exposure[sector] = sector_exposure.get(sector, 0) + float(p["weight_pct"])

    for sector, exp in sector_exposure.items():
        if exp > max_sector:
            violations.append(
                {
                    "code": "SECTOR_CAP",
                    "sector": sector,
                    "proposed": exp,
                    "limit": max_sector,
                }
            )

    rules = db.scalars(select(StrategyRule).where(StrategyRule.active.is_(True))).all()
    extra_review_symbols: list[str] = []
    for rule in rules:
        check = rule.machine_check or {}
        code = check.get("type")
        if code == "ban_action" and check.get("action") == "add":
            banned_sectors = check.get("sectors", [])
            for p in proposed_weights:
                sec = db.get(Security, UUID(p["security_id"]))
                if sec and sec.sector in banned_sectors and float(p["weight_pct"]) > 0:
                    violations.append(
                        {
                            "code": "STRATEGY_RULE",
                            "rule_code": rule.rule_code,
                            "message": rule.natural_language,
                            "symbol": sec.symbol,
                        }
                    )
                    p["weight_pct"] = 0
        elif code == "require_extra_review":
            sectors = check.get("sectors", [])
            symbols = check.get("symbols", [])
            for p in proposed_weights:
                sec = db.get(Security, UUID(p["security_id"]))
                if not sec or float(p["weight_pct"]) <= 0:
                    continue
                if sec.symbol in symbols or (sec.sector and sec.sector in sectors):
                    extra_review_symbols.append(sec.symbol)
                    violations.append(
                        {
                            "code": "REQUIRE_EXTRA_REVIEW",
                            "rule_code": rule.rule_code,
                            "message": rule.natural_language or "记忆规则：需额外复核",
                            "symbol": sec.symbol,
                        }
                    )

    approved = len(violations) == 0
    return {
        "approved": approved,
        "violations": violations,
        "suggestions": suggestions,
        "adjusted_weights": proposed_weights,
        "cash_pct": 100 - sum(float(p["weight_pct"]) for p in proposed_weights),
        "extra_review_symbols": list(dict.fromkeys(extra_review_symbols)),
    }


def portfolio_risk_dashboard(db: Session, portfolio_id: UUID) -> dict:
    summary = get_portfolio_summary(db, portfolio_id)
    portfolio = db.get(Portfolio, portfolio_id)
    limits = portfolio.risk_limits or {}
    max_single = float(limits.get("max_single_name_pct", 10))

    alerts = []
    for pos in summary["positions"]:
        if pos["weight_pct"] > max_single:
            alerts.append(
                {
                    "type": "SINGLE_NAME_CAP",
                    "symbol": pos["symbol"],
                    "weight_pct": pos["weight_pct"],
                    "limit": max_single,
                }
            )
    return {
        "limits": limits,
        "cash_pct": summary["cash_pct"],
        "alerts": alerts,
        "ok": len(alerts) == 0,
    }
