"""研究新鲜度闸门：无研究或过期时禁止加仓/买入。"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DecisionAction, ResearchView


def research_allows_trade(
    db: Session,
    security_id: UUID,
    *,
    max_age_days: int = 30,
) -> tuple[bool, str]:
    view = db.scalar(
        select(ResearchView)
        .where(ResearchView.security_id == security_id)
        .order_by(ResearchView.version.desc())
        .limit(1)
    )
    if not view:
        return False, "缺少研究报告"
    created = view.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created).days
    if age_days > max_age_days:
        return False, f"研究已过期（{age_days} 天，上限 {max_age_days} 天）"
    return True, ""


def gate_action_for_research(
    db: Session,
    security_id: UUID,
    action: DecisionAction,
    profile: dict,
) -> tuple[DecisionAction, str | None]:
    """对 buy/add 应用研究闸门，必要时降级为 watch。"""
    if action not in (DecisionAction.buy, DecisionAction.add):
        return action, None
    max_days = int(profile.get("research_max_age_days", 30))
    allowed, reason = research_allows_trade(db, security_id, max_age_days=max_days)
    if allowed:
        return action, None
    return DecisionAction.watch, reason
