from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyPortfolioReport, Decision, DecisionStatus
from app.services.nav_service import record_nav_snapshot
from app.services.portfolio_service import get_portfolio_summary


def generate_daily_report(db: Session, portfolio_id: UUID, report_date: date | None = None) -> DailyPortfolioReport:
    report_date = report_date or date.today()
    record_nav_snapshot(db, portfolio_id, report_date)
    summary = get_portfolio_summary(db, portfolio_id)

    open_decisions = db.scalars(
        select(Decision).where(
            Decision.portfolio_id == portfolio_id,
            Decision.status.in_([DecisionStatus.draft, DecisionStatus.approved]),
        )
    ).all()

    positions = summary["positions"]
    top = sorted(positions, key=lambda x: abs(x.get("unrealized_pnl", 0)), reverse=True)[:5]

    lines = [
        f"# {summary['name']} 日报 — {report_date.isoformat()}",
        "",
        f"- **组合净值**: {summary['nav']:,.2f}",
        f"- **累计收益**: {summary['cumulative_return_pct']:.2f}%",
        f"- **现金占比**: {summary['cash_pct']:.1f}%",
        f"- **持仓数量**: {summary['position_count']}",
        "",
        "## Top 持仓",
    ]
    for p in positions[:8]:
        lines.append(
            f"- {p['name']} ({p['symbol']}): 权重 {p['weight_pct']:.1f}%, "
            f"浮盈亏 {p['unrealized_pnl']:,.0f}"
        )
    if open_decisions:
        lines.extend(["", "## 待处理决策", ""])
        for d in open_decisions:
            lines.append(f"- [{d.status.value}] {d.action.value} — {d.decision_reason[:80]}...")

    summary_md = "\n".join(lines)
    metrics = {
        "nav": summary["nav"],
        "cumulative_return_pct": summary["cumulative_return_pct"],
        "cash_pct": summary["cash_pct"],
    }

    existing = db.scalar(
        select(DailyPortfolioReport).where(
            DailyPortfolioReport.portfolio_id == portfolio_id,
            DailyPortfolioReport.report_date == report_date,
        )
    )
    if existing:
        existing.summary_md = summary_md
        existing.metrics = metrics
        existing.top_movers = top
        db.commit()
        db.refresh(existing)
        return existing

    report = DailyPortfolioReport(
        portfolio_id=portfolio_id,
        report_date=report_date,
        summary_md=summary_md,
        metrics=metrics,
        top_movers=top,
        agent_commentary={"note": "Phase 1 规则生成日报"},
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
