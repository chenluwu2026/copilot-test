from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
        return {
            "decision_id": str(o.decision_id),
            "return_since_decision_pct": float(o.return_since_decision_pct or 0),
            "outcome_summary": o.outcome_summary,
            "what_went_right": o.what_went_right,
            "what_went_wrong": o.what_went_wrong,
            "assumption_results": o.assumption_results,
            "price_metadata": o.price_metadata or {},
            "memory_id": memory_id,
        }
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


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
