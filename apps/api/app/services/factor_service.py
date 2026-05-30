"""Factor Agent：结合真实 K 线动量与研究评级。"""
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResearchRating, ResearchView, Security
from app.services.data_quality_service import symbol_has_fresh_bars
from app.services.market_data_service import compute_momentum_from_bars


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
        momentum = compute_momentum_from_bars(db, sid, window=20)
        has_real_bars = momentum is not None
        if momentum is None:
            momentum = _pseudo_momentum(sec.symbol, price)
        data_complete = has_real_bars and symbol_has_fresh_bars(db, sid)
        warnings = []
        if not data_complete:
            warnings.append("行情数据不完整或过期，动量为估算值")
        crowding = 30 + (growth - 50) * 0.5
        if crowding > 60:
            warnings.append("拥挤度偏高，注意回调")
        composite = (momentum * 0.25 + value * 0.2 + quality * 0.25 + growth * 0.3)
        results.append(
            {
                "security_id": str(sid),
                "symbol": sec.symbol,
                "name": sec.name,
                "data_complete": data_complete,
                "factors": {
                    "momentum": round(momentum, 1),
                    "value": round(value, 1),
                    "quality": round(quality, 1),
                    "growth": round(growth, 1),
                    "crowding": round(crowding, 1),
                    "composite": round(composite, 1),
                },
                "warnings": warnings,
            }
        )
    return sorted(results, key=lambda x: x["factors"]["composite"], reverse=True)
