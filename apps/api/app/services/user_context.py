from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User


def get_default_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == settings.default_user_email))
    if user:
        return user
    user = User(
        email=settings.default_user_email,
        display_name="演示用户",
        investment_profile={
            "markets": ["CN_A", "HK"],
            "style": ["fundamental", "quality_growth"],
        },
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
