"""定时数据同步（APScheduler）。"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.models import DataSyncJob, SyncJobStatus, SyncJobType
from app.services.sync_runner import start_sync_all_background

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _scheduled_sync_all():
    if not settings.data_sync_cron_enabled:
        return
    db = SessionLocal()
    try:
        job = DataSyncJob(job_type=SyncJobType.all, params={"trigger": "cron"})
        db.add(job)
        db.commit()
        db.refresh(job)
        start_sync_all_background(
            job.id,
            days_q=settings.quote_sync_days,
            days_f=settings.filing_sync_days,
        )
        logger.info("scheduled data sync started job_id=%s", job.id)
    except Exception:
        logger.exception("failed to start scheduled sync")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.data_sync_cron_enabled:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=settings.data_sync_cron_tz)
    hour, minute = settings.data_sync_cron_time.split(":", 1)
    _scheduler.add_job(
        _scheduled_sync_all,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id="aims_data_sync_all",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("data sync scheduler started at %s (%s)", settings.data_sync_cron_time, settings.data_sync_cron_tz)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
