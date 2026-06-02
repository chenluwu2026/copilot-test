from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DecisionAction, DecisionStatus
from app.schemas_api import DecisionCreate, DecisionExecute, DecisionStatusUpdate, FeedbackCreate
from app.services import decision_service as ds
from app.services import portfolio_service as ps
from app.services.decision_provenance_service import get_decision_provenance
from app.services.decision_timeline_service import get_decision_timeline
from app.services.user_context import get_default_user

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _decision_to_dict(d) -> dict:
    return {
        "id": str(d.id),
        "portfolio_id": str(d.portfolio_id),
        "security_id": str(d.security_id),
        "symbol": d.security.symbol,
        "name": d.security.name,
        "action": d.action.value,
        "current_weight_pct": float(d.current_weight_pct),
        "target_weight_pct": float(d.target_weight_pct),
        "delta_weight_pct": float(d.delta_weight_pct),
        "status": d.status.value,
        "confidence_grade": d.confidence_grade,
        "holding_period": d.holding_period,
        "decision_reason": d.decision_reason,
        "main_risks": d.main_risks,
        "review_conditions": d.review_conditions,
        "cio_summary": d.cio_summary,
        "evidence_grade": (d.cio_summary or {}).get("evidence_grade"),
        "evidence_score": (d.cio_summary or {}).get("evidence_score"),
        "created_by_agent": d.created_by_agent,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "executed_at": d.executed_at.isoformat() if d.executed_at else None,
        "assumptions": [
            {
                "id": str(a.id),
                "text": a.assumption_text,
                "measurable": a.measurable,
                "metric_key": a.metric_key,
                "deadline": a.deadline.isoformat() if a.deadline else None,
            }
            for a in d.assumptions
        ],
        "references": [
            {
                "id": str(r.id),
                "ref_type": r.ref_type.value,
                "ref_id": r.ref_id,
                "excerpt": r.excerpt,
            }
            for r in d.references
        ],
        "feedbacks": [
            {
                "rating": f.rating,
                "correction": f.correction,
                "tags": f.tags,
            }
            for f in (d.feedbacks or [])
        ],
    }


@router.get("")
def list_decisions(
    portfolio_id: UUID | None = None,
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    st = DecisionStatus(status) if status else None
    items = ds.list_decisions(db, portfolio_id, st)
    return [_decision_to_dict(d) for d in items]


@router.get("/{decision_id}/timeline")
def decision_timeline(decision_id: UUID, db: Session = Depends(get_db)):
    try:
        return get_decision_timeline(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{decision_id}/provenance")
def decision_provenance(decision_id: UUID, db: Session = Depends(get_db)):
    try:
        return get_decision_provenance(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{decision_id}")
def get_decision(decision_id: UUID, db: Session = Depends(get_db)):
    d = ds.get_decision(db, decision_id)
    if not d:
        raise HTTPException(404, "决策不存在")
    return _decision_to_dict(d)


@router.post("")
def create_decision(body: DecisionCreate, db: Session = Depends(get_db)):
    try:
        d = ds.create_decision(
            db,
            body.portfolio_id,
            body.security_id,
            DecisionAction(body.action),
            body.decision_reason,
            body.current_weight_pct,
            body.target_weight_pct,
            body.main_risks,
            body.review_conditions,
            [a.model_dump() for a in body.assumptions],
            [r.model_dump() for r in body.references],
            body.confidence_grade,
            body.holding_period,
            body.cio_summary,
        )
        return _decision_to_dict(d)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.patch("/{decision_id}/status")
def update_status(decision_id: UUID, body: DecisionStatusUpdate, db: Session = Depends(get_db)):
    try:
        d = ds.update_decision_status(db, decision_id, DecisionStatus(body.status))
        return _decision_to_dict(d)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{decision_id}/execute")
def execute_decision(decision_id: UUID, body: DecisionExecute, db: Session = Depends(get_db)):
    from decimal import Decimal

    try:
        price = Decimal(str(body.price)) if body.price else None
        trade = ps.execute_decision(db, decision_id, price)
        if trade is None:
            return {
                "trade_id": None,
                "status": "executed",
                "message": "已确认，无需成交",
            }
        return {"trade_id": str(trade.id), "status": "executed"}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{decision_id}/feedback")
def add_feedback(decision_id: UUID, body: FeedbackCreate, db: Session = Depends(get_db)):
    user = get_default_user(db)
    fb = ds.add_feedback(db, user.id, decision_id, body.rating, body.correction, body.tags)
    return {"id": str(fb.id), "rating": fb.rating}
