from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import decision_ledger_service as dls
from app.services.fm_daily_run_service import run_fm_daily
from app.services.fm_targets_service import get_latest_fm_targets

router = APIRouter(prefix="/fm", tags=["fund-manager"])


class FmDailyRunIn(BaseModel):
    portfolio_id: UUID
    max_turnover_pct: float = 30
    auto_approve: bool = False
    auto_execute_simulated: bool = False
    simulated_fill_ratio: float = 0.7
    auto_retry_resize: bool = True
    max_retry_steps: int = 3
    retry_decay_factor: float = 0.75
    auto_apply_fallback_partial: bool = True
    candidate_limit: int = Field(default=20, ge=1, le=50)


@router.post("/daily-run")
def fm_daily_run(body: FmDailyRunIn, db: Session = Depends(get_db)):
    try:
        return run_fm_daily(
            db,
            portfolio_id=body.portfolio_id,
            max_turnover_pct=body.max_turnover_pct,
            auto_approve=body.auto_approve,
            auto_execute_simulated=body.auto_execute_simulated,
            simulated_fill_ratio=body.simulated_fill_ratio,
            auto_retry_resize=body.auto_retry_resize,
            max_retry_steps=body.max_retry_steps,
            retry_decay_factor=body.retry_decay_factor,
            auto_apply_fallback_partial=body.auto_apply_fallback_partial,
            candidate_limit=body.candidate_limit,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/latest-targets")
def fm_latest_targets(portfolio_id: UUID, db: Session = Depends(get_db)):
    return get_latest_fm_targets(db, portfolio_id)


@router.get("/runs")
def list_fm_runs(portfolio_id: UUID, limit: int = 30, db: Session = Depends(get_db)):
    return dls.list_run_summaries(db, portfolio_id, limit=limit)


@router.get("/runs/{run_id}")
def get_fm_run(portfolio_id: UUID, run_id: str, db: Session = Depends(get_db)):
    items = dls.list_ledgers_by_run(db, portfolio_id=portfolio_id, run_id=run_id)
    if not items:
        raise HTTPException(404, "未找到该 run_id 的账本记录")
    gate_stats = dls.gate_failure_stats(db, portfolio_id, limit=200)
    return {
        "run_id": run_id,
        "portfolio_id": str(portfolio_id),
        "ledger_count": len(items),
        "gate_failure_stats": gate_stats,
        "ledgers": [
            {
                "id": str(x.id),
                "portfolio_id": str(x.portfolio_id),
                "security_id": str(x.security_id),
                "decision_id": str(x.decision_id) if x.decision_id else None,
                "run_id": x.run_id,
                "status": x.status.value,
                "proposal_json": x.proposal_json,
                "risk_result_json": x.risk_result_json,
                "execution_plan_json": x.execution_plan_json,
                "execution_result_json": x.execution_result_json,
                "postmortem_json": x.postmortem_json,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in items
        ],
    }


@router.get("/ledgers")
def list_fm_ledgers(portfolio_id: UUID, run_id: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    items = dls.list_ledgers(db, portfolio_id=portfolio_id, limit=limit)
    if run_id:
        items = [x for x in items if x.run_id == run_id]
    return [
        {
            "id": str(x.id),
            "portfolio_id": str(x.portfolio_id),
            "security_id": str(x.security_id),
            "decision_id": str(x.decision_id) if x.decision_id else None,
            "run_id": x.run_id,
            "status": x.status.value,
            "proposal_json": x.proposal_json,
            "risk_result_json": x.risk_result_json,
            "execution_plan_json": x.execution_plan_json,
            "execution_result_json": x.execution_result_json,
            "created_at": x.created_at.isoformat() if x.created_at else None,
        }
        for x in items
    ]
