"""复盘质量清单：假设验证、引用链、记忆可激活。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Decision, DecisionOutcome, DecisionReference, MemoryEntry


def build_review_quality(
    db: Session,
    decision_id: UUID,
    *,
    memory_id: str | None = None,
) -> dict:
    decision = db.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(
            joinedload(Decision.assumptions),
            joinedload(Decision.references),
            joinedload(Decision.security),
        )
    )
    if not decision:
        raise ValueError("决策不存在")

    outcome = db.scalar(
        select(DecisionOutcome).where(DecisionOutcome.decision_id == decision_id)
    )

    ref_types = {r.ref_type.value for r in decision.references}
    chain_ok = bool(
        ref_types & {"research_report", "research", "structured_event", "news"}
    )
    assumption_items = []
    if outcome and outcome.assumption_results:
        for ar in outcome.assumption_results:
            assumption_items.append(
                {
                    "text": ar.get("assumption_text", ""),
                    "result": ar.get("result", "open"),
                    "evidence": ar.get("evidence") or ar.get("measurable_evidence", ""),
                }
            )
    else:
        for a in decision.assumptions:
            assumption_items.append(
                {"text": a.assumption_text, "result": "pending", "evidence": ""}
            )

    validated = sum(1 for x in assumption_items if x["result"] == "validated")
    invalidated = sum(1 for x in assumption_items if x["result"] == "invalidated")
    memory_ready = False
    pending_memory = False
    if memory_id:
        mem = db.get(MemoryEntry, memory_id)
        if mem:
            pending_memory = mem.pending
            memory_ready = not mem.pending or mem.active

    checklist = [
        {
            "item": "假设已评估",
            "ok": outcome is not None and len(assumption_items) > 0,
            "detail": f"已验证 {validated} / 证伪 {invalidated} / 共 {len(assumption_items)}",
        },
        {
            "item": "引用链完整",
            "ok": chain_ok and len(decision.references) >= 1,
            "detail": f"引用类型: {', '.join(sorted(ref_types)) or '无'}",
        },
        {
            "item": "复盘摘要已生成",
            "ok": bool(outcome and outcome.outcome_summary),
            "detail": (outcome.outcome_summary or "")[:120] if outcome else "未复盘",
        },
        {
            "item": "教训可沉淀记忆",
            "ok": memory_id is not None or bool(outcome and outcome.what_went_wrong),
            "detail": "已生成待激活记忆" if memory_id else "无自动教训",
        },
        {
            "item": "记忆可激活",
            "ok": memory_ready or (memory_id is None and not pending_memory),
            "detail": "待用户在复盘页激活" if pending_memory else "—",
        },
    ]

    ok_count = sum(1 for c in checklist if c["ok"])
    return {
        "decision_id": str(decision_id),
        "symbol": decision.security.symbol if decision.security else "",
        "checklist": checklist,
        "assumption_results": assumption_items,
        "quality_pct": round(ok_count / len(checklist) * 100) if checklist else 0,
        "memory_id": memory_id,
    }
