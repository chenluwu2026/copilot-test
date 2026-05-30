from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Market, Security
from app.schemas_api import SecurityOut

router = APIRouter(prefix="/securities", tags=["securities"])


@router.get("", response_model=list[SecurityOut])
def search_securities(
    q: str | None = Query(None),
    market: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    stmt = select(Security).where(Security.is_active.is_(True))
    if market:
        stmt = stmt.where(Security.market == Market(market))
    if q:
        stmt = stmt.where(
            or_(Security.symbol.ilike(f"%{q}%"), Security.name.ilike(f"%{q}%"))
        )
    stmt = stmt.limit(limit)
    rows = db.scalars(stmt).all()
    return [
        SecurityOut(
            id=r.id,
            symbol=r.symbol,
            name=r.name,
            market=r.market.value,
            currency=r.currency,
            sector=r.sector,
            lot_size=r.lot_size,
            last_price=float(r.last_price) if r.last_price else None,
        )
        for r in rows
    ]
