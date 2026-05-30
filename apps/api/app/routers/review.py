from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.review_service import (
    attribution_report,
    backtest_decisions,
    list_open_decisions,
    review_decision,
)

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/open-decisions")
def open_decisions(portfolio_id: UUID | None = None, db: Session = Depends(get_db)):
    return list_open_decisions(db, portfolio_id)


@router.post("/decisions/{decision_id}/run")
def run_review(decision_id: UUID, db: Session = Depends(get_db)):
    try:
        o = review_decision(db, decision_id)
        return {
            "decision_id": str(o.decision_id),
            "return_since_decision_pct": float(o.return_since_decision_pct or 0),
            "outcome_summary": o.outcome_summary,
            "what_went_right": o.what_went_right,
            "what_went_wrong": o.what_went_wrong,
            "assumption_results": o.assumption_results,
        }
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/attribution/{portfolio_id}")
def attribution(portfolio_id: UUID, db: Session = Depends(get_db)):
    return attribution_report(db, portfolio_id)


@router.get("/backtest/{portfolio_id}")
def backtest(portfolio_id: UUID, db: Session = Depends(get_db)):
    return backtest_decisions(db, portfolio_id)
