from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import MemoryEntry, MemoryType, StrategyRule


def search_memory(db: Session, query: str | None = None, limit: int = 10) -> list[MemoryEntry]:
    q = select(MemoryEntry).where(MemoryEntry.active.is_(True))
    if query:
        q = q.where(
            or_(
                MemoryEntry.title.ilike(f"%{query}%"),
                MemoryEntry.content.ilike(f"%{query}%"),
            )
        )
    q = q.order_by(MemoryEntry.confidence.desc()).limit(limit)
    return list(db.scalars(q))


def _tokenize_context(
    symbols: list[str] | None = None,
    sectors: list[str] | None = None,
    keywords: list[str] | None = None,
) -> list[str]:
    tokens: list[str] = []
    for s in symbols or []:
        if not s:
            continue
        tokens.append(s)
        base = s.split(".")[0]
        if base and base != s:
            tokens.append(base)
    for sec in sectors or []:
        if sec:
            tokens.append(sec)
    for kw in keywords or []:
        if kw:
            tokens.append(kw)
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        key = t.lower()
        if key not in seen and len(t) >= 2:
            seen.add(key)
            out.append(t)
    return out


def _memory_match_score(entry: MemoryEntry, tokens: list[str]) -> int:
    hay = " ".join(
        [
            entry.title or "",
            entry.content or "",
            " ".join(entry.tags or []),
        ]
    ).lower()
    return sum(1 for t in tokens if t.lower() in hay)


def search_memory_context(
    db: Session,
    *,
    symbols: list[str] | None = None,
    sectors: list[str] | None = None,
    keywords: list[str] | None = None,
    limit: int = 5,
) -> list[MemoryEntry]:
    """按标的/行业/关键词检索活跃记忆，供 CIO / Portfolio 注入。"""
    tokens = _tokenize_context(symbols, sectors, keywords)
    if not tokens:
        return search_memory(db, "投资", limit=limit)

    rows = list(
        db.scalars(
            select(MemoryEntry)
            .where(MemoryEntry.active.is_(True))
            .order_by(MemoryEntry.confidence.desc())
            .limit(50)
        )
    )
    ranked = sorted(rows, key=lambda m: _memory_match_score(m, tokens), reverse=True)
    matched = [m for m in ranked if _memory_match_score(m, tokens) > 0]
    if matched:
        return matched[:limit]
    return search_memory(db, " ".join(tokens[:3]), limit=limit)


def list_memories(db: Session, active_only: bool = False, pending: bool | None = None) -> list:
    q = select(MemoryEntry).order_by(MemoryEntry.created_at.desc())
    if active_only:
        q = q.where(MemoryEntry.active.is_(True))
    if pending is not None:
        q = q.where(MemoryEntry.pending.is_(pending))
    rows = db.scalars(q).all()
    return [_mem_dict(m) for m in rows]


def _mem_dict(m: MemoryEntry) -> dict:
    return {
        "id": str(m.id),
        "memory_type": m.memory_type.value,
        "title": m.title,
        "content": m.content,
        "tags": m.tags,
        "confidence": float(m.confidence),
        "active": m.active,
        "pending": m.pending,
        "evidence_decision_ids": m.evidence_decision_ids,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def activate_memory(db: Session, memory_id: UUID, create_rule: bool = True) -> MemoryEntry:
    m = db.get(MemoryEntry, memory_id)
    if not m:
        raise ValueError("记忆不存在")
    m.active = True
    m.pending = False
    if create_rule and m.memory_type in (MemoryType.rule, MemoryType.anti_pattern):
        code = f"mem_{str(m.id)[:8]}"
        existing = db.scalar(select(StrategyRule).where(StrategyRule.rule_code == code))
        if not existing:
            machine = {"type": "note", "memory_id": str(m.id)}
            if m.memory_type == MemoryType.anti_pattern:
                machine = {
                    "type": "ban_action",
                    "action": "add",
                    "memory_id": str(m.id),
                    "sectors": m.tags or [],
                }
            elif m.memory_type == MemoryType.lesson:
                machine = {"type": "require_extra_review", "memory_id": str(m.id)}
            db.add(
                StrategyRule(
                    rule_code=code,
                    natural_language=m.content,
                    machine_check=machine,
                    source_memory_id=m.id,
                )
            )
    db.commit()
    db.refresh(m)
    return m


def create_memory(
    db: Session,
    memory_type: MemoryType,
    title: str,
    content: str,
    tags: list | None = None,
    evidence_decision_ids: list | None = None,
    active: bool = False,
) -> MemoryEntry:
    m = MemoryEntry(
        memory_type=memory_type,
        title=title,
        content=content,
        tags=tags or [],
        evidence_decision_ids=evidence_decision_ids or [],
        active=active,
        pending=not active,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m
