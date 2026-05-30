from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import event_service
from app.services.structuring_service import ingest_news

router = APIRouter(prefix="/events", tags=["events"])


class NewsIngest(BaseModel):
    title: str
    body: str = ""
    security_ids: list[UUID]
    source_name: str = "manual"
    source_url: str | None = None


@router.get("")
def list_events(
    security_id: UUID | None = None,
    event_type: str | None = None,
    impact_direction: str | None = None,
    time_sensitivity: str | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    return event_service.list_events(
        db, security_id, event_type, impact_direction, time_sensitivity, limit
    )


@router.get("/{event_id}")
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    ev = event_service.get_event(db, event_id)
    if not ev:
        raise HTTPException(404, "事件不存在")
    return ev


@router.post("/ingest")
def ingest(body: NewsIngest, db: Session = Depends(get_db)):
    try:
        article, event = ingest_news(
            db,
            body.title,
            body.body,
            body.security_ids,
            body.source_name,
            body.source_url,
        )
        return {
            "article_id": str(article.id),
            "event_id": str(event.id),
        }
    except Exception as e:
        raise HTTPException(400, str(e)) from e
