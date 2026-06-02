from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.factor_service import compute_factors
from app.config import settings
from app.services.llm.client import is_llm_available, use_llm_agents
from app.services.orchestrator import get_agent_config, get_agent_run, list_agent_runs, run_rebalance_workflow
from app.services.portfolio_agent_service import propose_weights
from app.services.risk_service import check_risk, portfolio_risk_dashboard
from app.services.user_context import get_default_user

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/config")
def agent_config():
    return get_agent_config()


@router.get("/config/health")
def agent_config_health():
    return {
        "agent_mode": settings.agent_mode,
        "structuring_mode": settings.structuring_mode,
        "llm_model": settings.llm_model,
        "llm_configured": is_llm_available(),
        "llm_active": use_llm_agents(),
        "openai_base_url_set": bool(settings.openai_base_url),
    }


@router.post("/workflows/rebalance/{portfolio_id}")
def run_rebalance(portfolio_id: UUID, db: Session = Depends(get_db)):
    try:
        run = run_rebalance_workflow(db, portfolio_id)
        return {
            "run_id": str(run.id),
            "status": run.status.value,
            "decision_ids": run.output.get("decision_ids", []),
        }
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.get("/runs")
def runs(portfolio_id: UUID | None = None, db: Session = Depends(get_db)):
    return list_agent_runs(db, portfolio_id)


@router.get("/runs/{run_id}")
def run_detail(run_id: UUID, db: Session = Depends(get_db)):
    data = get_agent_run(db, run_id)
    if not data:
        raise HTTPException(404, "运行记录不存在")
    return data


@router.get("/factors/{portfolio_id}")
def factors(portfolio_id: UUID, db: Session = Depends(get_db)):
    from app.models import Position
    from sqlalchemy import select

    ids = [
        p.security_id
        for p in db.scalars(select(Position).where(Position.portfolio_id == portfolio_id))
    ]
    from app.models import Watchlist, WatchlistItem

    user = get_default_user(db)
    for wl in db.scalars(select(Watchlist).where(Watchlist.user_id == user.id)):
        for item in db.scalars(select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)):
            if item.security_id not in ids:
                ids.append(item.security_id)
    return compute_factors(db, ids)


@router.get("/risk/{portfolio_id}")
def risk_dashboard(portfolio_id: UUID, db: Session = Depends(get_db)):
    return portfolio_risk_dashboard(db, portfolio_id)
