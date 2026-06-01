"""决策证据卷宗：为 CIO / Portfolio LLM 组装每标的上下文。"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FinancialReport, Position, ResearchView, Security, StrategyRule
from app.services.event_service import list_events
from app.services.factor_service import compute_factors
from app.services.memory_service import search_memory_context
from app.services.profile_service import user_is_forbidden
from app.services.research_gate_service import research_allows_trade


def _research_age_days(view: ResearchView | None) -> int | None:
    if not view or not view.created_at:
        return None
    created = view.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).days


def _financials_summary(db: Session, security_id: UUID, limit: int = 2) -> list[dict]:
    rows = db.scalars(
        select(FinancialReport)
        .where(FinancialReport.security_id == security_id)
        .order_by(FinancialReport.period_key.desc())
        .limit(limit)
    ).all()
    return [
        {
            "period_key": r.period_key,
            "report_type": r.report_type,
            "metrics": r.metrics,
        }
        for r in rows
    ]


def build_dossier(
    db: Session,
    portfolio_id: UUID,
    security_id: UUID,
    profile: dict,
    *,
    current_weight_pct: float = 0.0,
    risk_violations: list | None = None,
    factor_row: dict | None = None,
) -> dict:
    sec = db.get(Security, security_id)
    if not sec:
        raise ValueError("标的不存在")

    pos = db.scalar(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.security_id == security_id,
        )
    )
    view = db.scalar(
        select(ResearchView)
        .where(ResearchView.security_id == security_id)
        .order_by(ResearchView.version.desc())
        .limit(1)
    )

    max_age = int(profile.get("research_max_age_days", 30))
    research_ok, research_reason = research_allows_trade(db, security_id, max_age_days=max_age)
    forbidden = user_is_forbidden(profile, symbol=sec.symbol, sector=sec.sector)

    if factor_row is None:
        factors = compute_factors(db, [security_id])
        factor_row = factors[0] if factors else None

    events = list_events(db, security_id=security_id, limit=5)
    memories = search_memory_context(
        db,
        symbols=[sec.symbol],
        sectors=[sec.sector] if sec.sector else [],
        keywords=["教训", "复盘"],
        limit=3,
    )

    fa = {}
    if view:
        fa = view.content_structured.get("fundamental_analysis", {})

    return {
        "security_id": str(security_id),
        "symbol": sec.symbol,
        "name": sec.name,
        "sector": sec.sector,
        "last_price": float(sec.last_price) if sec.last_price else None,
        "position": {
            "weight_pct": current_weight_pct,
            "quantity": float(pos.quantity) if pos else 0,
            "avg_cost": float(pos.avg_cost) if pos and pos.avg_cost else None,
            "market_value": float(pos.market_value) if pos else 0,
        },
        "research": {
            "view_id": str(view.id) if view else None,
            "version": view.version if view else None,
            "rating": view.rating.value if view else None,
            "age_days": _research_age_days(view),
            "investment_conclusion": (view.investment_conclusion[:500] if view else None),
            "fundamental_analysis": fa,
            "agent_name": view.agent_name if view else None,
        },
        "valuation": {
            "scenario_analysis": view.scenario_analysis if view else {},
            "valuation_snapshot": view.valuation_snapshot if view else {},
        },
        "factors": factor_row,
        "events": [
            {
                "id": e["id"],
                "event_type": e.get("event_type"),
                "impact_direction": e.get("impact_direction"),
                "summary": (e.get("summary") or "")[:200],
                "published_at": e.get("published_at"),
            }
            for e in events[:5]
        ],
        "financials": _financials_summary(db, security_id),
        "memories": [{"title": m.title, "content": m.content[:150]} for m in memories],
        "gates": {
            "research_allowed": research_ok,
            "research_gate_reason": research_reason if not research_ok else None,
            "forbidden": forbidden,
            "risk_violations": [
                v for v in (risk_violations or []) if v.get("symbol") == sec.symbol
            ],
        },
    }


def build_dossiers_for_universe(
    db: Session,
    portfolio_id: UUID,
    security_ids: list[UUID],
    profile: dict,
    current_map: dict[str, float],
    risk_result: dict,
) -> dict[str, dict]:
    violations = risk_result.get("violations") or []
    factors = {f["security_id"]: f for f in compute_factors(db, security_ids)}
    dossiers: dict[str, dict] = {}
    for sid in security_ids:
        sec = db.get(Security, sid)
        if not sec:
            continue
        dossiers[sec.symbol] = build_dossier(
            db,
            portfolio_id,
            sid,
            profile,
            current_weight_pct=float(current_map.get(sec.symbol, 0)),
            risk_violations=violations,
            factor_row=factors.get(str(sid)),
        )
    return dossiers


def dossier_summary_for_trace(dossier: dict) -> dict:
    """压缩版写入 agent trace。"""
    r = dossier.get("research") or {}
    return {
        "symbol": dossier.get("symbol"),
        "rating": r.get("rating"),
        "research_age_days": r.get("age_days"),
        "gates": dossier.get("gates"),
        "events_count": len(dossier.get("events") or []),
    }


def build_references_from_dossier(dossier: dict) -> list[dict]:
    refs: list[dict] = []
    research = dossier.get("research") or {}
    if research.get("view_id"):
        refs.append(
            {
                "ref_type": "research_report",
                "ref_id": research["view_id"],
                "excerpt": (research.get("investment_conclusion") or "")[:300],
            }
        )
    val = dossier.get("valuation") or {}
    scenarios = (val.get("scenario_analysis") or {}).get("scenarios") or []
    if scenarios:
        s0 = scenarios[0]
        refs.append(
            {
                "ref_type": "valuation",
                "ref_id": research.get("view_id"),
                "excerpt": f"{s0.get('name')}: {s0.get('target_price_low')}-{s0.get('target_price_high')}",
            }
        )
    for ev in (dossier.get("events") or [])[:2]:
        refs.append(
            {
                "ref_type": "filing" if ev.get("event_type") == "filing" else "news",
                "ref_id": ev.get("id"),
                "excerpt": ev.get("summary"),
            }
        )
    fac = dossier.get("factors")
    if fac:
        refs.append(
            {
                "ref_type": "factor",
                "ref_id": dossier.get("security_id"),
                "excerpt": f"综合因子 {fac.get('factors', {}).get('composite', 'n/a')}",
            }
        )
    return refs


def load_strategy_rules_text(db: Session) -> list[dict]:
    rows = db.scalars(select(StrategyRule).where(StrategyRule.active.is_(True))).all()
    return [
        {
            "rule_code": r.rule_code,
            "natural_language": r.natural_language,
            "machine_check": r.machine_check,
        }
        for r in rows
    ]
