"""决策质量与使用成效指标（路线图验收）。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, Decision, DecisionReference, DecisionStatus


def get_quality_metrics(db: Session, portfolio_id: UUID) -> dict:
    drafts = list(
        db.scalars(
            select(Decision).where(
                Decision.portfolio_id == portfolio_id,
                Decision.status.in_([DecisionStatus.draft, DecisionStatus.approved, DecisionStatus.executed]),
            )
        )
    )
    approved = [d for d in drafts if d.status in (DecisionStatus.approved, DecisionStatus.executed)]
    executed = [d for d in drafts if d.status == DecisionStatus.executed]

    with_refs = 0
    for d in drafts:
        refs = db.scalars(select(DecisionReference).where(DecisionReference.decision_id == d.id)).all()
        if any(r.ref_type.value in ("research_report", "news", "filing", "valuation") for r in refs):
            with_refs += 1
        elif (d.cio_summary or {}).get("evidence_grade"):
            with_refs += 1

    runs = list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.portfolio_id == portfolio_id, AgentRun.workflow_name == "rebalance_cio")
            .order_by(AgentRun.started_at.desc())
            .limit(50)
        )
    )
    llm_runs = 0
    for r in runs:
        trace = (r.output or {}).get("trace") or {}
        if trace.get("cio_mode") == "llm":
            llm_runs += 1

    draft_count = len([d for d in drafts if d.status == DecisionStatus.draft])
    total_drafts = len(drafts) or 1

    return {
        "portfolio_id": str(portfolio_id),
        "draft_count": draft_count,
        "approved_count": len(approved),
        "executed_count": len(executed),
        "approval_rate_pct": round(len(approved) / total_drafts * 100, 1) if drafts else 0,
        "reference_coverage_pct": round(with_refs / total_drafts * 100, 1) if drafts else 0,
        "rebalance_runs": len(runs),
        "llm_cio_run_pct": round(llm_runs / len(runs) * 100, 1) if runs else 0,
        "agent_mode_hint": "设置 AGENT_MODE=llm 且配置 OPENAI_API_KEY 以提高 LLM 占比",
    }
