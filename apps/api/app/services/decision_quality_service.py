"""决策草稿质量评分（证据完整度）。"""
from app.services.decision_service import validate_decision_payload


def score_decision_draft(dossier: dict | None, decision_payload: dict) -> dict:
    issues: list[str] = []
    score = 100

    assumptions = decision_payload.get("assumptions") or []
    review_conds = decision_payload.get("review_conditions") or []
    reason = decision_payload.get("decision_reason") or ""

    if not assumptions:
        issues.append("缺少核心假设")
        score -= 25
    elif not any(a.get("measurable") for a in assumptions):
        issues.append("假设均不可测量")
        score -= 10

    if not review_conds:
        issues.append("缺少复盘条件")
        score -= 20

    if len(reason) < 40:
        issues.append("决策理由过短")
        score -= 15

    if dossier:
        research = dossier.get("research") or {}
        if not research.get("view_id"):
            issues.append("无研究报告支撑")
            score -= 30
        elif research.get("age_days") is not None and research.get("age_days", 0) > 60:
            issues.append("研究过期")
            score -= 10
        if not dossier.get("events"):
            score -= 5
        gates = dossier.get("gates") or {}
        if gates.get("forbidden"):
            issues.append("标的在禁止清单")
            score -= 40
        if not gates.get("research_allowed") and decision_payload.get("action") in (
            "buy",
            "add",
        ):
            issues.append("研究闸门未通过")
            score -= 35
    else:
        issues.append("无证据卷宗")
        score -= 20

    try:
        validate_decision_payload(decision_payload)
    except Exception as e:
        issues.append(f"Schema 校验失败: {e}")
        score -= 30

    score = max(0, min(100, score))
    grade = "A" if score >= 80 else "B" if score >= 60 else "C"
    return {"score": score, "grade": grade, "issues": issues}
