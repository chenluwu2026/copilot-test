from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ImpactDirection, NewsArticle, StructuredEvent
from app.services.structuring_service import event_to_dict


def list_events(
    db: Session,
    security_id: UUID | None = None,
    event_type: str | None = None,
    impact_direction: str | None = None,
    time_sensitivity: str | None = None,
    limit: int = 50,
) -> list[dict]:
    q = select(StructuredEvent).order_by(StructuredEvent.published_at.desc()).limit(limit)
    if event_type:
        q = q.where(StructuredEvent.event_type == event_type)
    if impact_direction:
        q = q.where(StructuredEvent.impact_direction == ImpactDirection(impact_direction))
    if time_sensitivity:
        from app.models import ConfidenceLevel

        q = q.where(StructuredEvent.time_sensitivity == ConfidenceLevel(time_sensitivity))

    events = list(db.scalars(q))
    if security_id:
        sid = str(security_id)
        events = [
            e
            for e in events
            if any(c.get("security_id") == sid for c in e.companies)
            or any(r.get("security_id") == sid for r in e.related_securities)
        ]

    result = []
    for e in events:
        article = None
        if e.source_id:
            article = db.get(NewsArticle, e.source_id)
        result.append(event_to_dict(e, article))
    return result


def get_event(db: Session, event_id: UUID) -> dict | None:
    e = db.get(StructuredEvent, event_id)
    if not e:
        return None
    article = db.get(NewsArticle, e.source_id) if e.source_id else None
    return event_to_dict(e, article)
