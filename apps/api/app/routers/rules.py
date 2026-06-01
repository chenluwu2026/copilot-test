from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StrategyRule

router = APIRouter(prefix="/rules", tags=["rules"])


class StrategyRuleCreate(BaseModel):
    rule_code: str
    natural_language: str
    machine_check: dict = {}
    active: bool = True


class StrategyRuleUpdate(BaseModel):
    natural_language: str | None = None
    machine_check: dict | None = None
    active: bool | None = None


def _rule_dict(r: StrategyRule) -> dict:
    return {
        "id": str(r.id),
        "rule_code": r.rule_code,
        "natural_language": r.natural_language,
        "machine_check": r.machine_check or {},
        "active": r.active,
        "source_memory_id": str(r.source_memory_id) if r.source_memory_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("")
def list_rules(active_only: bool = False, db: Session = Depends(get_db)):
    q = select(StrategyRule).order_by(StrategyRule.created_at.desc())
    if active_only:
        q = q.where(StrategyRule.active.is_(True))
    return [_rule_dict(r) for r in db.scalars(q).all()]


@router.post("")
def create_rule(body: StrategyRuleCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(StrategyRule).where(StrategyRule.rule_code == body.rule_code))
    if existing:
        raise HTTPException(400, "rule_code 已存在")
    r = StrategyRule(
        rule_code=body.rule_code,
        natural_language=body.natural_language,
        machine_check=body.machine_check,
        active=body.active,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _rule_dict(r)


@router.patch("/{rule_id}")
def update_rule(rule_id: UUID, body: StrategyRuleUpdate, db: Session = Depends(get_db)):
    r = db.get(StrategyRule, rule_id)
    if not r:
        raise HTTPException(404, "规则不存在")
    if body.natural_language is not None:
        r.natural_language = body.natural_language
    if body.machine_check is not None:
        r.machine_check = body.machine_check
    if body.active is not None:
        r.active = body.active
    db.commit()
    db.refresh(r)
    return _rule_dict(r)


@router.delete("/{rule_id}")
def delete_rule(rule_id: UUID, db: Session = Depends(get_db)):
    r = db.get(StrategyRule, rule_id)
    if not r:
        raise HTTPException(404, "规则不存在")
    db.delete(r)
    db.commit()
    return {"deleted": str(rule_id)}
