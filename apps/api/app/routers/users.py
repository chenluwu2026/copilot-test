from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.profile_service import get_investment_profile, update_investment_profile
from app.services.user_context import get_default_user

router = APIRouter(prefix="/users", tags=["users"])


class RiskBudgetPatch(BaseModel):
    max_drawdown_pct: float | None = None
    max_single_name_pct: float | None = None
    max_sector_pct: float | None = None
    min_cash_pct: float | None = None


class InvestmentProfilePatch(BaseModel):
    markets: list[str] | None = None
    style: list[str] | None = None
    risk_budget: RiskBudgetPatch | None = None
    forbidden_sectors: list[str] | None = None
    forbidden_symbols: list[str] | None = None
    research_max_age_days: int | None = Field(None, ge=1, le=365)
    notes: str | None = None


@router.get("/me")
def get_me(db: Session = Depends(get_db)):
    user = get_default_user(db)
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "investment_profile": get_investment_profile(user),
    }


@router.patch("/me/profile")
def patch_profile(body: InvestmentProfilePatch, db: Session = Depends(get_db)):
    user = get_default_user(db)
    patch = body.model_dump(exclude_none=True)
    if "risk_budget" in patch and patch["risk_budget"] is not None:
        patch["risk_budget"] = {
            k: v for k, v in patch["risk_budget"].items() if v is not None
        }
    profile = update_investment_profile(db, user, patch)
    return {"investment_profile": profile}
