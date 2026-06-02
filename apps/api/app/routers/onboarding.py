from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio
from app.services.onboarding_service import get_phase1_dod

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def onboarding_status(portfolio_id: UUID | None = None, db: Session = Depends(get_db)):
    if portfolio_id is None:
        p = db.scalar(select(Portfolio).limit(1))
        if not p:
            raise HTTPException(404, "暂无组合")
        portfolio_id = p.id
    else:
        p = db.get(Portfolio, portfolio_id)
        if not p:
            raise HTTPException(404, "组合不存在")
    return get_phase1_dod(db, portfolio_id)
