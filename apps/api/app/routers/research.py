from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResearchRating, Security
from app.services import event_service, research_service as rs

router = APIRouter(prefix="/research", tags=["research"])


class ResearchCreate(BaseModel):
    security_id: UUID
    rating: str
    horizon: str = "6-12个月"
    fundamental_analysis: dict
    investment_conclusion: str
    scenario_analysis: dict | None = None
    valuation_snapshot: dict | None = None


@router.get("")
def list_research(db: Session = Depends(get_db)):
    return rs.list_research_summaries(db)


@router.get("/symbol/{symbol}")
def get_by_symbol(symbol: str, db: Session = Depends(get_db)):
    data = rs.get_research_by_symbol(db, symbol)
    if not data:
        raise HTTPException(404, "暂无研究或标的不存在")
    sec = db.scalar(select(Security).where(Security.symbol == symbol))
    if sec:
        data["related_events"] = event_service.list_events(db, security_id=sec.id, limit=10)
    return data


@router.post("")
def create_research(body: ResearchCreate, db: Session = Depends(get_db)):
    try:
        view = rs.create_research_view(
            db,
            body.security_id,
            ResearchRating(body.rating),
            body.fundamental_analysis,
            body.investment_conclusion,
            body.horizon,
            body.scenario_analysis,
            body.valuation_snapshot,
        )
        return rs._view_detail(view)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{security_id}/generate-draft")
def generate_draft(security_id: UUID, db: Session = Depends(get_db)):
    try:
        view = rs.generate_research_draft(db, security_id)
        return rs._view_detail(view)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
