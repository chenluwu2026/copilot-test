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


def _build_downgrade_advice(risk: dict, target_weight: float, current_weight: float) -> dict:
    failed = risk.get("failed_gates") or []
    checks = {c["gate_name"]: c for c in risk.get("checks", [])}
    severity = "high" if any(g in failed for g in ("cash_buffer_gate", "sector_limit_gate")) else "medium"
    advice = {"severity": severity, "failed_gates": failed, "suggested_action": "watch", "reason": "风控未通过"}

    if "position_limit_gate" in failed:
        threshold = float((checks.get("position_limit_gate") or {}).get("threshold") or target_weight)
        resized = max(0.0, min(threshold, target_weight))
        advice.update(
            {
                "suggested_action": "resize",
                "suggested_target_weight_pct": round(resized, 4),
                "reason": f"单票超限，建议从 {target_weight:.2f}% 降到 {resized:.2f}%",
            }
        )
        return advice

    if "liquidity_gate" in failed:
        advice.update(
            {
                "suggested_action": "resize",
                "suggested_target_weight_pct": round(max(current_weight, target_weight * 0.5), 4),
                "reason": "流动性不足，建议缩量并延长 TWAP 切片执行",
            }
        )
        return advice

    if "correlation_gate" in failed:
        advice.update({"suggested_action": "watch", "reason": "相关性超限，建议观察或替换为低相关标的"})
        return advice

    if "sector_limit_gate" in failed:
        advice.update({"suggested_action": "watch", "reason": "行业集中度超限，建议转向分散行业"})
        return advice

    if "cash_buffer_gate" in failed:
        advice.update({"suggested_action": "watch", "reason": "现金缓冲不足，建议先减仓腾挪现金"})
        return advice

    return advice


def run_decision_pipeline(
    db: Session,
    *,
    portfolio_id: UUID,
    candidates: list[dict],
    max_turnover_pct: float = 40,
    auto_approve: bool = False,
    auto_execute_simulated: bool = False,
    simulated_fill_ratio: float = 1.0,
    auto_retry_resize: bool = True,
    max_retry_steps: int = 3,
    retry_decay_factor: float = 0.75,
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

    def _build_execution_plan(current_weight: float, target_weight: float) -> tuple[dict, float, float, float]:
        delta_pct_local = abs(target_weight - current_weight)
        order_notional_local = float(nav * Decimal(str(delta_pct_local)) / Decimal("100"))
        qty_local = (order_notional_local / px) if px > 0 else 0.0
        execution_sim_local = ess.simulate_execution(
            side=_pick_action(current_weight, target_weight).value,
            quantity=qty_local,
            reference_price=px if px > 0 else 1.0,
            adv_notional=adv_notional if adv_notional > 0 else None,
            fill_ratio=1.0,
        )
        adv_ratio_pct_local = (order_notional_local / adv_notional * 100) if adv_notional > 0 else 0.0
        return (
            {
                "order_notional": order_notional_local,
                "estimated_quantity": qty_local,
                "estimated_slippage_bps": execution_sim_local["slippage_bps"],
                "estimated_shortfall": execution_sim_local["implementation_shortfall"],
                "adv_ratio_pct": adv_ratio_pct_local,
                "schedule": _execution_schedule(adv_ratio_pct_local),
            },
            order_notional_local,
            qty_local,
            adv_ratio_pct_local,
        )

    def _create_decision_with_optional_flow(
        *,
        security_id: str,
        symbol: str | None,
        current_weight: float,
        target_weight: float,
        action: DecisionAction,
        risk_result: dict,
        execution_plan_obj: dict,
        retry_note: str | None = None,
    ) -> dict:
        reason = f"自动组合构建建议：目标权重 {target_weight:.2f}%"
        if retry_note:
            reason = f"{reason}（{retry_note}）"
        decision = ds.create_decision(
            db,
            portfolio_id=portfolio_id,
            security_id=UUID(security_id),
            action=action,
            decision_reason=reason,
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
                quantity=execution_plan_obj["estimated_quantity"],
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
        return {
            "security_id": security_id,
            "symbol": symbol,
            "allowed": True,
            "risk": risk_result,
            "decision_id": str(decision.id),
            "action": action.value,
            "target_weight_pct": target_weight,
            "current_weight_pct": current_weight,
            "execution_plan": execution_plan_obj,
            "auto_approved": auto_approved,
            "simulated_execution": simulated_execution,
        }

    for item in plan["targets"]:
        target_weight = float(item["target_weight_pct"])
        current_weight = float(item["current_weight_pct"])
        sec = db.get(Security, UUID(item["security_id"]))
        px = float(sec.last_price or 0) if sec else 0.0
        adv_notional = float((sec.meta or {}).get("avg_daily_turnover") or 0) if sec else 0.0
        execution_plan, order_notional, _, _ = _build_execution_plan(current_weight, target_weight)

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
            results.append(
                _create_decision_with_optional_flow(
                    security_id=item["security_id"],
                    symbol=item["symbol"],
                    current_weight=current_weight,
                    target_weight=target_weight,
                    action=action,
                    risk_result=risk,
                    execution_plan_obj=execution_plan,
                )
            )
        else:
            downgrade_advice = _build_downgrade_advice(risk, target_weight, current_weight)
            retried = False
            retry_result = None
            if auto_retry_resize and downgrade_advice.get("suggested_action") == "resize":
                resized_target = float(downgrade_advice.get("suggested_target_weight_pct") or target_weight)
                retried = True
                attempts: list[dict] = []
                for idx in range(max(1, max_retry_steps)):
                    resized_plan, resized_order_notional, _, _ = _build_execution_plan(current_weight, resized_target)
                    retry_risk = prs.run_pretrade_checks(
                        db,
                        portfolio_id,
                        UUID(item["security_id"]),
                        target_weight_pct=resized_target,
                        order_notional=resized_order_notional,
                        corr_value=None,
                    )
                    cost_benefit = {
                        "shortfall_reduction": round(
                            execution_plan["estimated_shortfall"] - resized_plan["estimated_shortfall"], 6
                        ),
                        "slippage_bps_reduction": round(
                            execution_plan["estimated_slippage_bps"] - resized_plan["estimated_slippage_bps"], 6
                        ),
                        "notional_reduction_pct": round(
                            ((execution_plan["order_notional"] - resized_plan["order_notional"])
                             / execution_plan["order_notional"] * 100)
                            if execution_plan["order_notional"] > 0
                            else 0.0,
                            6,
                        ),
                    }
                    attempts.append(
                        {
                            "step": idx + 1,
                            "target_weight_pct": resized_target,
                            "risk": retry_risk,
                            "cost_benefit": cost_benefit,
                        }
                    )
                    if retry_risk["allowed"]:
                        action = _pick_action(current_weight, resized_target)
                        created = _create_decision_with_optional_flow(
                            security_id=item["security_id"],
                            symbol=item["symbol"],
                            current_weight=current_weight,
                            target_weight=resized_target,
                            action=action,
                            risk_result=retry_risk,
                            execution_plan_obj=resized_plan,
                            retry_note=f"resize 第{idx+1}次风控通过",
                        )
                        created["retry"] = {
                            "attempted": True,
                            "from_target_weight_pct": target_weight,
                            "to_target_weight_pct": resized_target,
                            "passed": True,
                            "step": idx + 1,
                            "attempts": attempts,
                        }
                        results.append(created)
                        break

                    if idx == max(1, max_retry_steps) - 1:
                        retry_result = {
                            "passed": False,
                            "attempts": attempts,
                            "fallback_action": "partial" if attempts else "watch",
                        }
                        break
                    resized_target = max(current_weight, resized_target * retry_decay_factor)

                if retry_result is None and attempts and attempts[-1]["risk"]["allowed"]:
                    continue
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
                    "downgrade_advice": downgrade_advice,
                    "retry": {
                        "attempted": retried,
                        "from_target_weight_pct": target_weight,
                        "to_target_weight_pct": downgrade_advice.get("suggested_target_weight_pct"),
                        "passed": False if retried else None,
                        "result": retry_result,
                        "fallback_action": (retry_result or {}).get("fallback_action", "watch")
                        if retried
                        else "watch",
                    },
                }
            )

    return {
        "portfolio_id": str(portfolio_id),
        "targets": plan["targets"],
        "cash_target_pct": plan["cash_target_pct"],
        "results": results,
    }
