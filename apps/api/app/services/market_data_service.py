"""行情同步：写入 market_bars 并更新 securities.last_price。"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from time import sleep
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BarInterval, DataSyncJob, MarketBar, Security, SyncJobStatus, SyncJobType
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


def get_last_bar_date(db: Session, security_id: UUID) -> date | None:
    return db.scalar(
        select(func.max(MarketBar.bar_date)).where(MarketBar.security_id == security_id)
    )


def get_close_on_or_before(db: Session, security_id: UUID, on_date: date) -> tuple[float | None, date | None]:
    """取 on_date 当日或之前最近一根 K 线收盘价。"""
    row = db.scalar(
        select(MarketBar)
        .where(
            MarketBar.security_id == security_id,
            MarketBar.bar_date <= on_date,
        )
        .order_by(MarketBar.bar_date.desc())
        .limit(1)
    )
    if not row:
        return None, None
    return float(row.close), row.bar_date


def get_latest_close(db: Session, security_id: UUID) -> tuple[float | None, date | None, str]:
    """最新收盘价：优先 K 线，否则 last_price。"""
    last_bar_date = get_last_bar_date(db, security_id)
    if last_bar_date:
        close, d = get_close_on_or_before(db, security_id, last_bar_date)
        if close is not None:
            return close, d, "bars"
    sec = db.get(Security, security_id)
    if sec and sec.last_price:
        return float(sec.last_price), last_bar_date, "last_price"
    return None, None, "missing"


def sync_security_bars(
    db: Session,
    security: Security,
    days: int = 120,
    incremental: bool | None = None,
) -> int:
    end = date.today()
    use_incremental = incremental if incremental is not None else settings.quote_sync_incremental
    if use_incremental:
        last = get_last_bar_date(db, security.id)
        if last and last >= end - timedelta(days=1):
            return 0
        if last:
            start = last - timedelta(days=settings.quote_sync_overlap_days)
        else:
            start = end - timedelta(days=days)
    else:
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
    incremental: bool | None = None,
) -> dict:
    job = DataSyncJob(
        job_type=SyncJobType.quotes,
        params={
            "days": days,
            "incremental": incremental if incremental is not None else settings.quote_sync_incremental,
            "security_ids": [str(s) for s in security_ids] if security_ids else None,
        },
    )
    db.add(job)
    db.flush()

    if security_ids:
        securities = [db.get(Security, sid) for sid in security_ids]
        securities = [s for s in securities if s]
    else:
        securities = list(db.scalars(select(Security).where(Security.is_active.is_(True))))

    total_bars = 0
    skipped = 0
    errors = []
    retries = settings.quote_sync_retries
    for sec in securities:
        for attempt in range(retries + 1):
            try:
                n = sync_security_bars(db, sec, days, incremental=incremental)
                total_bars += n
                if n == 0 and incremental is not False:
                    skipped += 1
                break
            except Exception as e:
                if attempt < retries:
                    sleep(1.5 * (attempt + 1))
                    continue
                errors.append({"symbol": sec.symbol, "error": str(e)})

    if portfolio_id:
        refresh_portfolio_valuation(db, portfolio_id)

    job.status = SyncJobStatus.success if not errors else SyncJobStatus.failed
    job.result = {
        "bars_inserted": total_bars,
        "securities": len(securities),
        "skipped_up_to_date": skipped,
        "errors": errors,
    }
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
