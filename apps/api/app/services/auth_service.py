"""简易 JWT 登录（个人部署单用户）。"""
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User


def create_access_token(user_id: str, email: str) -> str:
    secret = settings.jwt_secret or settings.api_key or "aims-dev-secret-change-me"
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def login(db: Session, email: str, password: str) -> dict:
    if settings.auth_password and password != settings.auth_password:
        raise ValueError("口令错误")
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise ValueError("用户不存在")
    token = create_access_token(str(user.id), user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
    }
