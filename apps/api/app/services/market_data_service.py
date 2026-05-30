"""行情同步：写入 market_bars 并更新 securities.last_price。"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BarInterval, DataSyncJob, Market, MarketBar, Security, SyncJobStatus, SyncJobType
from app.services.portfolio_service import refresh_portfolio_valuation


def _fetch_bars(symbol: str, market: str, start: date, end: date, base_price: float):
    if settings.data_provider == "mock":
        from app.data_connectors import mock_provider

        return mock_provider.fetch_daily_bars(symbol, market, start, end, base_price)
    from app.data_connectors import akshare_provider

    try:
        return akshare_provider.fetch_daily_bars(symbol, market, start, end)
    except Exception:
        from app.data_connectors import mock_provider

        return mock_provider.fetch_daily_bars(symbol, market, start, end, base_price)


def sync_security_bars(
    db: Session,
    security: Security,
    days: int = 120,
) -> int:
    end = date.today()
    start = end - timedelta(days=days)
    market = security.market.value
    base = float(security.last_price or 100)
    bars = _fetch_bars(security.symbol, market, start, end, base)
    count = 0
    for b in bars:
        existing = db.scalar(
            select(MarketBar).where(
                MarketBar.security_id == security.id,
                MarketBar.bar_date == b["bar_date"],
                MarketBar.interval == BarInterval.d1,
            )
        )
        if existing:
            existing.open = Decimal(str(b["open"]))
            existing.high = Decimal(str(b["high"]))
            existing.low = Decimal(str(b["low"]))
            existing.close = Decimal(str(b["close"]))
            existing.volume = Decimal(str(b["volume"]))
            existing.turnover = Decimal(str(b.get("turnover") or 0))
            if b.get("turnover_rate") is not None:
                existing.turnover_rate = Decimal(str(b["turnover_rate"]))
        else:
            db.add(
                MarketBar(
                    security_id=security.id,
                    bar_date=b["bar_date"],
                    interval=BarInterval.d1,
                    open=Decimal(str(b["open"])),
                    high=Decimal(str(b["high"])),
                    low=Decimal(str(b["low"])),
                    close=Decimal(str(b["close"])),
                    volume=Decimal(str(b["volume"])),
                    turnover=Decimal(str(b.get("turnover") or 0)),
                    turnover_rate=Decimal(str(b.get("turnover_rate") or 0)),
                )
            )
            count += 1
    if bars:
        latest = max(bars, key=lambda x: x["bar_date"])
        security.last_price = Decimal(str(latest["close"]))
    db.commit()
    return count


def sync_quotes(
    db: Session,
    security_ids: list[UUID] | None = None,
    days: int = 120,
    portfolio_id: UUID | None = None,
) -> dict:
    job = DataSyncJob(
        job_type=SyncJobType.quotes,
        params={"days": days, "security_ids": [str(s) for s in security_ids] if security_ids else None},
    )
    db.add(job)
    db.flush()

    if security_ids:
        securities = [db.get(Security, sid) for sid in security_ids]
        securities = [s for s in securities if s]
    else:
        securities = list(db.scalars(select(Security).where(Security.is_active.is_(True))))

    total_bars = 0
    errors = []
    for sec in securities:
        try:
            total_bars += sync_security_bars(db, sec, days)
        except Exception as e:
            errors.append({"symbol": sec.symbol, "error": str(e)})

    if portfolio_id:
        refresh_portfolio_valuation(db, portfolio_id)

    job.status = SyncJobStatus.success if not errors else SyncJobStatus.failed
    job.result = {"bars_inserted": total_bars, "securities": len(securities), "errors": errors}
    job.error_message = "; ".join(e["error"] for e in errors[:3]) if errors else None
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"job_id": str(job.id), **job.result}


def get_bars(db: Session, security_id: UUID, days: int = 90) -> list[dict]:
    since = date.today() - timedelta(days=days)
    rows = db.scalars(
        select(MarketBar)
        .where(
            MarketBar.security_id == security_id,
            MarketBar.bar_date >= since,
        )
        .order_by(MarketBar.bar_date)
    ).all()
    return [
        {
            "bar_date": r.bar_date.isoformat(),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": float(r.volume),
            "turnover_rate": float(r.turnover_rate) if r.turnover_rate else None,
        }
        for r in rows
    ]


def compute_momentum_from_bars(db: Session, security_id: UUID, window: int = 20) -> float | None:
    bars = get_bars(db, security_id, days=window + 5)
    if len(bars) < 2:
        return None
    first = bars[0]["close"]
    last = bars[-1]["close"]
    if first <= 0:
        return None
    return round((last - first) / first * 100, 2)
