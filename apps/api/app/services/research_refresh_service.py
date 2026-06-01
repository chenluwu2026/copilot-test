"""调仓前刷新过期研究（不覆盖人工定稿）。"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchView, Security
from app.services.research_service import generate_research_draft


def _view_age_days(view: ResearchView | None) -> int | None:
    if not view or not view.created_at:
        return None
    created = view.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created).days


def should_refresh_research(view: ResearchView | None, max_age_days: int) -> bool:
    if view is None:
        return True
    if view.agent_name == "human":
        return False
    age = _view_age_days(view)
    if age is None:
        return True
    if age <= max_age_days:
        return False
    return view.agent_name.startswith("research_agent") or view.agent_name.endswith("_llm")


def refresh_stale_research(
    db: Session,
    security_ids: list[UUID],
    profile: dict,
) -> list[str]:
    max_age = int(profile.get("research_max_age_days", 30))
    refreshed: list[str] = []
    for sid in security_ids:
        sec = db.get(Security, sid)
        if not sec:
            continue
        view = db.scalar(
            select(ResearchView)
            .where(ResearchView.security_id == sid)
            .order_by(ResearchView.version.desc())
            .limit(1)
        )
        if not should_refresh_research(view, max_age):
            continue
        try:
            generate_research_draft(db, sid)
            refreshed.append(sec.symbol)
        except Exception:
            continue
    return refreshed
