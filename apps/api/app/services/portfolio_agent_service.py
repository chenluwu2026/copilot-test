"""Portfolio Agent：根据研究评级与因子合成目标权重草案。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchRating, ResearchView, Security, Watchlist, WatchlistItem
from app.services.factor_service import compute_factors
from app.services.memory_service import search_memory


RATING_TARGET_WEIGHT = {
    ResearchRating.strong_buy: 8.0,
    ResearchRating.buy: 6.0,
    ResearchRating.hold: 4.0,
    ResearchRating.neutral: 3.0,
    ResearchRating.reduce: 1.5,
    ResearchRating.sell: 0.0,
}


def propose_weights(
    db: Session,
    portfolio_id: UUID,
    user_id: UUID,
    factor_scores: list[dict],
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

    memories = search_memory(db, "教训", limit=5)
    anti_patterns = [m.content for m in memories if m.memory_type.value == "anti_pattern"]

    proposed = []
    for sid in universe:
        sec = db.get(Security, sid)
        if not sec:
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
            if "政策反转" in ap and "监管" in (view.investment_conclusion if view else ""):
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
    }
