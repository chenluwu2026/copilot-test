from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import DecisionAction
from app.services import decision_service as ds
from app.services import portfolio_construction_service as pcs
from app.services import portfolio_service as ps
from app.services import pretrade_risk_service as prs


def _pick_action(current_weight: float, target_weight: float) -> DecisionAction:
    delta = target_weight - current_weight
    if abs(delta) < 0.01:
        return DecisionAction.hold
    if delta > 0:
        return DecisionAction.add if current_weight > 0 else DecisionAction.buy
    return DecisionAction.reduce


def run_decision_pipeline(
    db: Session,
    *,
    portfolio_id: UUID,
    candidates: list[dict],
    max_turnover_pct: float = 40,
) -> dict:
    plan = pcs.construct_target_weights(
        db,
        portfolio_id=portfolio_id,
        candidates=candidates,
        max_turnover_pct=max_turnover_pct,
    )
    summary = ps.get_portfolio_summary(db, portfolio_id)
    nav = Decimal(str(summary["nav"]))

    results: list[dict] = []
    for item in plan["targets"]:
        target_weight = float(item["target_weight_pct"])
        current_weight = float(item["current_weight_pct"])
        delta_pct = abs(target_weight - current_weight)
        order_notional = float(nav * Decimal(str(delta_pct)) / Decimal("100"))

        risk = prs.run_pretrade_checks(
            db,
            portfolio_id,
            UUID(item["security_id"]),
            target_weight_pct=target_weight,
            order_notional=order_notional,
            corr_value=None,
        )

        if risk["allowed"]:
            action = _pick_action(current_weight, target_weight)
            decision = ds.create_decision(
                db,
                portfolio_id=portfolio_id,
                security_id=UUID(item["security_id"]),
                action=action,
                decision_reason=f"自动组合构建建议：目标权重 {target_weight:.2f}%",
                current_weight_pct=current_weight,
                target_weight_pct=target_weight,
                main_risks=[],
                review_conditions=[],
                assumptions=[],
                references=[{"ref_type": "factor", "excerpt": "pipeline auto-generated"}],
                confidence_grade="B",
                holding_period="1-3个月",
                cio_summary=None,
                created_by_agent="decision_pipeline",
            )
            results.append(
                {
                    "security_id": item["security_id"],
                    "symbol": item["symbol"],
                    "allowed": True,
                    "risk": risk,
                    "decision_id": str(decision.id),
                    "action": action.value,
                    "target_weight_pct": target_weight,
                    "current_weight_pct": current_weight,
                }
            )
        else:
            results.append(
                {
                    "security_id": item["security_id"],
                    "symbol": item["symbol"],
                    "allowed": False,
                    "risk": risk,
                    "decision_id": None,
                    "action": "watch",
                    "target_weight_pct": target_weight,
                    "current_weight_pct": current_weight,
                }
            )

    return {
        "portfolio_id": str(portfolio_id),
        "targets": plan["targets"],
        "cash_target_pct": plan["cash_target_pct"],
        "results": results,
    }
