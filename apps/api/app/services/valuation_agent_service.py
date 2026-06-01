"""Valuation Agent：为研究观点补充/更新三情景估值。"""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchView, Security
from app.services.llm.client import complete_json, use_llm_agents
from app.services.llm.prompts import VALUATION_SYSTEM

logger = logging.getLogger(__name__)


def _rule_scenarios(security: Security, view: ResearchView) -> dict:
    price = float(security.last_price or 100)
    existing = view.scenario_analysis or {}
    if existing.get("scenarios"):
        return existing
    return {
        "methods": ["PE_percentile", "historical_band"],
        "scenarios": [
            {
                "name": "optimistic",
                "probability_weight": 0.25,
                "target_price_low": round(price * 1.12, 2),
                "target_price_high": round(price * 1.28, 2),
                "triggers": ["盈利超预期", "估值修复"],
            },
            {
                "name": "base",
                "probability_weight": 0.5,
                "target_price_low": round(price * 0.95, 2),
                "target_price_high": round(price * 1.08, 2),
                "triggers": ["业绩符合预期"],
            },
            {
                "name": "pessimistic",
                "probability_weight": 0.25,
                "target_price_low": round(price * 0.72, 2),
                "target_price_high": round(price * 0.92, 2),
                "triggers": ["业绩不及预期", "行业逆风"],
            },
        ],
        "current_price": price,
        "currency": security.currency or "CNY",
        "agent": "valuation_agent_rule",
    }


def _llm_scenarios(security: Security, view: ResearchView) -> dict | None:
    if not use_llm_agents():
        return None
    price = float(security.last_price or 100)
    user = (
        f"标的 {security.symbol} {security.name}，现价 {price}。\n"
        f"研究结论：{(view.investment_conclusion or '')[:400]}\n"
        f"评级：{view.rating.value}"
    )
    try:
        raw = complete_json(VALUATION_SYSTEM, user)
        scenario = raw.get("scenario_analysis") or raw
        if scenario and "current_price" not in scenario:
            scenario["current_price"] = price
        scenario["agent"] = "valuation_agent_llm"
        return scenario
    except Exception as e:
        logger.warning("valuation LLM failed for %s: %s", security.symbol, e)
        return None


def update_valuation_for_security(db: Session, security_id: UUID) -> bool:
    sec = db.get(Security, security_id)
    if not sec:
        return False
    view = db.scalar(
        select(ResearchView)
        .where(ResearchView.security_id == security_id)
        .order_by(ResearchView.version.desc())
        .limit(1)
    )
    if not view:
        return False
    scenarios = _llm_scenarios(sec, view) or _rule_scenarios(sec, view)
    view.scenario_analysis = scenarios
    if not view.valuation_snapshot:
        view.valuation_snapshot = {"source": scenarios.get("agent", "valuation_agent")}
    db.commit()
    return True


def run_valuation_agent(db: Session, security_ids: list[UUID]) -> dict:
    updated: list[str] = []
    for sid in security_ids:
        sec = db.get(Security, sid)
        if not sec:
            continue
        if update_valuation_for_security(db, sid):
            updated.append(sec.symbol)
    return {"updated_symbols": updated, "count": len(updated)}
