from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard_service import get_dashboard_actions

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/actions")
def dashboard_actions(portfolio_id: UUID, db: Session = Depends(get_db)):
    return get_dashboard_actions(db, portfolio_id)
