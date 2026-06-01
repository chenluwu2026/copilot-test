import json
from pathlib import Path
from uuid import UUID

import jsonschema
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import (
    Decision,
    DecisionAction,
    DecisionAssumption,
    DecisionReference,
    DecisionStatus,
    ReferenceType,
    UserFeedback,
)


def _load_schema(name: str) -> dict:
    path = Path(settings.schemas_dir) / name
    return json.loads(path.read_text())


def validate_decision_payload(cio_summary: dict) -> None:
    schema = _load_schema("decision_order.schema.json")
    jsonschema.validate(instance=cio_summary, schema=schema)


def list_decisions(
    db: Session,
    portfolio_id: UUID | None = None,
    status: DecisionStatus | None = None,
    security_id: UUID | None = None,
) -> list[Decision]:
    q = select(Decision).options(
        joinedload(Decision.security),
        joinedload(Decision.assumptions),
        joinedload(Decision.references),
    )
    if portfolio_id:
        q = q.where(Decision.portfolio_id == portfolio_id)
    if status:
        q = q.where(Decision.status == status)
    if security_id:
        q = q.where(Decision.security_id == security_id)
    q = q.order_by(Decision.created_at.desc())
    return list(db.scalars(q).unique())


def get_decision(db: Session, decision_id: UUID) -> Decision | None:
    return db.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(
            joinedload(Decision.security),
            joinedload(Decision.assumptions),
            joinedload(Decision.references),
            joinedload(Decision.feedbacks),
        )
    )


def create_decision(
    db: Session,
    portfolio_id: UUID,
    security_id: UUID,
    action: DecisionAction,
    decision_reason: str,
    current_weight_pct: float,
    target_weight_pct: float,
    main_risks: list[str],
    review_conditions: list[str],
    assumptions: list[dict],
    references: list[dict] | None = None,
    confidence_grade: str | None = None,
    holding_period: str | None = None,
    cio_summary: dict | None = None,
    created_by_agent: str = "human",
    evidence_meta: dict | None = None,
) -> Decision:
    if cio_summary:
        validate_decision_payload(cio_summary)
        if evidence_meta:
            cio_summary = {**cio_summary, **evidence_meta}

    delta = target_weight_pct - current_weight_pct
    decision = Decision(
        portfolio_id=portfolio_id,
        security_id=security_id,
        action=action,
        current_weight_pct=current_weight_pct,
        target_weight_pct=target_weight_pct,
        delta_weight_pct=delta,
        decision_reason=decision_reason,
        main_risks=main_risks,
        review_conditions=review_conditions,
        confidence_grade=confidence_grade,
        holding_period=holding_period,
        cio_summary=cio_summary or {},
        created_by_agent=created_by_agent,
        status=DecisionStatus.draft,
    )
    db.add(decision)
    db.flush()

    for a in assumptions:
        db.add(
            DecisionAssumption(
                decision_id=decision.id,
                assumption_text=a["text"],
                measurable=a.get("measurable", False),
                metric_key=a.get("metric_key"),
                target_value=a.get("target_value"),
                deadline=a.get("deadline"),
            )
        )
    for r in references or []:
        db.add(
            DecisionReference(
                decision_id=decision.id,
                ref_type=ReferenceType(r["ref_type"]),
                ref_id=r.get("ref_id"),
                excerpt=r.get("excerpt"),
            )
        )
    db.commit()
    return get_decision(db, decision.id)


def update_decision_status(db: Session, decision_id: UUID, status: DecisionStatus) -> Decision:
    decision = db.get(Decision, decision_id)
    if not decision:
        raise ValueError("决策不存在")
    allowed = {
        DecisionStatus.draft: {DecisionStatus.approved, DecisionStatus.cancelled},
        DecisionStatus.approved: {DecisionStatus.executed, DecisionStatus.cancelled},
    }
    if status not in allowed.get(decision.status, set()):
        raise ValueError(f"不能从 {decision.status} 转为 {status}")
    decision.status = status
    db.commit()
    return get_decision(db, decision_id)


def add_feedback(
    db: Session,
    user_id: UUID,
    decision_id: UUID,
    rating: int,
    correction: str | None = None,
    tags: list[str] | None = None,
) -> UserFeedback:
    fb = UserFeedback(
        user_id=user_id,
        decision_id=decision_id,
        rating=rating,
        correction=correction,
        tags=tags or [],
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
