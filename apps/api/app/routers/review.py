from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.profile_service import get_investment_profile
from app.services.review_reminder_service import (
    list_open_decisions_enriched,
    list_pending_memory_promotions,
    promote_or_activate_memory,
    review_summary,
)
from app.services.backtest_quality_service import backtest_quality_report
from app.services.execution_quality_service import execution_quality_report
from app.services.retrospective_service import generate_monthly_retrospective
from app.services.review_quality_service import build_review_quality
from app.services.review_service import (
    attribution_report,
    backtest_decisions,
    review_decision,
)
from app.services.user_context import get_default_user

router = APIRouter(prefix="/review", tags=["review"])


class PromoteMemoryBody(BaseModel):
    title: str | None = None
    activate: bool = False


@router.get("/summary")
def summary(portfolio_id: UUID, db: Session = Depends(get_db)):
    user = get_default_user(db)
    profile = get_investment_profile(user)
    return review_summary(db, portfolio_id, profile)


@router.get("/pending-memories")
def pending_memories(portfolio_id: UUID, db: Session = Depends(get_db)):
    return list_pending_memory_promotions(db, portfolio_id)


@router.get("/open-decisions")
def open_decisions(portfolio_id: UUID | None = None, db: Session = Depends(get_db)):
    user = get_default_user(db)
    profile = get_investment_profile(user)
    return list_open_decisions_enriched(db, portfolio_id, profile)


@router.post("/decisions/{decision_id}/run")
def run_review(decision_id: UUID, db: Session = Depends(get_db)):
    try:
        o, memory_id = review_decision(db, decision_id)
        quality = build_review_quality(db, decision_id, memory_id=memory_id)
        from app.services.decision_ledger_service import get_latest_ledger_by_decision

        ledger = get_latest_ledger_by_decision(db, decision_id)
        return {
            "decision_id": str(o.decision_id),
            "return_since_decision_pct": float(o.return_since_decision_pct or 0),
            "outcome_summary": o.outcome_summary,
            "what_went_right": o.what_went_right,
            "what_went_wrong": o.what_went_wrong,
            "assumption_results": o.assumption_results,
            "price_metadata": o.price_metadata or {},
            "memory_id": memory_id,
            "review_quality": quality,
            "ledger_status": ledger.status.value if ledger else None,
            "ledger_has_postmortem": bool(ledger and (ledger.postmortem_json or {})),
            "run_id": ledger.run_id if ledger else None,
        }
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/decisions/{decision_id}/quality")
def review_quality(decision_id: UUID, db: Session = Depends(get_db)):
    try:
        return build_review_quality(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/retrospective/{portfolio_id}")
def monthly_retrospective(
    portfolio_id: UUID,
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: Session = Depends(get_db),
):
    return generate_monthly_retrospective(db, portfolio_id, year=year, month=month)


@router.get("/backtest-quality/{portfolio_id}")
def backtest_quality(portfolio_id: UUID, db: Session = Depends(get_db)):
    return backtest_quality_report(db, portfolio_id)


@router.get("/execution-quality/{portfolio_id}")
def execution_quality(portfolio_id: UUID, db: Session = Depends(get_db)):
    return execution_quality_report(db, portfolio_id)


@router.post("/decisions/{decision_id}/memory")
def promote_memory(
    decision_id: UUID, body: PromoteMemoryBody, db: Session = Depends(get_db)
):
    try:
        return promote_or_activate_memory(db, decision_id, body.title, body.activate)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/attribution/{portfolio_id}")
def attribution(portfolio_id: UUID, db: Session = Depends(get_db)):
    return attribution_report(db, portfolio_id)


@router.get("/backtest/{portfolio_id}")
def backtest(portfolio_id: UUID, db: Session = Depends(get_db)):
    return backtest_decisions(db, portfolio_id)
