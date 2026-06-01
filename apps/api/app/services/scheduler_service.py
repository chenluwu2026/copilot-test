"""定时数据同步与 CIO 调仓草案（APScheduler）。"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import DataSyncJob, Portfolio, SyncJobStatus, SyncJobType
from app.services.orchestrator import run_rebalance_workflow
from app.services.sync_runner import start_sync_all_background
from app.services.user_context import get_default_user

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


def _scheduled_rebalance_draft():
    if not settings.rebalance_cron_enabled:
        return
    db = SessionLocal()
    try:
        user = get_default_user(db)
        portfolio = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
        if not portfolio:
            return
        run = run_rebalance_workflow(db, portfolio.id, trigger="cron")
        logger.info(
            "scheduled rebalance draft run_id=%s decisions=%s",
            run.id,
            (run.output or {}).get("decision_ids", []),
        )
    except Exception:
        logger.exception("scheduled rebalance draft failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.data_sync_cron_enabled and not settings.rebalance_cron_enabled:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=settings.data_sync_cron_tz)

    if settings.data_sync_cron_enabled:
        hour, minute = settings.data_sync_cron_time.split(":", 1)
        _scheduler.add_job(
            _scheduled_sync_all,
            CronTrigger(hour=int(hour), minute=int(minute)),
            id="aims_data_sync_all",
            replace_existing=True,
        )
        logger.info(
            "data sync scheduler at %s (%s)",
            settings.data_sync_cron_time,
            settings.data_sync_cron_tz,
        )

    if settings.rebalance_cron_enabled:
        rh, rm = settings.rebalance_cron_time.split(":", 1)
        _scheduler.add_job(
            _scheduled_rebalance_draft,
            CronTrigger(hour=int(rh), minute=int(rm)),
            id="aims_rebalance_draft",
            replace_existing=True,
        )
        logger.info(
            "rebalance draft scheduler at %s (%s)",
            settings.rebalance_cron_time,
            settings.data_sync_cron_tz,
        )

    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
