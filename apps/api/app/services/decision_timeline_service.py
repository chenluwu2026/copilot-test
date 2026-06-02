"""决策状态时间线与 Agent 运行关联。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AgentRun, Decision, DecisionOutcome, DecisionStatus
from app.services.decision_service import get_decision


def get_decision_timeline(db: Session, decision_id: UUID) -> dict:
    d = get_decision(db, decision_id)
    if not d:
        raise ValueError("决策不存在")

    events: list[dict] = [
        {
            "key": "created",
            "label": "创建决策",
            "status": "draft",
            "at": d.created_at.isoformat() if d.created_at else None,
            "detail": f"来源: {d.created_by_agent}",
        }
    ]

    if d.status in (
        DecisionStatus.approved,
        DecisionStatus.executed,
    ):
        events.append(
            {
                "key": "approved",
                "label": "批准",
                "status": "approved",
                "at": None,
                "detail": "人工或系统批准",
            }
        )

    if d.status == DecisionStatus.executed and d.executed_at:
        events.append(
            {
                "key": "executed",
                "label": "执行成交",
                "status": "executed",
                "at": d.executed_at.isoformat(),
                "detail": "模拟交易已记录",
            }
        )

    outcome = db.scalar(
        select(DecisionOutcome).where(DecisionOutcome.decision_id == decision_id)
    )
    if outcome and outcome.outcome_status.value != "open":
        events.append(
            {
                "key": "reviewed",
                "label": "已复盘",
                "status": "reviewed",
                "at": outcome.closed_at.isoformat() if outcome.closed_at else None,
                "detail": outcome.outcome_summary or "复盘完成",
            }
        )

    agent_runs: list[dict] = []
    did = str(decision_id)
    for run in db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(50)):
        ids = (run.output or {}).get("decision_ids") or []
        if did in [str(x) for x in ids]:
            agent_runs.append(
                {
                    "run_id": str(run.id),
                    "workflow_name": run.workflow_name,
                    "status": run.status.value,
                    "trigger": run.trigger,
                    "cio_mode": (run.output or {}).get("cio_mode"),
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                }
            )

    return {
        "decision_id": did,
        "current_status": d.status.value,
        "events": events,
        "agent_runs": agent_runs,
    }
