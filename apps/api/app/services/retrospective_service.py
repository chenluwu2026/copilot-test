"""月度复盘 Markdown 聚合。"""
from calendar import monthrange
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import DailyPortfolioReport, Decision, DecisionOutcome, DecisionStatus


def generate_monthly_retrospective(
    db: Session,
    portfolio_id: UUID,
    *,
    year: int | None = None,
    month: int | None = None,
) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    decisions = db.scalars(
        select(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            Decision.created_at >= datetime.combine(start, datetime.min.time()).replace(
                tzinfo=timezone.utc
            ),
        )
        .options(joinedload(Decision.security), joinedload(Decision.outcome))
    ).all()

    executed = [d for d in decisions if d.status == DecisionStatus.executed]
    reviewed = [d for d in executed if d.outcome]
    returns = [
        float(d.outcome.return_since_decision_pct or 0)
        for d in reviewed
        if d.outcome
    ]

    reports = db.scalars(
        select(DailyPortfolioReport)
        .where(
            DailyPortfolioReport.portfolio_id == portfolio_id,
            DailyPortfolioReport.report_date >= start,
            DailyPortfolioReport.report_date <= end,
        )
        .order_by(DailyPortfolioReport.report_date)
    ).all()

    lines = [
        f"# {year}年{month}月 组合复盘",
        "",
        f"- 统计区间：{start.isoformat()} ~ {end.isoformat()}",
        f"- 决策草案/流转：{len(decisions)} 笔",
        f"- 已执行：{len(executed)} 笔",
        f"- 已复盘：{len(reviewed)} 笔",
        "",
    ]

    if returns:
        win = sum(1 for r in returns if r > 0)
        lines.extend(
            [
                "## 决策后验",
                "",
                f"- 平均收益：{sum(returns) / len(returns):.2f}%",
                f"- 胜率：{win / len(returns) * 100:.1f}%",
                f"- 最佳：{max(returns):.2f}% / 最差：{min(returns):.2f}%",
                "",
            ]
        )

    lines.append("## 重点决策")
    lines.append("")
    for d in reviewed[:10]:
        sym = d.security.symbol if d.security else "?"
        ret = float(d.outcome.return_since_decision_pct or 0) if d.outcome else 0
        summary = (d.outcome.outcome_summary or d.decision_reason or "")[:100]
        lines.append(f"- **{sym}** {d.action.value}：收益 {ret:.1f}% — {summary}")
    if not reviewed:
        lines.append("- （本月暂无已复盘决策）")
    lines.append("")

    lines.append("## 日报摘要")
    lines.append("")
    if reports:
        for r in reports[-5:]:
            lines.append(f"### {r.report_date.isoformat()}")
            lines.append((r.summary_md or "")[:500])
            lines.append("")
    else:
        lines.append("- （本月无日报，可在复盘页生成）")
        lines.append("")

    lines.extend(
        [
            "## 下月改进",
            "",
            "- [ ] 补齐过期研究的十段式",
            "- [ ] 低证据（C 级）草案补充引用后再批准",
            "- [ ] 到期决策按时复盘并激活记忆",
            "",
        ]
    )

    md = "\n".join(lines)
    return {
        "portfolio_id": str(portfolio_id),
        "year": year,
        "month": month,
        "summary_md": md,
        "stats": {
            "decisions": len(decisions),
            "executed": len(executed),
            "reviewed": len(reviewed),
            "daily_reports": len(reports),
        },
    }
