"""Dashboard 待办聚合。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, DecisionStatus
from app.services.data_quality_service import get_data_quality
from app.services.event_review_service import high_impact_event_todos
from app.services.profile_service import get_investment_profile
from app.services.review_reminder_service import review_summary
from app.services.operator_steps_service import assumptions_pending_verification
from app.services.user_context import get_default_user


def get_dashboard_actions(db: Session, portfolio_id: UUID) -> dict:
    user = get_default_user(db)
    profile = get_investment_profile(user)
    review = review_summary(db, portfolio_id, profile)

    draft_rows = list(
        db.scalars(
            select(Decision).where(
                Decision.portfolio_id == portfolio_id,
                Decision.status == DecisionStatus.draft,
            )
        )
    )
    drafts = len(draft_rows)
    low_evidence_drafts = sum(
        1
        for d in draft_rows
        if (d.cio_summary or {}).get("evidence_grade") == "C"
    )
    approved = len(
        list(
            db.scalars(
                select(Decision).where(
                    Decision.portfolio_id == portfolio_id,
                    Decision.status == DecisionStatus.approved,
                )
            )
        )
    )

    quality = get_data_quality(db)
    stale = quality["summary"].get("stale_quotes", 0) + quality["summary"].get(
        "missing_quotes", 0
    )

    event_todos = high_impact_event_todos(db, user.id)

    return {
        "portfolio_id": str(portfolio_id),
        "review": review,
        "draft_decisions": drafts,
        "low_evidence_drafts": low_evidence_drafts,
        "approved_decisions": approved,
        "stale_data_symbols": stale,
        "data_coverage_pct": quality["summary"].get("coverage_pct", 0),
        "event_review_todos": event_todos,
        "assumptions_pending": assumptions_pending_verification(db, portfolio_id),
    }
