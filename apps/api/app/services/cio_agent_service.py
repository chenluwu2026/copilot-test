"""CIO Agent：规则引擎或 LLM（证据卷宗驱动）生成决策草稿。"""
import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DecisionAction, ResearchRating, ResearchView, Security
from app.services import decision_service as ds
from app.services.decision_dossier_service import build_references_from_dossier
from app.services.decision_quality_service import score_decision_draft
from app.services.llm.client import complete_json, use_llm_agents
from app.services.llm.prompts import CIO_SYMBOL_SYSTEM, CIO_SYSTEM
from app.services.profile_service import user_is_forbidden
from app.services.research_gate_service import gate_action_for_research

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
    profile: dict | None = None,
    dossiers_by_symbol: dict[str, dict] | None = None,
    strategy_rules: list[dict] | None = None,
) -> tuple[list[str], list[dict], str]:
    profile = profile or {}
    if use_llm_agents():
        try:
            return _generate_llm(
                db,
                portfolio_id,
                proposed,
                current_map,
                risk_result,
                memories,
                trace,
                profile,
                dossiers_by_symbol or {},
                strategy_rules or [],
            )
        except Exception as e:
            logger.warning("CIO LLM failed, fallback to rule: %s", e)
            trace["cio_fallback"] = str(e)
    return _generate_rule(
        db,
        portfolio_id,
        proposed,
        current_map,
        risk_result,
        memories,
        profile,
        dossiers_by_symbol or {},
    )


def _candidates_from_proposed(
    proposed: list[dict],
    current_map: dict[str, float],
    max_symbols: int,
) -> list[dict]:
    cands = []
    for pw in proposed:
        symbol = pw["symbol"]
        current = float(current_map.get(symbol, 0))
        target = float(pw["weight_pct"])
        delta = target - current
        if abs(delta) >= 1.0:
            cands.append({**pw, "delta_weight_pct": delta, "current_weight_pct": current})
    cands.sort(key=lambda x: abs(x["delta_weight_pct"]), reverse=True)
    return cands[:max_symbols]


def _apply_gates(
    db: Session,
    sec: Security,
    action: DecisionAction,
    target: float,
    current: float,
    profile: dict,
    item: dict,
) -> tuple[DecisionAction, float, dict]:
    if user_is_forbidden(profile, symbol=sec.symbol, sector=sec.sector):
        action = DecisionAction.watch
        target = current
    gated_action, gate_reason = gate_action_for_research(db, sec.id, action, profile)
    if gated_action != action:
        action = gated_action
        target = current
        item = dict(item)
        item["decision_reason"] = (
            item.get("decision_reason", "") + f" [研究闸门] {gate_reason}"
        )
    return action, target, item


def _persist_decision(
    db,
    portfolio_id,
    sec,
    item: dict,
    dossier: dict | None,
    view,
    profile: dict,
) -> tuple[str, dict]:
    action = DecisionAction(item["action"])
    current = float(item.get("current_weight_pct", 0))
    target = float(item["target_weight_pct"])
    action, target, item = _apply_gates(db, sec, action, target, current, profile, item)

    refs = build_references_from_dossier(dossier) if dossier else []
    if view and not refs:
        refs = [
            {
                "ref_type": "research_report",
                "ref_id": str(view.id),
                "excerpt": view.investment_conclusion[:200],
            }
        ]

    quality = score_decision_draft(dossier, item)
    cio_summary = {**item, "decision_by": "cio_agent"}
    decision = ds.create_decision(
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
        refs,
        item.get("confidence_grade", "B"),
        item.get("holding_period", "6-12个月"),
        cio_summary=cio_summary,
        created_by_agent="cio_agent",
        evidence_meta={
            "evidence_grade": quality["grade"],
            "evidence_score": quality["score"],
            "evidence_issues": quality["issues"],
        },
    )
    return str(decision.id), {
        "decision_id": str(decision.id),
        "symbol": sec.symbol,
        "action": action.value,
        "mode": "llm",
        "evidence_grade": quality["grade"],
    }


def _generate_llm(
    db: Session,
    portfolio_id: UUID,
    proposed: list[dict],
    current_map: dict[str, float],
    risk_result: dict,
    memories: list,
    trace: dict,
    profile: dict,
    dossiers_by_symbol: dict[str, dict],
    strategy_rules: list[dict],
) -> tuple[list[str], list[dict], str]:
    cands = _candidates_from_proposed(
        proposed, current_map, settings.cio_max_symbols
    )
    if not cands:
        raise RuntimeError("无满足 |delta|>=1 的调仓候选")

    mode = (settings.cio_decision_mode or "batch").lower()
    decision_ids: list[str] = []
    cio_outputs: list[dict] = []

    base_ctx = {
        "proposed_weights": proposed,
        "current_weights": current_map,
        "risk": risk_result,
        "investment_profile": profile,
        "strategy_rules": strategy_rules,
        "memories": [{"title": m.title, "content": m.content[:200]} for m in memories],
    }

    if mode == "per_symbol":
        for pw in cands:
            symbol = pw["symbol"]
            dossier = dossiers_by_symbol.get(symbol)
            if not dossier:
                continue
            user = json.dumps(
                {
                    **base_ctx,
                    "dossier": dossier,
                    "portfolio_proposal": pw,
                },
                ensure_ascii=False,
                indent=2,
            )
            raw = _llm_json_with_retry(CIO_SYMBOL_SYSTEM, user, trace)
            item = raw if raw.get("security") else raw
            try:
                ds.validate_decision_payload(item)
            except Exception as e:
                logger.warning("skip invalid per_symbol %s: %s", symbol, e)
                continue
            sec = db.scalar(select(Security).where(Security.symbol == symbol))
            if not sec:
                continue
            view = None
            vid = (dossier.get("research") or {}).get("view_id")
            if vid:
                view = db.get(ResearchView, UUID(vid))
            did, out = _persist_decision(db, portfolio_id, sec, item, dossier, view, profile)
            decision_ids.append(did)
            cio_outputs.append(out)
    else:
        dossier_list = [
            dossiers_by_symbol[pw["symbol"]]
            for pw in cands
            if pw["symbol"] in dossiers_by_symbol
        ]
        user = json.dumps(
            {**base_ctx, "dossiers": dossier_list, "candidates": cands},
            ensure_ascii=False,
            indent=2,
        )
        raw = _llm_json_with_retry(CIO_SYSTEM, user, trace)
        trace["cio_llm_raw_keys"] = list(raw.keys())
        for item in (raw.get("decisions") or [])[: settings.cio_max_symbols]:
            symbol = item.get("security", {}).get("symbol")
            if not symbol:
                continue
            sec = db.scalar(select(Security).where(Security.symbol == symbol))
            if not sec:
                continue
            try:
                ds.validate_decision_payload(item)
            except Exception as e:
                logger.warning("skip invalid batch %s: %s", symbol, e)
                continue
            dossier = dossiers_by_symbol.get(symbol)
            view = None
            if dossier and (dossier.get("research") or {}).get("view_id"):
                view = db.get(ResearchView, UUID(dossier["research"]["view_id"]))
            did, out = _persist_decision(db, portfolio_id, sec, item, dossier, view, profile)
            decision_ids.append(did)
            cio_outputs.append(out)

    if not decision_ids:
        raise RuntimeError("LLM 未产出有效决策")
    trace["cio_decision_mode"] = mode
    return decision_ids, cio_outputs, "llm"


def _llm_json_with_retry(system: str, user: str, trace: dict) -> dict:
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            return complete_json(system, user)
        except Exception as e:
            last_err = e
            trace.setdefault("cio_llm_retries", []).append(str(e))
    raise RuntimeError(f"LLM JSON failed after retries: {last_err}")


def _generate_rule(
    db: Session,
    portfolio_id: UUID,
    proposed: list[dict],
    current_map: dict[str, float],
    risk_result: dict,
    memories: list,
    profile: dict,
    dossiers_by_symbol: dict[str, dict],
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

        if not risk_result.get("approved", True) and action in (
            DecisionAction.buy,
            DecisionAction.add,
        ):
            action = DecisionAction.watch
            target = current

        dossier = dossiers_by_symbol.get(symbol)
        reason = (
            f"[CIO 规则引擎] {pw.get('rationale', '')}。"
            f"目标权重 {target:.1f}%（当前 {current:.1f}%）。"
        )
        if dossier:
            r = dossier.get("research") or {}
            if r.get("investment_conclusion"):
                reason += f" 研究：{r['investment_conclusion'][:120]}。"
            evs = dossier.get("events") or []
            if evs:
                reason += f" 近期事件：{evs[0].get('summary', '')[:80]}。"
        if memories:
            reason += f" 参考记忆：{memories[0].title}。"

        gated_action, gate_reason = gate_action_for_research(db, sec.id, action, profile)
        if gated_action != action:
            action = gated_action
            target = current
            reason += f" [研究闸门] {gate_reason}。"

        core_vars = []
        if view:
            fa = view.content_structured.get("fundamental_analysis", {})
            cv = fa.get("core_variables_6_12m", [])
            core_vars = cv if isinstance(cv, list) else [str(cv)]
        assumptions = [
            {"text": core_vars[0] if core_vars else "价格与基本面一致", "measurable": True}
        ]
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

        item = {
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
        }
        quality = score_decision_draft(dossier, item)
        cio_summary = {**item, "decision_by": "cio_agent"}
        refs = build_references_from_dossier(dossier) if dossier else []
        decision = ds.create_decision(
            db,
            portfolio_id,
            sec.id,
            action,
            reason,
            current,
            target,
            main_risks,
            review_conds,
            assumptions,
            refs,
            item.get("confidence_grade", "B"),
            item.get("holding_period", "6-12个月"),
            cio_summary=cio_summary,
            created_by_agent="cio_agent",
            evidence_meta={
                "evidence_grade": quality["grade"],
                "evidence_score": quality["score"],
                "evidence_issues": quality["issues"],
            },
        )
        decision_ids.append(str(decision.id))
        cio_outputs.append(
            {
                "decision_id": str(decision.id),
                "symbol": symbol,
                "action": action.value,
                "mode": "rule",
                "evidence_grade": quality["grade"],
            }
        )
    return decision_ids, cio_outputs, "rule"
