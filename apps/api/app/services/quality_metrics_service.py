"""决策质量与使用成效指标（路线图验收）。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, Decision, DecisionLedger, DecisionLedgerStatus, DecisionReference, DecisionStatus
from app.services.decision_ledger_service import gate_failure_stats


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

    pipeline_ledgers = list(
        db.scalars(
            select(DecisionLedger)
            .where(
                DecisionLedger.portfolio_id == portfolio_id,
                DecisionLedger.run_id.isnot(None),
            )
            .order_by(DecisionLedger.created_at.desc())
            .limit(200)
        )
    )
    fm_ledgers = [l for l in pipeline_ledgers if (l.run_id or "").startswith("fm-")]
    pl_total = len(fm_ledgers) or 1
    pl_rejected = len([l for l in fm_ledgers if l.status == DecisionLedgerStatus.risk_rejected])
    pipeline_rejection_rate_pct = round(pl_rejected / pl_total * 100, 1) if fm_ledgers else 0.0

    weight_drift_pct = 0.0
    drift_samples = 0
    for ledger in fm_ledgers[:50]:
        prop = ledger.proposal_json or {}
        tw = prop.get("target_weight_pct")
        cw = prop.get("current_weight_pct")
        if tw is not None and cw is not None:
            weight_drift_pct += abs(float(tw) - float(cw))
            drift_samples += 1
    avg_weight_drift_pct = round(weight_drift_pct / drift_samples, 2) if drift_samples else 0.0

    gate_stats = gate_failure_stats(db, portfolio_id, limit=200)
    top_gate = next(iter(gate_stats), None)

    drift_alerts: list[dict] = []
    if pipeline_rejection_rate_pct >= 40 and fm_ledgers:
        drift_alerts.append(
            {
                "level": "warning",
                "code": "high_pipeline_rejection",
                "message": f"近批次流水线拒单率 {pipeline_rejection_rate_pct}%，建议检查风控阈值或候选池质量",
            }
        )
    if avg_weight_drift_pct >= 8:
        drift_alerts.append(
            {
                "level": "info",
                "code": "weight_drift",
                "message": f"近期目标与当前权重平均偏离 {avg_weight_drift_pct}%，调仓幅度较大",
            }
        )
    if top_gate and gate_stats[top_gate] >= 3:
        drift_alerts.append(
            {
                "level": "warning",
                "code": "gate_failure_cluster",
                "message": f"风控门 {top_gate} 近期失败 {gate_stats[top_gate]} 次，优先排查该约束",
            }
        )

    return {
        "portfolio_id": str(portfolio_id),
        "draft_count": draft_count,
        "approved_count": len(approved),
        "executed_count": len(executed),
        "approval_rate_pct": round(len(approved) / total_drafts * 100, 1) if drafts else 0,
        "reference_coverage_pct": round(with_refs / total_drafts * 100, 1) if drafts else 0,
        "rebalance_runs": len(runs),
        "llm_cio_run_pct": round(llm_runs / len(runs) * 100, 1) if runs else 0,
        "pipeline_rejection_rate_pct": pipeline_rejection_rate_pct,
        "avg_weight_drift_pct": avg_weight_drift_pct,
        "gate_failure_stats": gate_stats,
        "drift_alerts": drift_alerts,
        "agent_mode_hint": "设置 AGENT_MODE=llm 且配置 OPENAI_API_KEY 以提高 LLM 占比",
    }
