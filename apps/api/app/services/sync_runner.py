"""后台数据同步（避免 HTTP 长连接超时）。"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.database import SessionLocal
from app.models import DataSyncJob, Portfolio, SyncJobStatus, SyncJobType
from app.config import settings
from app.services.filing_sync_service import sync_filings, sync_financials
from app.services.market_data_service import sync_quotes
from app.services.nav_service import record_nav_snapshot
from app.services.portfolio_service import refresh_portfolio_valuation
from app.services.report_service import generate_daily_report
from app.services.user_context import get_default_user

logger = logging.getLogger(__name__)


def _run_sync_all_job(job_id: UUID, security_ids: list[UUID] | None, days_q: int, days_f: int, portfolio_id: UUID | None):
    db = SessionLocal()
    job = db.get(DataSyncJob, job_id)
    if not job:
        db.close()
        return
    try:
        from sqlalchemy import select

        user = get_default_user(db)
        p = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
        pid = portfolio_id or (p.id if p else None)
        results = {}
        results["quotes"] = sync_quotes(db, security_ids, days_q, pid)
        results["filings"] = sync_filings(db, security_ids, days_f, True)
        results["financials"] = sync_financials(db, security_ids)
        post_sync: dict = {}
        if pid and settings.auto_nav_after_sync:
            refresh_portfolio_valuation(db, pid)
            snap = record_nav_snapshot(db, pid)
            post_sync["nav_snapshot"] = snap.snapshot_date.isoformat()
        if pid and settings.auto_daily_report_after_sync:
            report = generate_daily_report(db, pid)
            post_sync["daily_report_id"] = str(report.id)
        if post_sync:
            results["post_sync"] = post_sync
        job.status = SyncJobStatus.success
        job.result = results
    except Exception as e:
        logger.exception("background sync failed")
        job.status = SyncJobStatus.failed
        job.error_message = str(e)
    finally:
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.close()


def start_sync_all_background(
    job_id: UUID,
    security_ids: list[UUID] | None = None,
    days_q: int = 120,
    days_f: int = 90,
    portfolio_id: UUID | None = None,
) -> None:
    import threading

    t = threading.Thread(
        target=_run_sync_all_job,
        args=(job_id, security_ids, days_q, days_f, portfolio_id),
        daemon=True,
    )
    t.start()
