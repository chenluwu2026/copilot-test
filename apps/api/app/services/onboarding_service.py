"""Phase 1 DoD 与 onboarding 进度。"""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    DailyPortfolioReport,
    Decision,
    DecisionStatus,
    NavSnapshot,
    Trade,
)


def _decision_meets_quality(d: Decision) -> bool:
    has_assumptions = len(d.assumptions) >= 1
    has_review = bool(d.review_conditions)
    has_refs = len(d.references) >= 1
    return has_assumptions and has_review and has_refs


def get_phase1_dod(db: Session, portfolio_id: UUID) -> dict:
    trade_count = db.scalar(
        select(func.count()).select_from(Trade).where(Trade.portfolio_id == portfolio_id)
    ) or 0

    decisions = list(
        db.scalars(
            select(Decision)
            .where(Decision.portfolio_id == portfolio_id)
            .options(
                selectinload(Decision.assumptions),
                selectinload(Decision.references),
            )
        )
    )
    quality_decisions = [d for d in decisions if _decision_meets_quality(d)]
    executed = [d for d in decisions if d.status == DecisionStatus.executed]

    nav_count = db.scalar(
        select(func.count()).select_from(NavSnapshot).where(NavSnapshot.portfolio_id == portfolio_id)
    ) or 0

    report_count = db.scalar(
        select(func.count())
        .select_from(DailyPortfolioReport)
        .where(DailyPortfolioReport.portfolio_id == portfolio_id)
    ) or 0

    checks = {
        "trades_gte_5": {
            "ok": trade_count >= 5,
            "current": trade_count,
            "required": 5,
            "hint": "在组合页录入至少 5 笔模拟交易，或运行种子数据增强脚本。",
        },
        "decisions_gte_3_with_metadata": {
            "ok": len(quality_decisions) >= 3,
            "current": len(quality_decisions),
            "required": 3,
            "hint": "至少 3 条决策含假设、复盘条件与参考信息。",
        },
        "decision_executed": {
            "ok": len(executed) >= 1,
            "current": len(executed),
            "required": 1,
            "hint": "批准一条决策并在收件箱执行成交。",
        },
        "nav_points_gte_5": {
            "ok": nav_count >= 5,
            "current": nav_count,
            "required": 5,
            "hint": "日终净值需 ≥5 个点；可执行 NAV 回填或等待日终批处理。",
        },
        "daily_report_exists": {
            "ok": report_count >= 1,
            "current": report_count,
            "required": 1,
            "hint": "在复盘页或 API 生成至少 1 份组合日报。",
        },
    }

    completed = sum(1 for c in checks.values() if c["ok"])
    return {
        "portfolio_id": str(portfolio_id),
        "phase": 1,
        "completed_count": completed,
        "total_count": len(checks),
        "all_complete": completed == len(checks),
        "checks": checks,
    }
