"""到期决策自动复盘（方案 B）。"""
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.profile_service import get_investment_profile
from app.services.review_reminder_service import _collect_open_decisions
from app.services.review_service import review_decision
from app.services.user_context import get_default_user

logger = logging.getLogger(__name__)


def run_due_reviews(db: Session, portfolio_id: UUID, profile: dict, max_count: int = 5) -> dict:
    items = _collect_open_decisions(db, portfolio_id, profile)
    due = [x for x in items if x.get("review_due")][:max_count]
    completed = []
    errors = []
    for item in due:
        did = UUID(item["decision_id"])
        try:
            review_decision(db, did)
            completed.append(item["symbol"])
        except Exception as e:
            errors.append(f"{item.get('symbol')}: {e}")
            logger.warning("auto review failed %s: %s", did, e)
    return {"reviewed": len(completed), "symbols": completed, "errors": errors}


def run_scheduled_reviews() -> dict:
    from app.config import settings
    from app.database import SessionLocal
    from app.models import Portfolio

    db = SessionLocal()
    try:
        user = get_default_user(db)
        from sqlalchemy import select

        portfolio = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
        if not portfolio:
            return {"reviewed": 0}
        profile = get_investment_profile(user)
        return run_due_reviews(
            db, portfolio.id, profile, max_count=settings.review_cron_max_per_run
        )
    finally:
        db.close()
