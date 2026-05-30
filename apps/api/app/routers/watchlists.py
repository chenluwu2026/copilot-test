from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Watchlist, WatchlistItem, WatchlistTier
from app.schemas_api import WatchlistCreate, WatchlistItemCreate
from app.services.user_context import get_default_user

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("")
def list_watchlists(db: Session = Depends(get_db)):
    user = get_default_user(db)
    lists = db.scalars(
        select(Watchlist)
        .where(Watchlist.user_id == user.id)
        .options(joinedload(Watchlist.items).joinedload(WatchlistItem.security))
    ).unique().all()
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "description": w.description,
            "items": [
                {
                    "id": str(i.id),
                    "security_id": str(i.security_id),
                    "symbol": i.security.symbol,
                    "name": i.security.name,
                    "tier": i.tier.value,
                    "thesis_summary": i.thesis_summary,
                }
                for i in w.items
            ],
        }
        for w in lists
    ]


@router.post("")
def create_watchlist(body: WatchlistCreate, db: Session = Depends(get_db)):
    user = get_default_user(db)
    w = Watchlist(user_id=user.id, name=body.name, description=body.description)
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": str(w.id), "name": w.name}


@router.post("/{watchlist_id}/items")
def add_item(watchlist_id: UUID, body: WatchlistItemCreate, db: Session = Depends(get_db)):
    w = db.get(Watchlist, watchlist_id)
    if not w:
        raise HTTPException(404, "股票池不存在")
    item = WatchlistItem(
        watchlist_id=watchlist_id,
        security_id=body.security_id,
        tier=WatchlistTier(body.tier),
        thesis_summary=body.thesis_summary,
    )
    db.add(item)
    db.commit()
    return {"id": str(item.id)}
