"""决策溯源：关联 Agent 运行、记忆、证据卷宗与质量分。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, Decision
from app.services.decision_service import get_decision
from app.services.review_reminder_service import memories_for_decision


def find_agent_run_for_decision(db: Session, decision_id: UUID) -> dict | None:
    decision = get_decision(db, decision_id)
    if not decision:
        return None
    did = str(decision_id)
    runs = db.scalars(
        select(AgentRun)
        .where(AgentRun.portfolio_id == decision.portfolio_id)
        .order_by(AgentRun.started_at.desc())
        .limit(30)
    ).all()
    for run in runs:
        out = run.output or {}
        ids = [str(x) for x in out.get("decision_ids", [])]
        if did in ids:
            trace = out.get("trace") or {}
            symbol = decision.security.symbol if decision.security else None
            dossier_summary = None
            if symbol and trace.get("dossiers"):
                dossier_summary = trace["dossiers"].get(symbol)
            return {
                "run_id": str(run.id),
                "workflow_name": run.workflow_name,
                "status": run.status.value,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "agent_mode": trace.get("agent_mode") or (run.input_context or {}).get("agent_mode"),
                "cio_mode": trace.get("cio_mode"),
                "cio_decision_mode": trace.get("cio_decision_mode"),
                "memory_query": trace.get("memory_query"),
                "memories": trace.get("memories", []),
                "dossier_summary": dossier_summary,
                "dossiers_trace": trace.get("dossiers"),
                "risk_step": _find_step(trace, "risk_agent"),
                "portfolio_step": _find_step(trace, "portfolio_agent"),
                "valuation_step": _find_step(trace, "valuation_agent"),
                "research_refresh_step": _find_step(trace, "research_refresh"),
            }
    return None


def _find_step(trace: dict, agent: str) -> dict | None:
    for step in trace.get("steps", []):
        if step.get("agent") == agent:
            return step.get("output")
    return None


def get_decision_provenance(db: Session, decision_id: UUID) -> dict:
    decision = get_decision(db, decision_id)
    if not decision:
        raise ValueError("决策不存在")
    cio = decision.cio_summary or {}
    reason = decision.decision_reason or ""
    gate_hints: list[str] = []
    if "[研究闸门]" in reason:
        gate_hints.append(reason.split("[研究闸门]")[-1].split("。")[0].strip())
    if "投资画像禁止项" in reason:
        gate_hints.append("投资画像禁止项")
    if decision.action.value in ("watch",) and "CIO" in reason:
        gate_hints.append("可能被风控或研究闸门降级")

    linked_memories = [
        {"id": str(m.id), "title": m.title, "content": m.content[:200], "active": m.active}
        for m in memories_for_decision(db, decision_id)
    ]
    agent_run = find_agent_run_for_decision(db, decision_id)

    evidence = {
        "grade": cio.get("evidence_grade"),
        "score": cio.get("evidence_score"),
        "issues": cio.get("evidence_issues", []),
    }
    references = [
        {
            "ref_type": r.ref_type.value,
            "ref_id": r.ref_id,
            "excerpt": (r.excerpt or "")[:200],
        }
        for r in (decision.references or [])
    ]

    return {
        "decision_id": str(decision_id),
        "cio_summary": cio,
        "created_by_agent": decision.created_by_agent,
        "gate_hints": gate_hints,
        "linked_memories": linked_memories,
        "agent_run": agent_run,
        "evidence": evidence,
        "references": references,
        "dossier_summary": (agent_run or {}).get("dossier_summary"),
    }
