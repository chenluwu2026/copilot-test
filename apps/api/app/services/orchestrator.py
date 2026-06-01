"""CIO 调仓工作流编排（证据驱动）。"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AgentRun, AgentRunStatus, Position, Security, Watchlist, WatchlistItem
from app.services.cio_agent_service import generate_cio_decisions
from app.services.decision_dossier_service import (
    build_dossiers_for_universe,
    dossier_summary_for_trace,
    load_strategy_rules_text,
)
from app.services.factor_service import compute_factors
from app.services.memory_service import search_memory_context
from app.services.portfolio_agent_service import propose_weights
from app.services.portfolio_service import get_portfolio_summary
from app.services.profile_service import get_investment_profile
from app.services.research_refresh_service import refresh_stale_research
from app.services.risk_service import check_risk
from app.services.user_context import get_default_user
from app.services.valuation_agent_service import run_valuation_agent


def run_rebalance_workflow(db: Session, portfolio_id: UUID, trigger: str = "manual") -> AgentRun:
    run = AgentRun(
        portfolio_id=portfolio_id,
        workflow_name="rebalance_cio",
        trigger=trigger,
        status=AgentRunStatus.running,
        input_context={
            "portfolio_id": str(portfolio_id),
            "agent_mode": settings.agent_mode,
            "cio_decision_mode": settings.cio_decision_mode,
        },
    )
    db.add(run)
    db.flush()

    trace: dict = {"steps": [], "agent_mode": settings.agent_mode}
    try:
        user = get_default_user(db)
        profile = get_investment_profile(user)
        trace["investment_profile"] = profile
        strategy_rules = load_strategy_rules_text(db)
        trace["strategy_rules_count"] = len(strategy_rules)

        summary = get_portfolio_summary(db, portfolio_id)
        current_map = {p["symbol"]: p["weight_pct"] for p in summary["positions"]}

        positions = db.scalars(select(Position).where(Position.portfolio_id == portfolio_id)).all()
        universe_ids = [p.security_id for p in positions]
        for wl in db.scalars(select(Watchlist).where(Watchlist.user_id == user.id)):
            for item in db.scalars(
                select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
            ):
                if item.security_id not in universe_ids:
                    universe_ids.append(item.security_id)

        if settings.cio_refresh_research:
            refreshed = refresh_stale_research(db, universe_ids, profile)
            trace["steps"].append(
                {"agent": "research_refresh", "output": {"refreshed_symbols": refreshed}}
            )

        valuation_out = run_valuation_agent(db, universe_ids)
        trace["steps"].append({"agent": "valuation_agent", "output": valuation_out})

        factors = compute_factors(db, universe_ids)
        trace["steps"].append({"agent": "factor_agent", "output": factors})

        portfolio_out = propose_weights(
            db, portfolio_id, user.id, factors, profile, current_map=current_map
        )
        trace["steps"].append({"agent": "portfolio_agent", "output": portfolio_out})

        proposed = portfolio_out["proposed_weights"]
        risk_round = 0
        risk_result = check_risk(db, portfolio_id, proposed)
        while not risk_result["approved"] and risk_round < 2:
            proposed = risk_result["adjusted_weights"]
            risk_result = check_risk(db, portfolio_id, proposed)
            risk_round += 1
        trace["steps"].append({"agent": "risk_agent", "output": risk_result})

        dossiers = build_dossiers_for_universe(
            db, portfolio_id, universe_ids, profile, current_map, risk_result
        )
        trace["dossiers"] = {
            sym: dossier_summary_for_trace(d) for sym, d in dossiers.items()
        }

        symbols = [p.get("symbol") for p in proposed if p.get("symbol")]
        sectors: set[str] = set()
        for sid in universe_ids:
            sec = db.get(Security, sid)
            if sec and sec.sector:
                sectors.add(sec.sector)
        memories = search_memory_context(
            db,
            symbols=symbols,
            sectors=list(sectors),
            keywords=["教训", "复盘", "风险"],
            limit=5,
        )
        trace["memory_query"] = {"symbols": symbols, "sectors": list(sectors)}
        trace["memories"] = [{"title": m.title, "content": m.content} for m in memories]

        decision_ids, cio_outputs, cio_mode = generate_cio_decisions(
            db,
            portfolio_id,
            proposed,
            current_map,
            risk_result,
            memories,
            trace,
            profile,
            dossiers_by_symbol=dossiers,
            strategy_rules=strategy_rules,
        )
        trace["cio_mode"] = cio_mode

        run.status = AgentRunStatus.success
        run.output = {
            "decision_ids": decision_ids,
            "cio_decisions": cio_outputs,
            "trace": trace,
        }
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
    except Exception as e:
        run.status = AgentRunStatus.failed
        run.error_message = str(e)
        run.output = {"trace": trace}
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise


def list_agent_runs(db: Session, portfolio_id: UUID | None = None, limit: int = 20) -> list:
    q = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if portfolio_id:
        q = q.where(AgentRun.portfolio_id == portfolio_id)
    runs = db.scalars(q).all()
    return [
        {
            "id": str(r.id),
            "workflow_name": r.workflow_name,
            "status": r.status.value,
            "trigger": r.trigger,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "decision_ids": r.output.get("decision_ids", []) if r.output else [],
            "error_message": r.error_message,
            "agent_mode": (r.input_context or {}).get("agent_mode"),
        }
        for r in runs
    ]


def get_agent_run(db: Session, run_id: UUID) -> dict | None:
    r = db.get(AgentRun, run_id)
    if not r:
        return None
    return {
        "id": str(r.id),
        "workflow_name": r.workflow_name,
        "status": r.status.value,
        "input_context": r.input_context,
        "output": r.output,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


def get_agent_config() -> dict:
    from app.services.llm.client import is_llm_available, use_llm_agents

    return {
        "agent_mode": settings.agent_mode,
        "structuring_mode": settings.structuring_mode,
        "llm_configured": is_llm_available(),
        "llm_active": use_llm_agents(),
        "llm_model": settings.llm_model if settings.openai_api_key else None,
        "data_sync_cron_enabled": settings.data_sync_cron_enabled,
        "cio_decision_mode": settings.cio_decision_mode,
        "cio_refresh_research": settings.cio_refresh_research,
        "cio_max_symbols": settings.cio_max_symbols,
        "rebalance_cron_chain_after_sync": settings.rebalance_cron_chain_after_sync,
        "daily_report_cron_enabled": settings.daily_report_cron_enabled,
        "event_research_refresh_enabled": settings.event_research_refresh_enabled,
        "review_cron_enabled": settings.review_cron_enabled,
        "review_cron_time": settings.review_cron_time,
        "news_sync_cron_enabled": settings.news_sync_cron_enabled,
        "news_sync_cron_time": settings.news_sync_cron_time,
        "auth_password_configured": bool(settings.auth_password),
        "alembic_upgrade_on_start": settings.alembic_upgrade_on_start,
    }
