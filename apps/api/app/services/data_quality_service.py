"""数据新鲜度与完整性检查。"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Filing, FinancialReport, MarketBar, Security


def get_data_quality(db: Session) -> dict:
    """全库数据质量概览，供数据中心与 Factor Agent 使用。"""
    securities = list(db.scalars(select(Security).where(Security.is_active.is_(True))))
    stale_days = settings.data_stale_days
    cutoff = date.today() - timedelta(days=stale_days)
    per_symbol = []
    with_bars = 0
    stale_quotes = 0
    no_bars = 0

    for sec in securities:
        last_bar = db.scalar(
            select(func.max(MarketBar.bar_date)).where(MarketBar.security_id == sec.id)
        )
        filing_count = db.scalar(
            select(func.count()).select_from(Filing).where(Filing.security_id == sec.id)
        )
        fin_count = db.scalar(
            select(func.count())
            .select_from(FinancialReport)
            .where(FinancialReport.security_id == sec.id)
        )
        if last_bar is None:
            no_bars += 1
            freshness = "missing"
        elif last_bar < cutoff:
            stale_quotes += 1
            freshness = "stale"
        else:
            with_bars += 1
            freshness = "ok"

        per_symbol.append(
            {
                "symbol": sec.symbol,
                "name": sec.name,
                "market": sec.market.value,
                "last_bar_date": last_bar.isoformat() if last_bar else None,
                "freshness": freshness,
                "filing_count": int(filing_count or 0),
                "financial_report_count": int(fin_count or 0),
            }
        )

    total = len(securities) or 1
    return {
        "summary": {
            "securities": len(securities),
            "with_fresh_quotes": with_bars,
            "stale_quotes": stale_quotes,
            "missing_quotes": no_bars,
            "coverage_pct": round(with_bars / total * 100, 1),
            "stale_threshold_days": stale_days,
            "data_provider": settings.data_provider,
        },
        "symbols": sorted(per_symbol, key=lambda x: x["symbol"]),
    }


def symbol_has_fresh_bars(db: Session, security_id, stale_days: int | None = None) -> bool:
    days = stale_days or settings.data_stale_days
    cutoff = date.today() - timedelta(days=days)
    last_bar = db.scalar(
        select(func.max(MarketBar.bar_date)).where(MarketBar.security_id == security_id)
    )
    return last_bar is not None and last_bar >= cutoff
