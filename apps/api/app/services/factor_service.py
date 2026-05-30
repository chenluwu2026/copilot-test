"""Factor Agent：基于现价与研究评级的简化因子得分（MVP）。"""
import hashlib
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchRating, ResearchView, Security


RATING_SCORE = {
    ResearchRating.strong_buy: 90,
    ResearchRating.buy: 75,
    ResearchRating.hold: 50,
    ResearchRating.neutral: 50,
    ResearchRating.reduce: 35,
    ResearchRating.sell: 20,
}


def _pseudo_momentum(symbol: str, price: float) -> float:
    """无历史行情时用符号哈希模拟动量，便于演示。"""
    h = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    return 40 + (h % 40) + (price % 50) * 0.1


def compute_factors(db: Session, security_ids: list) -> list[dict]:
    results = []
    for sid in security_ids:
        sec = db.get(Security, sid)
        if not sec:
            continue
        price = float(sec.last_price or 100)
        view = db.scalar(
            select(ResearchView)
            .where(ResearchView.security_id == sid)
            .order_by(ResearchView.version.desc())
            .limit(1)
        )
        quality = 70 if sec.sector in ("食品饮料", "银行") else 55
        value = 65 if price < 100 else 45
        growth = RATING_SCORE.get(view.rating, 50) if view else 50
        momentum = _pseudo_momentum(sec.symbol, price)
        crowding = 30 + (growth - 50) * 0.5
        composite = (momentum * 0.25 + value * 0.2 + quality * 0.25 + growth * 0.3)
        results.append(
            {
                "security_id": str(sid),
                "symbol": sec.symbol,
                "name": sec.name,
                "factors": {
                    "momentum": round(momentum, 1),
                    "value": round(value, 1),
                    "quality": round(quality, 1),
                    "growth": round(growth, 1),
                    "crowding": round(crowding, 1),
                    "composite": round(composite, 1),
                },
                "warnings": (
                    ["拥挤度偏高，注意回调"] if crowding > 60 else []
                ),
            }
        )
    return sorted(results, key=lambda x: x["factors"]["composite"], reverse=True)
