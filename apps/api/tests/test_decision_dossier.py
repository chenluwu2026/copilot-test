"""决策卷宗与质量评分单元测试。"""
from app.services.decision_quality_service import score_decision_draft


def test_score_high_with_dossier():
    dossier = {
        "research": {"view_id": "v1", "age_days": 10},
        "events": [{"id": "e1"}],
        "gates": {"research_allowed": True, "forbidden": False},
    }
    payload = {
        "action": "add",
        "decision_reason": "研究结论显示盈利改善，估值 base 情景目标价上行，因子综合分 72。",
        "assumptions": [{"text": "收入增速维持双位数", "measurable": True}],
        "review_conditions": ["季度收入低于预期 10% 时复盘"],
        "security": {"symbol": "600519.SH", "name": "茅台"},
        "current_weight_pct": 0,
        "target_weight_pct": 5,
        "main_risks": ["估值偏高"],
        "confidence_grade": "B+",
        "holding_period": "6-12个月",
        "decision_by": "cio_agent",
    }
    result = score_decision_draft(dossier, payload)
    assert result["grade"] in ("A", "B")
    assert result["score"] >= 60


def test_score_low_without_research():
    result = score_decision_draft(
        {"research": {}, "gates": {"research_allowed": False, "forbidden": False}},
        {
            "action": "buy",
            "decision_reason": "看好",
            "assumptions": [],
            "review_conditions": [],
            "security": {"symbol": "X", "name": "X"},
            "current_weight_pct": 0,
            "target_weight_pct": 5,
            "main_risks": ["x"],
            "confidence_grade": "C",
            "holding_period": "3m",
            "decision_by": "cio_agent",
        },
    )
    assert result["grade"] == "C"
    assert result["score"] < 60
