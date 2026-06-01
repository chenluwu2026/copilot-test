from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import login

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    email: str
    password: str = ""


@router.post("/login")
def auth_login(body: LoginBody, db: Session = Depends(get_db)):
    try:
        return login(db, body.email.strip(), body.password)
    except ValueError as e:
        raise HTTPException(401, str(e)) from e
