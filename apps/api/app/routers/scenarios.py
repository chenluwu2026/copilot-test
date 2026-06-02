from fastapi import APIRouter, HTTPException

from app.services.macro_scenario_service import get_scenario, list_macro_scenarios

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios():
    return {"scenarios": list_macro_scenarios()}


@router.get("/{scenario_id}")
def get_one(scenario_id: str):
    s = get_scenario(scenario_id)
    if not s:
        raise HTTPException(404, "情景不存在")
    return s
