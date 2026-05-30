"""CIO Agent：规则引擎或 LLM 生成决策草稿。"""
import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DecisionAction, ResearchRating, ResearchView, Security
from app.services import decision_service as ds
from app.services.llm.client import complete_json, use_llm_agents
from app.services.llm.prompts import CIO_SYSTEM

logger = logging.getLogger(__name__)

RATING_TO_ACTION = {
    ResearchRating.strong_buy: DecisionAction.add,
    ResearchRating.buy: DecisionAction.add,
    ResearchRating.hold: DecisionAction.hold,
    ResearchRating.neutral: DecisionAction.watch,
    ResearchRating.reduce: DecisionAction.reduce,
    ResearchRating.sell: DecisionAction.sell,
}


def generate_cio_decisions(
    db: Session,
    portfolio_id: UUID,
    proposed: list[dict],
    current_map: dict[str, float],
    risk_result: dict,
    memories: list,
    trace: dict,
) -> tuple[list[str], list[dict], str]:
    """
    返回 (decision_ids, cio_outputs, mode_used)。
    """
    if use_llm_agents():
        try:
            return _generate_llm(db, portfolio_id, proposed, current_map, risk_result, memories, trace)
        except Exception as e:
            logger.warning("CIO LLM failed, fallback to rule: %s", e)
            trace["cio_fallback"] = str(e)
    return _generate_rule(db, portfolio_id, proposed, current_map, risk_result, memories)


def _generate_rule(
    db: Session,
    portfolio_id: UUID,
    proposed: list[dict],
    current_map: dict[str, float],
    risk_result: dict,
    memories: list,
) -> tuple[list[str], list[dict], str]:
    decision_ids = []
    cio_outputs = []
    for pw in proposed:
        symbol = pw["symbol"]
        target = float(pw["weight_pct"])
        current = float(current_map.get(symbol, 0))
        delta = target - current
        if abs(delta) < 1.0:
            continue

        sec = db.scalar(select(Security).where(Security.symbol == symbol))
        if not sec:
            continue
        view = db.scalar(
            select(ResearchView)
            .where(ResearchView.security_id == sec.id)
            .order_by(ResearchView.version.desc())
            .limit(1)
        )
        rating = view.rating if view else ResearchRating.hold
        if delta > 0:
            action = DecisionAction.add if current > 0 else DecisionAction.buy
        elif target <= 0.5:
            action = DecisionAction.sell if current > 1 else DecisionAction.watch
        else:
            action = DecisionAction.reduce

        if not risk_result.get("approved", True) and action in (DecisionAction.buy, DecisionAction.add):
            action = DecisionAction.watch
            target = current

        reason = (
            f"[CIO 规则引擎] {pw.get('rationale', '')}。"
            f"目标权重 {target:.1f}%（当前 {current:.1f}%）。"
        )
        if memories:
            reason += f" 参考记忆：{memories[0].title}。"

        core_vars = []
        if view:
            fa = view.content_structured.get("fundamental_analysis", {})
            cv = fa.get("core_variables_6_12m", [])
            core_vars = cv if isinstance(cv, list) else [str(cv)]
        assumptions = [{"text": core_vars[0] if core_vars else "价格与基本面一致", "measurable": True}]
        review_conds = [
            "核心假设被证伪时复盘，非单纯价格止损",
            "权重偏离目标超过 3% 且基本面无变化时检视",
        ]
        risks = (
            view.content_structured.get("fundamental_analysis", {}).get("key_risks", "")
            if view
            else "市场波动"
        )
        main_risks = [risks] if isinstance(risks, str) else list(risks)[:2] or ["市场波动"]

        cio_summary = {
            "security": {"symbol": symbol, "name": sec.name},
            "action": action.value,
            "research_rating": rating.value,
            "current_weight_pct": current,
            "target_weight_pct": target,
            "delta_weight_pct": delta,
            "decision_reason": reason,
            "assumptions": assumptions,
            "main_risks": main_risks,
            "review_conditions": review_conds,
            "confidence_grade": "B" if abs(delta) < 3 else "B+",
            "holding_period": view.horizon if view else "3-6个月",
            "decision_by": "cio_agent",
        }
        decision = _create_from_summary(
            db, portfolio_id, sec.id, action, reason, current, target, main_risks, review_conds, assumptions, view, cio_summary
        )
        decision_ids.append(str(decision.id))
        cio_outputs.append(
            {
                "decision_id": str(decision.id),
                "symbol": symbol,
                "action": action.value,
                "mode": "rule",
            }
        )
    return decision_ids, cio_outputs, "rule"


def _generate_llm(
    db: Session,
    portfolio_id: UUID,
    proposed: list[dict],
    current_map: dict[str, float],
    risk_result: dict,
    memories: list,
    trace: dict,
) -> tuple[list[str], list[dict], str]:
    context = {
        "proposed_weights": proposed,
        "current_weights": current_map,
        "risk": risk_result,
        "memories": [{"title": m.title, "content": m.content[:200]} for m in memories],
    }
    user = json.dumps(context, ensure_ascii=False, indent=2)
    raw = complete_json(CIO_SYSTEM, user)
    trace["cio_llm_raw_keys"] = list(raw.keys())
    items = raw.get("decisions") or []
    decision_ids = []
    cio_outputs = []

    for item in items:
        symbol = item.get("security", {}).get("symbol")
        if not symbol:
            continue
        sec = db.scalar(select(Security).where(Security.symbol == symbol))
        if not sec:
            continue
        try:
            ds.validate_decision_payload(item)
        except Exception as e:
            logger.warning("skip invalid LLM decision %s: %s", symbol, e)
            continue
        action = DecisionAction(item["action"])
        current = float(item.get("current_weight_pct", current_map.get(symbol, 0)))
        target = float(item["target_weight_pct"])
        decision = _create_from_summary(
            db,
            portfolio_id,
            sec.id,
            action,
            item["decision_reason"],
            current,
            target,
            item["main_risks"],
            item["review_conditions"],
            item["assumptions"],
            None,
            {**item, "decision_by": "cio_agent"},
        )
        decision_ids.append(str(decision.id))
        cio_outputs.append({"decision_id": str(decision.id), "symbol": symbol, "action": action.value, "mode": "llm"})

    if not decision_ids:
        raise RuntimeError("LLM 未产出有效决策")
    return decision_ids, cio_outputs, "llm"


def _create_from_summary(
    db, portfolio_id, security_id, action, reason, current, target, main_risks, review_conds, assumptions, view, cio_summary
):
    refs = (
        [{"ref_type": "valuation", "excerpt": view.investment_conclusion[:200]}]
        if view
        else []
    )
    return ds.create_decision(
        db,
        portfolio_id,
        security_id,
        action,
        reason,
        current,
        target,
        main_risks,
        review_conds,
        assumptions,
        refs,
        cio_summary.get("confidence_grade", "B"),
        cio_summary.get("holding_period", "6-12个月"),
        cio_summary=cio_summary,
        created_by_agent="cio_agent",
    )
