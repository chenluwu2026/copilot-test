"""关注池标的资讯定时入库（方案 C）。"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Security, Watchlist, WatchlistItem
from app.services.structuring_service import ingest_news
from app.services.user_context import get_default_user

logger = logging.getLogger(__name__)


def _fetch_headlines(symbol: str, name: str) -> list[tuple[str, str]]:
    """尝试 AkShare 个股新闻，失败则返回空。"""
    if settings.data_provider == "mock":
        return []
    try:
        import akshare as ak

        code = symbol.split(".")[0]
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return []
        rows = []
        for _, row in df.head(3).iterrows():
            title = str(row.get("新闻标题", row.get("title", "")))[:200]
            body = str(row.get("新闻内容", row.get("content", "")))[:1500]
            if title:
                rows.append((f"{name}: {title}", body))
        return rows
    except Exception as e:
        logger.debug("akshare news skip %s: %s", symbol, e)
        return []


def sync_news_for_watchlist(db: Session, user_id: UUID, max_symbols: int | None = None) -> dict:
    max_symbols = max_symbols or settings.news_sync_max_symbols
    security_ids: list[UUID] = []
    for wl in db.scalars(select(Watchlist).where(Watchlist.user_id == user_id)):
        for item in db.scalars(
            select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
        ):
            if item.security_id not in security_ids:
                security_ids.append(item.security_id)

    ingested = 0
    errors: list[str] = []
    for sid in security_ids[:max_symbols]:
        sec = db.get(Security, sid)
        if not sec:
            continue
        headlines = _fetch_headlines(sec.symbol, sec.name)
        if not headlines:
            continue
        for title, body in headlines:
            try:
                ingest_news(
                    db,
                    title,
                    body,
                    [sid],
                    source_name="news_cron",
                    published_at=datetime.now(timezone.utc),
                )
                ingested += 1
            except Exception as e:
                errors.append(f"{sec.symbol}: {e}")
    return {"ingested": ingested, "symbols_scanned": min(len(security_ids), max_symbols), "errors": errors[:5]}


def run_scheduled_news_sync() -> dict:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        user = get_default_user(db)
        return sync_news_for_watchlist(db, user.id)
    finally:
        db.close()
