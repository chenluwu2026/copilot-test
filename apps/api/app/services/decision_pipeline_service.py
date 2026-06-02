from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import DecisionAction, Security
from app.models import DecisionLedgerStatus, DecisionStatus
from app.services import decision_ledger_service as dls
from app.services import decision_service as ds
from app.services import execution_simulator_service as ess
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


def _execution_schedule(adv_ratio_pct: float) -> dict:
    if adv_ratio_pct <= 2:
        return {"style": "single-shot", "slices": 1, "horizon_minutes": 5}
    if adv_ratio_pct <= 8:
        return {"style": "twap", "slices": 4, "horizon_minutes": 30}
    return {"style": "twap", "slices": 8, "horizon_minutes": 90}


def run_decision_pipeline(
    db: Session,
    *,
    portfolio_id: UUID,
    candidates: list[dict],
    max_turnover_pct: float = 40,
    auto_approve: bool = False,
    auto_execute_simulated: bool = False,
    simulated_fill_ratio: float = 1.0,
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
        sec = db.get(Security, UUID(item["security_id"]))
        px = float(sec.last_price or 0) if sec else 0.0
        qty = (order_notional / px) if px > 0 else 0.0
        adv_notional = float((sec.meta or {}).get("avg_daily_turnover") or 0) if sec else 0.0
        execution_sim = ess.simulate_execution(
            side=_pick_action(current_weight, target_weight).value,
            quantity=qty,
            reference_price=px if px > 0 else 1.0,
            adv_notional=adv_notional if adv_notional > 0 else None,
            fill_ratio=1.0,
        )
        adv_ratio_pct = (order_notional / adv_notional * 100) if adv_notional > 0 else 0.0
        execution_plan = {
            "order_notional": order_notional,
            "estimated_quantity": qty,
            "estimated_slippage_bps": execution_sim["slippage_bps"],
            "estimated_shortfall": execution_sim["implementation_shortfall"],
            "adv_ratio_pct": adv_ratio_pct,
            "schedule": _execution_schedule(adv_ratio_pct),
        }

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
            auto_approved = False
            simulated_execution = None
            if auto_approve:
                decision = ds.update_decision_status(db, decision.id, DecisionStatus.approved)
                auto_approved = True
            if auto_execute_simulated and auto_approved:
                simulated_execution = ess.simulate_execution(
                    side=action.value,
                    quantity=execution_plan["estimated_quantity"],
                    reference_price=px if px > 0 else 1.0,
                    adv_notional=adv_notional if adv_notional > 0 else None,
                    fill_ratio=simulated_fill_ratio,
                )
                ledger = dls.get_latest_ledger_by_decision(db, decision.id)
                if ledger:
                    try:
                        dls.transition_ledger(
                            db,
                            ledger_id=ledger.id,
                            to_status=DecisionLedgerStatus.submitted,
                        )
                    except ValueError:
                        pass
                    try:
                        dls.transition_ledger(
                            db,
                            ledger_id=ledger.id,
                            to_status=DecisionLedgerStatus.filled,
                            execution_result_json={
                                "mode": "simulated",
                                **simulated_execution,
                            },
                        )
                    except ValueError:
                        pass
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
                    "execution_plan": execution_plan,
                    "auto_approved": auto_approved,
                    "simulated_execution": simulated_execution,
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
                    "execution_plan": execution_plan,
                }
            )

    return {
        "portfolio_id": str(portfolio_id),
        "targets": plan["targets"],
        "cash_target_pct": plan["cash_target_pct"],
        "results": results,
    }
