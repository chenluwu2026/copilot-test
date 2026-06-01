"""事件 → 研究刷新整合（设计文档 05-agent-workflows §2–3）。"""
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ConfidenceLevel, Security, StructuredEvent
from app.services.research_refresh_service import refresh_stale_research
from app.services.research_service import generate_research_draft

logger = logging.getLogger(__name__)

HIGH_SENSITIVITY_EVENTS = frozenset(
    {
        "earnings_release",
        "regulation",
        "buyback",
        "macro_policy",
    }
)


def event_should_refresh_research(event: StructuredEvent) -> bool:
    if not settings.event_research_refresh_enabled:
        return False
    if event.time_sensitivity == ConfidenceLevel.high:
        return True
    if event.event_type in HIGH_SENSITIVITY_EVENTS:
        return True
    if event.impact_direction.value in ("negative", "mixed"):
        return True
    return False


def refresh_research_for_event(db: Session, event: StructuredEvent) -> list[str]:
    """对事件关联标的刷新研究草稿（遵守 research_refresh 不覆盖 human 规则）。"""
    from app.services.profile_service import get_investment_profile
    from app.services.user_context import get_default_user

    security_ids: list[UUID] = []
    for c in event.companies or []:
        sid = c.get("security_id")
        if sid:
            security_ids.append(UUID(str(sid)))
    for r in event.related_securities or []:
        sid = r.get("security_id")
        if sid and UUID(str(sid)) not in security_ids:
            security_ids.append(UUID(str(sid)))
    if not security_ids:
        return []

    user = get_default_user(db)
    profile = get_investment_profile(user)

    if settings.event_research_refresh_force_draft:
        refreshed: list[str] = []
        for sid in security_ids:
            try:
                generate_research_draft(db, sid)
                sec = db.get(Security, sid)
                if sec:
                    refreshed.append(sec.symbol)
            except Exception as e:
                logger.warning("event research draft failed %s: %s", sid, e)
        return refreshed

    return refresh_stale_research(db, security_ids, profile)


def maybe_refresh_research_after_event(db: Session, event: StructuredEvent) -> list[str]:
    if not event_should_refresh_research(event):
        return []
    symbols = refresh_research_for_event(db, event)
    if symbols:
        logger.info("event %s triggered research refresh: %s", event.id, symbols)
    return symbols
