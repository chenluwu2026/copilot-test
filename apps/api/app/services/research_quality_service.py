"""研究质量评分：十段式完成度、估值情景、新鲜度、闸门。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchView, Security
from app.services.research_gate_service import research_allows_trade

SECTION_KEYS = [
    "business_model",
    "industry_space",
    "competitive_landscape",
    "financial_quality",
    "management",
    "growth_drivers",
    "key_risks",
    "current_valuation",
]


def _section_filled(fa: dict | None, key: str) -> bool:
    if not fa:
        return False
    val = fa.get(key)
    if val is None:
        return False
    if isinstance(val, str):
        return len(val.strip()) >= 20
    if isinstance(val, dict):
        return bool(val.get("summary") or val.get("text"))
    return bool(val)


def get_research_quality(db: Session, symbol: str, *, max_age_days: int = 60) -> dict:
    sec = db.scalar(select(Security).where(Security.symbol == symbol))
    if not sec:
        return {"symbol": symbol, "found": False}

    view = db.scalar(
        select(ResearchView)
        .where(ResearchView.security_id == sec.id)
        .order_by(ResearchView.version.desc())
        .limit(1)
    )
    if not view:
        allowed, reason = research_allows_trade(db, sec.id, max_age_days=max_age_days)
        return {
            "symbol": symbol,
            "found": True,
            "has_view": False,
            "completion_pct": 0,
            "sections": {k: False for k in SECTION_KEYS},
            "gate": {"research_allowed": allowed, "reason": reason},
            "issues": ["尚无研究观点，请维护十段式或生成草稿"],
        }

    fa = view.fundamental_analysis or {}
    sections = {k: _section_filled(fa, k) for k in SECTION_KEYS}
    filled = sum(1 for v in sections.values() if v)
    completion_pct = round(filled / len(SECTION_KEYS) * 100)

    scenarios = (view.scenario_analysis or {}).get("scenarios") or []
    has_scenarios = len(scenarios) >= 2
    has_valuation = bool(view.valuation_snapshot)

    created = view.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created).days if created else None

    allowed, reason = research_allows_trade(db, sec.id, max_age_days=max_age_days)
    issues: list[str] = []
    if completion_pct < 50:
        issues.append("十段式完成度不足 50%")
    if not has_scenarios:
        issues.append("缺少至少 2 个估值情景")
    if age_days is not None and age_days > max_age_days:
        issues.append(f"研究已 {age_days} 天未更新（阈值 {max_age_days} 天）")
    if not allowed:
        issues.append(f"交易闸门：{reason}")

    score = completion_pct
    if has_scenarios:
        score = min(100, score + 10)
    if has_valuation:
        score = min(100, score + 5)
    if age_days is not None and age_days <= max_age_days:
        score = min(100, score + 5)
    else:
        score = max(0, score - 15)

    grade = "A" if score >= 80 else "B" if score >= 60 else "C"
    return {
        "symbol": symbol,
        "found": True,
        "has_view": True,
        "view_id": str(view.id),
        "rating": view.rating.value if view.rating else None,
        "completion_pct": completion_pct,
        "sections": sections,
        "has_scenarios": has_scenarios,
        "scenario_count": len(scenarios),
        "has_valuation_snapshot": has_valuation,
        "age_days": age_days,
        "gate": {"research_allowed": allowed, "reason": reason},
        "quality_score": score,
        "quality_grade": grade,
        "issues": issues,
    }
