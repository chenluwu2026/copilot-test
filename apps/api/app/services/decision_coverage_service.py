"""决策对照：卷宗要点 vs CIO 输出是否覆盖。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Decision
from app.services.decision_dossier_service import build_dossier
from app.services.decision_quality_service import score_decision_draft
from app.services.profile_service import get_investment_profile
from app.services.user_context import get_default_user


def _coverage_item(label: str, covered: bool, detail: str) -> dict:
    return {"label": label, "covered": covered, "detail": detail}


def get_decision_coverage(db: Session, decision_id: UUID) -> dict:
    decision = db.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(
            joinedload(Decision.security),
            joinedload(Decision.assumptions),
            joinedload(Decision.references),
        )
    )
    if not decision:
        raise ValueError("决策不存在")

    user = get_default_user(db)
    profile = get_investment_profile(user)
    dossier = build_dossier(
        db,
        decision.portfolio_id,
        decision.security_id,
        profile,
        current_weight_pct=float(decision.current_weight_pct or 0),
    )

    reason = (decision.decision_reason or "").lower()
    dossier_research = dossier.get("research") or {}
    research_title = (
        dossier_research.get("investment_conclusion") or dossier_research.get("rating") or ""
    )[:80]
    events = dossier.get("events") or []
    factor = dossier.get("factor") or {}
    risk = dossier.get("risk") or {}

    checks = [
        _coverage_item(
            "研究结论",
            bool(dossier_research.get("view_id"))
            and (
                not research_title
                or any(w in reason for w in research_title.lower().split()[:3] if len(w) > 2)
                or len(reason) >= 80
            ),
            research_title or "无研究 view",
        ),
        _coverage_item(
            "核心假设",
            len(decision.assumptions) >= 1,
            f"{len(decision.assumptions)} 条假设",
        ),
        _coverage_item(
            "复盘条件",
            len(decision.review_conditions or []) >= 1,
            f"{len(decision.review_conditions or [])} 条条件",
        ),
        _coverage_item(
            "近期事件",
            len(events) == 0 or "事件" in decision.decision_reason or len(events) <= 3,
            f"{len(events)} 条相关事件",
        ),
        _coverage_item(
            "因子/动量",
            not factor or any(
                k in reason for k in ("动量", "因子", "momentum", "factor", "估值")
            ),
            str(factor.get("momentum_20d") if factor else "无因子数据"),
        ),
        _coverage_item(
            "风险约束",
            not (risk.get("violations") or [])
            or "风险" in decision.decision_reason
            or "减仓" in decision.decision_reason,
            str(risk.get("violations") or []),
        ),
        _coverage_item(
            "证据引用",
            len(decision.references) >= 1,
            f"{len(decision.references)} 条引用",
        ),
    ]

    covered_count = sum(1 for c in checks if c["covered"])
    coverage_pct = round(covered_count / len(checks) * 100) if checks else 0

    payload = {
        "assumptions": [{"text": a.assumption_text, "measurable": a.measurable} for a in decision.assumptions],
        "review_conditions": decision.review_conditions or [],
        "decision_reason": decision.decision_reason,
        "action": decision.action.value,
    }
    quality = score_decision_draft(dossier, payload)

    return {
        "decision_id": str(decision_id),
        "symbol": decision.security.symbol if decision.security else "",
        "coverage_pct": coverage_pct,
        "checks": checks,
        "dossier_summary": {
            "research_rating": dossier_research.get("rating"),
            "research_age_days": dossier_research.get("age_days"),
            "event_count": len(events),
            "gates": dossier.get("gates"),
        },
        "evidence_grade": quality.get("grade"),
        "evidence_score": quality.get("score"),
        "evidence_issues": quality.get("issues"),
    }
