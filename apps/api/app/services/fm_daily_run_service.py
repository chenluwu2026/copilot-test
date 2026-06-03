"""基金经理一日编排：数据就绪检查 + 候选池 + 决策流水线。"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Portfolio, Watchlist, WatchlistItem, WatchlistTier
from app.services.data_quality_service import get_data_quality
from app.services.decision_pipeline_service import run_decision_pipeline
from app.services.portfolio_service import get_portfolio_summary

_TIER_SCORE = {
    WatchlistTier.core: 1.0,
    WatchlistTier.track: 0.75,
    WatchlistTier.idea: 0.45,
}


def _build_candidates(db: Session, portfolio_id: UUID, *, limit: int = 20) -> list[dict]:
    scores: dict[str, float] = {}
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        return []
    watchlists = db.scalars(
        select(Watchlist)
        .where(Watchlist.user_id == portfolio.user_id)
        .options(joinedload(Watchlist.items))
    ).unique().all()
    for wl in watchlists:
        for item in wl.items:
            sid = str(item.security_id)
            tier_score = _TIER_SCORE.get(item.tier, 0.5)
            scores[sid] = max(scores.get(sid, 0), tier_score)

    summary = get_portfolio_summary(db, portfolio_id)
    for pos in summary.get("positions", []):
        sid = pos.get("security_id")
        if not sid:
            continue
        scores[sid] = max(scores.get(sid, 0), 0.55)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"security_id": UUID(sid), "score": score} for sid, score in ranked]


def run_fm_daily(
    db: Session,
    *,
    portfolio_id: UUID,
    max_turnover_pct: float = 30,
    auto_approve: bool = False,
    auto_execute_simulated: bool = False,
    simulated_fill_ratio: float = 0.7,
    auto_retry_resize: bool = True,
    max_retry_steps: int = 3,
    retry_decay_factor: float = 0.75,
    auto_apply_fallback_partial: bool = True,
    candidate_limit: int = 20,
) -> dict:
    run_id = f"fm-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"

    quality = get_data_quality(db)
    qsum = quality.get("summary", {})
    stale = int(qsum.get("stale_quotes", 0)) + int(qsum.get("missing_quotes", 0))
    coverage = float(qsum.get("coverage_pct", 0))

    candidates = _build_candidates(db, portfolio_id, limit=candidate_limit)
    if not candidates:
        return {
            "run_id": run_id,
            "portfolio_id": str(portfolio_id),
            "summary_md": "## 基金经理一日运行\n\n- 状态：未执行（候选池为空）\n- 请先在股票池添加标的或建立持仓。",
            "data_readiness": {
                "coverage_pct": coverage,
                "stale_or_missing_symbols": stale,
                "ready": stale == 0 and coverage >= 50,
            },
            "candidate_count": 0,
            "pipeline": None,
            "counts": {"created_decisions": 0, "rejected": 0, "fallback_applied": 0},
        }

    pipeline = run_decision_pipeline(
        db,
        portfolio_id=portfolio_id,
        candidates=candidates,
        max_turnover_pct=max_turnover_pct,
        auto_approve=auto_approve,
        auto_execute_simulated=auto_execute_simulated,
        simulated_fill_ratio=simulated_fill_ratio,
        auto_retry_resize=auto_retry_resize,
        max_retry_steps=max_retry_steps,
        retry_decay_factor=retry_decay_factor,
        auto_apply_fallback_partial=auto_apply_fallback_partial,
        run_id=run_id,
    )

    results = pipeline.get("results", [])
    created = [r for r in results if r.get("decision_id")]
    rejected = [r for r in results if not r.get("decision_id")]
    fallback = [r for r in results if (r.get("fallback") or {}).get("applied")]

    summary_md = (
        f"## 基金经理一日运行 `{run_id}`\n\n"
        f"- 数据覆盖：{coverage:.1f}%（陈旧/缺失 {stale} 个）\n"
        f"- 候选标的：{len(candidates)} 个\n"
        f"- 建单：{len(created)} · 未通过：{len(rejected)} · fallback：{len(fallback)}\n"
        f"- 自动审批：{'是' if auto_approve else '否'} · 模拟执行：{'是' if auto_execute_simulated else '否'}\n"
    )

    return {
        "run_id": run_id,
        "portfolio_id": str(portfolio_id),
        "summary_md": summary_md,
        "data_readiness": {
            "coverage_pct": coverage,
            "stale_or_missing_symbols": stale,
            "ready": stale == 0 and coverage >= 50,
        },
        "candidate_count": len(candidates),
        "pipeline": pipeline,
        "counts": {
            "created_decisions": len(created),
            "rejected": len(rejected),
            "fallback_applied": len(fallback),
        },
    }
