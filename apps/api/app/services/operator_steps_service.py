"""基金经理一日：六步操作状态机。"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Decision,
    DecisionStatus,
    ResearchView,
    Watchlist,
    WatchlistItem,
)
from app.services.profile_service import get_investment_profile
from app.services.data_quality_service import get_data_quality
from app.services.dashboard_service import get_dashboard_actions
from app.services.user_context import get_default_user


def _step(
    step_id: str,
    label: str,
    href: str,
    *,
    complete: bool,
    blocked_reason: str | None = None,
) -> dict:
    if complete:
        status = "complete"
    elif blocked_reason:
        status = "blocked"
    else:
        status = "active"
    return {
        "id": step_id,
        "label": label,
        "href": href,
        "status": status,
        "blocked_reason": blocked_reason,
    }


def get_operator_steps(db: Session, portfolio_id: UUID) -> dict:
    user = get_default_user(db)
    profile = get_investment_profile(user)
    profile_ok_base = bool(profile.get("markets")) and bool(profile.get("style"))
    wl_items = db.scalar(
        select(func.count())
        .select_from(WatchlistItem)
        .join(Watchlist)
        .where(Watchlist.user_id == user.id)
    ) or 0
    profile_ok = profile_ok_base and wl_items >= 3

    quality = get_data_quality(db)
    coverage = quality["summary"].get("coverage_pct", 0)
    stale = quality["summary"].get("stale_quotes", 0) + quality["summary"].get("missing_quotes", 0)
    data_ok = coverage >= 70 and stale == 0

    research_count = db.scalar(select(func.count()).select_from(ResearchView)) or 0
    research_ok = research_count >= 2

    actions = get_dashboard_actions(db, portfolio_id)
    has_drafts = actions["draft_decisions"] > 0
    rebalance_ok = not has_drafts and actions.get("approved_decisions", 0) == 0

    inbox_ok = actions["draft_decisions"] == 0 and actions["approved_decisions"] == 0
    executed_count = db.scalar(
        select(func.count())
        .select_from(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            Decision.status == DecisionStatus.executed,
        )
    ) or 0
    review_ok = actions["review"]["due_count"] == 0 and executed_count >= 1

    steps = [
        _step(
            "profile",
            "画像与股票池",
            "/settings",
            complete=profile_ok,
            blocked_reason=None if profile_ok else "请完善投资画像并维护至少 3 只核心池标的",
        ),
        _step(
            "data_sync",
            "全量同步",
            "/data",
            complete=data_ok,
            blocked_reason=None if data_ok else f"行情覆盖率 {coverage}% 或存在过期标的，请先同步",
        ),
        _step(
            "research",
            "维护研究",
            "/research",
            complete=research_ok,
            blocked_reason=None if research_ok else "至少维护 2 份公司研究观点",
        ),
        _step(
            "rebalance",
            "生成调仓",
            "/portfolio",
            complete=rebalance_ok and executed_count > 0,
            blocked_reason=None
            if rebalance_ok or has_drafts
            else "请先在组合页生成调仓草案",
        ),
        _step(
            "inbox",
            "收件箱批准",
            "/decisions/inbox",
            complete=inbox_ok and executed_count >= 1,
            blocked_reason=None if not has_drafts else f"还有 {actions['draft_decisions']} 条草案待批准",
        ),
        _step(
            "review",
            "复盘记忆",
            "/review",
            complete=review_ok,
            blocked_reason=None
            if review_ok
            else (
                f"{actions['review']['due_count']} 条决策待复盘"
                if actions["review"]["due_count"]
                else "请先执行至少一笔决策后再复盘"
            ),
        ),
    ]

    completed = sum(1 for s in steps if s["status"] == "complete")
    return {
        "portfolio_id": str(portfolio_id),
        "completed_count": completed,
        "total_count": len(steps),
        "steps": steps,
    }


def assumptions_pending_verification(db: Session, portfolio_id: UUID) -> list[dict]:
    from datetime import date

    today = date.today()
    pending: list[dict] = []
    decisions = list(
        db.scalars(
            select(Decision)
            .where(
                Decision.portfolio_id == portfolio_id,
                Decision.status.in_([DecisionStatus.approved, DecisionStatus.executed]),
            )
            .options(selectinload(Decision.assumptions))
        )
    )
    for d in decisions:
        for a in d.assumptions:
            if a.measurable and a.deadline and a.deadline <= today:
                pending.append(
                    {
                        "decision_id": str(d.id),
                        "assumption_id": str(a.id),
                        "text": a.assumption_text,
                        "deadline": a.deadline.isoformat(),
                    }
                )
    return pending
