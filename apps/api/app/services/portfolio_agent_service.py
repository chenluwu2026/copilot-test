"""Portfolio Agent：根据研究评级与因子合成目标权重草案（规则或 LLM）。"""
import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchRating, ResearchView, Security, Watchlist, WatchlistItem
from app.services.decision_dossier_service import build_dossier
from app.services.factor_service import compute_factors
from app.services.llm.client import complete_json, use_llm_agents
from app.services.llm.prompts import PORTFOLIO_SYSTEM
from app.services.memory_service import search_memory_context
from app.services.profile_service import user_is_forbidden

logger = logging.getLogger(__name__)

RATING_TARGET_WEIGHT = {
    ResearchRating.strong_buy: 8.0,
    ResearchRating.buy: 6.0,
    ResearchRating.hold: 4.0,
    ResearchRating.neutral: 3.0,
    ResearchRating.reduce: 1.5,
    ResearchRating.sell: 0.0,
}


def _dossier_for_portfolio(dossier: dict) -> dict:
    r = dossier.get("research") or {}
    v = dossier.get("valuation") or {}
    fac = (dossier.get("factors") or {}).get("factors", {})
    return {
        "symbol": dossier.get("symbol"),
        "name": dossier.get("name"),
        "rating": r.get("rating"),
        "conclusion": (r.get("investment_conclusion") or "")[:200],
        "scenarios": (v.get("scenario_analysis") or {}).get("scenarios", [])[:2],
        "composite_factor": fac.get("composite"),
        "forbidden": (dossier.get("gates") or {}).get("forbidden"),
    }


def propose_weights_llm(
    db: Session,
    portfolio_id: UUID,
    universe: set[UUID],
    profile: dict,
    current_map: dict[str, float],
) -> dict | None:
    if not use_llm_agents():
        return None
    summaries = []
    for sid in universe:
        sec = db.get(Security, sid)
        if not sec:
            continue
        try:
            d = build_dossier(
                db,
                portfolio_id,
                sid,
                profile,
                current_weight_pct=float(current_map.get(sec.symbol, 0)),
            )
            summaries.append(_dossier_for_portfolio(d))
        except Exception:
            continue
    if not summaries:
        return None
    ctx = {
        "investment_profile": profile,
        "dossiers": summaries,
        "current_weights": current_map,
    }
    try:
        raw = complete_json(PORTFOLIO_SYSTEM, json.dumps(ctx, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.warning("portfolio LLM failed: %s", e)
        return None

    proposed = []
    sym_map = {db.get(Security, sid).symbol: sid for sid in universe if db.get(Security, sid)}
    for pw in raw.get("proposed_weights") or []:
        sym = pw.get("symbol")
        sid = sym_map.get(sym)
        if not sid:
            continue
        sec = db.get(Security, sid)
        proposed.append(
            {
                "security_id": str(sid),
                "symbol": sym,
                "name": pw.get("name") or sec.name,
                "weight_pct": round(float(pw.get("weight_pct", 0)), 2),
                "rationale": pw.get("rationale", "LLM 组合草案"),
            }
        )
    if not proposed:
        return None
    total = sum(p["weight_pct"] for p in proposed)
    max_gross = 90.0
    if total > max_gross:
        scale = max_gross / total
        for p in proposed:
            p["weight_pct"] = round(p["weight_pct"] * scale, 2)
    return {
        "proposed_weights": proposed,
        "gross_exposure_pct": sum(p["weight_pct"] for p in proposed),
        "mode": "llm",
    }


def propose_weights(
    db: Session,
    portfolio_id: UUID,
    user_id: UUID,
    factor_scores: list[dict],
    profile: dict | None = None,
    *,
    current_map: dict[str, float] | None = None,
) -> dict:
    """对股票池+持仓标的生成 proposed_weights。"""
    from app.models import Position

    positions = db.scalars(
        select(Position).where(Position.portfolio_id == portfolio_id)
    ).all()
    position_ids = {p.security_id for p in positions}

    watchlist_ids = set()
    for wl in db.scalars(select(Watchlist).where(Watchlist.user_id == user_id)):
        for item in db.scalars(
            select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
        ):
            watchlist_ids.add(item.security_id)

    universe = position_ids | watchlist_ids
    factor_map = {f["security_id"]: f for f in factor_scores}
    profile = profile or {}
    current_map = current_map or {}

    if use_llm_agents():
        llm_out = propose_weights_llm(db, portfolio_id, universe, profile, current_map)
        if llm_out:
            llm_out["memories_applied"] = []
            return llm_out

    symbol_list: list[str] = []
    sector_list: list[str] = []
    for sid in universe:
        sec = db.get(Security, sid)
        if sec:
            symbol_list.append(sec.symbol)
            if sec.sector:
                sector_list.append(sec.sector)

    memories = search_memory_context(
        db,
        symbols=symbol_list,
        sectors=sector_list,
        keywords=["教训", "anti_pattern"],
        limit=5,
    )
    anti_patterns = [m.content for m in memories if m.memory_type.value == "anti_pattern"]

    proposed = []
    for sid in universe:
        sec = db.get(Security, sid)
        if not sec:
            continue
        if user_is_forbidden(profile, symbol=sec.symbol, sector=sec.sector):
            proposed.append(
                {
                    "security_id": str(sid),
                    "symbol": sec.symbol,
                    "name": sec.name,
                    "weight_pct": 0.0,
                    "rationale": "投资画像禁止项",
                }
            )
            continue
        view = db.scalar(
            select(ResearchView)
            .where(ResearchView.security_id == sid)
            .order_by(ResearchView.version.desc())
            .limit(1)
        )
        base = RATING_TARGET_WEIGHT.get(view.rating, 3.0) if view else 2.0
        fac = factor_map.get(str(sid), {}).get("factors", {})
        composite = fac.get("composite", 50)
        adj = (composite - 50) / 50 * 2
        weight = max(0, min(10, base + adj))

        for ap in anti_patterns:
            if "低估值不能单独" in ap and sec.sector == "传媒" and weight > 5:
                weight = min(weight, 5.0)
            if "政策反转" in ap and view and "监管" in (view.investment_conclusion or ""):
                weight = min(weight, 2.0)

        proposed.append(
            {
                "security_id": str(sid),
                "symbol": sec.symbol,
                "name": sec.name,
                "weight_pct": round(weight, 2),
                "rationale": (
                    f"研究评级 {view.rating.value if view else 'n/a'}，"
                    f"因子综合 {composite:.0f}"
                ),
            }
        )

    total = sum(p["weight_pct"] for p in proposed)
    max_gross = 90.0
    if total > max_gross:
        scale = max_gross / total
        for p in proposed:
            p["weight_pct"] = round(p["weight_pct"] * scale, 2)

    return {
        "proposed_weights": proposed,
        "gross_exposure_pct": sum(p["weight_pct"] for p in proposed),
        "memories_applied": [m.title for m in memories],
        "mode": "rule",
    }
