"""重大事件 → Dashboard 待办（关注池标的）。"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ImpactDirection, Security, Watchlist, WatchlistItem
from app.services.event_service import list_events


def high_impact_event_todos(
    db: Session,
    user_id: UUID,
    *,
    hours: int = 24,
    limit: int = 10,
) -> list[dict]:
    symbols: set[str] = set()
    sid_to_symbol: dict[str, str] = {}
    for wl in db.scalars(select(Watchlist).where(Watchlist.user_id == user_id)):
        for item in db.scalars(
            select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
        ):
            sec = db.get(Security, item.security_id)
            if sec:
                symbols.add(sec.symbol)
                sid_to_symbol[str(item.security_id)] = sec.symbol

    if not symbols:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = list_events(db, limit=80)
    todos: list[dict] = []
    for ev in events:
        pub = ev.get("published_at")
        if not pub:
            continue
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if pub_dt < cutoff:
            continue
        impact = ev.get("impact_direction")
        if impact not in (
            ImpactDirection.negative.value,
            ImpactDirection.positive.value,
            ImpactDirection.mixed.value,
        ):
            continue
        matched = [
            c.get("symbol")
            for c in ev.get("companies", [])
            if c.get("symbol") in symbols
        ]
        if not matched:
            for r in ev.get("related_securities", []):
                sid = r.get("security_id")
                if sid and sid_to_symbol.get(sid) in symbols:
                    matched.append(sid_to_symbol[sid])
        if not matched:
            continue
        todos.append(
            {
                "event_id": ev.get("id"),
                "symbols": list(dict.fromkeys(matched)),
                "summary": (ev.get("summary") or "")[:160],
                "impact_direction": impact,
                "published_at": pub,
                "suggested_action": "review_rebalance",
            }
        )
        if len(todos) >= limit:
            break
    return todos
