"""投资画像：默认结构、读取与更新，并同步组合风控参数。"""
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Portfolio, User

DEFAULT_INVESTMENT_PROFILE: dict = {
    "markets": ["CN_A", "HK"],
    "style": ["fundamental", "quality_growth"],
    "risk_budget": {
        "max_drawdown_pct": 15,
        "max_single_name_pct": 10,
        "max_sector_pct": 25,
        "min_cash_pct": 5,
    },
    "forbidden_sectors": [],
    "forbidden_symbols": [],
    "research_max_age_days": 30,
    "notes": "",
}


def normalize_profile(raw: dict | None) -> dict:
    base = deepcopy(DEFAULT_INVESTMENT_PROFILE)
    if not raw:
        return base
    for key, value in raw.items():
        if value is None:
            continue
        if key == "risk_budget" and isinstance(value, dict):
            base["risk_budget"] = {**base["risk_budget"], **value}
        else:
            base[key] = value
    return base


def get_investment_profile(user: User) -> dict:
    return normalize_profile(user.investment_profile)


def _sync_portfolio_risk_limits(db: Session, user: User, profile: dict) -> None:
    rb = profile.get("risk_budget") or {}
    mapping = {
        "max_single_name_pct": rb.get("max_single_name_pct"),
        "max_sector_pct": rb.get("max_sector_pct"),
        "min_cash_pct": rb.get("min_cash_pct"),
    }
    portfolios = db.scalars(select(Portfolio).where(Portfolio.user_id == user.id)).all()
    for p in portfolios:
        limits = dict(p.risk_limits or {})
        for k, v in mapping.items():
            if v is not None:
                limits[k] = v
        p.risk_limits = limits


def update_investment_profile(db: Session, user: User, patch: dict) -> dict:
    profile = normalize_profile(user.investment_profile)
    for key, value in patch.items():
        if value is None:
            continue
        if key == "risk_budget" and isinstance(value, dict):
            profile["risk_budget"] = {**profile["risk_budget"], **value}
        else:
            profile[key] = value
    user.investment_profile = profile
    _sync_portfolio_risk_limits(db, user, profile)
    db.commit()
    db.refresh(user)
    return profile


def user_is_forbidden(profile: dict, *, symbol: str | None = None, sector: str | None = None) -> bool:
    if symbol and symbol in (profile.get("forbidden_symbols") or []):
        return True
    if sector and sector in (profile.get("forbidden_sectors") or []):
        return True
    return False
