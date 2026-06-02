"""宏观情景库（静态 JSON，finance-os 风格）。"""
import json
from pathlib import Path

_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "macro_scenarios.json"


def list_macro_scenarios() -> list[dict]:
    if not _SCENARIOS_PATH.exists():
        return _default_scenarios()
    return json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))


def get_scenario(scenario_id: str) -> dict | None:
    for s in list_macro_scenarios():
        if s.get("id") == scenario_id:
            return s
    return None


def _default_scenarios() -> list[dict]:
    return [
        {
            "id": "soft_landing",
            "name": "软着陆",
            "description": "通胀回落、增长温和，权益偏多、债券中性",
            "tilts": {"equity": 0.1, "bond": 0.0, "cash": -0.05},
        },
        {
            "id": "recession",
            "name": "衰退压力",
            "description": "盈利下修、波动上升，降权益、增现金",
            "tilts": {"equity": -0.15, "bond": 0.05, "cash": 0.1},
        },
    ]
