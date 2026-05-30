from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MemoryType
from app.services.memory_service import activate_memory, create_memory, list_memories, search_memory

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCreate(BaseModel):
    memory_type: str
    title: str
    content: str
    tags: list[str] = []
    active: bool = False


@router.get("")
def list_all(pending: bool | None = None, active_only: bool = False, db: Session = Depends(get_db)):
    return list_memories(db, active_only=active_only, pending=pending)


@router.get("/search")
def search(q: str, db: Session = Depends(get_db)):
    rows = search_memory(db, q)
    return [{"id": str(m.id), "title": m.title, "content": m.content} for m in rows]


@router.post("")
def create(body: MemoryCreate, db: Session = Depends(get_db)):
    m = create_memory(
        db,
        MemoryType(body.memory_type),
        body.title,
        body.content,
        body.tags,
        active=body.active,
    )
    return {"id": str(m.id)}


@router.post("/{memory_id}/activate")
def activate(memory_id: UUID, db: Session = Depends(get_db)):
    try:
        m = activate_memory(db, memory_id)
        return {"id": str(m.id), "active": m.active}
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
