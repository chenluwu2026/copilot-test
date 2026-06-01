"""从决策反馈生成投资画像调整建议。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, UserFeedback
from app.services.profile_service import get_investment_profile, normalize_profile


def suggest_profile_updates(db: Session, user_id) -> dict:
    feedbacks = db.scalars(
        select(UserFeedback)
        .where(UserFeedback.user_id == user_id)
        .order_by(UserFeedback.created_at.desc())
        .limit(20)
    ).all()
    if not feedbacks:
        return {"suggestions": [], "rationale": "暂无决策反馈"}

    corrections = [f.correction for f in feedbacks if f.correction]
    low_ratings = [f for f in feedbacks if f.rating and f.rating <= 2]

    suggestions: list[dict] = []
    text_blob = " ".join(corrections).lower()

    if any(k in text_blob for k in ("保守", "降仓", "现金", "回撤")):
        rb = normalize_profile({})["risk_budget"]
        suggestions.append(
            {
                "field": "risk_budget.min_cash_pct",
                "current": rb["min_cash_pct"],
                "suggested": min(rb["min_cash_pct"] + 5, 40),
                "reason": "多条反馈提及保守或现金需求",
            }
        )

    if any(k in text_blob for k in ("单票", "集中", "上限")):
        rb = normalize_profile({})["risk_budget"]
        suggestions.append(
            {
                "field": "risk_budget.max_single_name_pct",
                "current": rb["max_single_name_pct"],
                "suggested": max(rb["max_single_name_pct"] - 2, 5),
                "reason": "反馈提及集中度风险",
            }
        )

    if low_ratings:
        suggestions.append(
            {
                "field": "research_max_age_days",
                "current": 30,
                "suggested": 21,
                "reason": f"近 {len(low_ratings)} 条低分反馈，建议缩短研究有效期以强化闸门",
            }
        )

    return {
        "suggestions": suggestions[:5],
        "rationale": f"基于最近 {len(feedbacks)} 条决策反馈",
        "sample_corrections": corrections[:3],
    }


def suggestion_to_patch(suggestion: dict) -> dict:
    """将单条建议转为 PATCH /users/me/profile 可用的 patch。"""
    field = suggestion.get("field", "")
    val = suggestion.get("suggested")
    if field == "risk_budget.min_cash_pct":
        return {"risk_budget": {"min_cash_pct": val}}
    if field == "risk_budget.max_single_name_pct":
        return {"risk_budget": {"max_single_name_pct": val}}
    if field == "research_max_age_days":
        return {"research_max_age_days": int(val)}
    return {}
