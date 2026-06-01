"""定时：数据同步、日报、调仓草案（APScheduler）。"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import DataSyncJob, Portfolio, SyncJobStatus, SyncJobType
from app.services.orchestrator import run_rebalance_workflow
from app.services.report_service import generate_daily_report
from app.services.news_sync_service import run_scheduled_news_sync
from app.services.review_cron_service import run_scheduled_reviews
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


def _scheduled_daily_report():
    if not settings.daily_report_cron_enabled:
        return
    db = SessionLocal()
    try:
        user = get_default_user(db)
        portfolio = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
        if not portfolio:
            return
        report = generate_daily_report(db, portfolio.id)
        logger.info(
            "scheduled daily report portfolio=%s date=%s",
            portfolio.id,
            report.report_date,
        )
    except Exception:
        logger.exception("scheduled daily report failed")
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


def _scheduled_review_due():
    if not settings.review_cron_enabled:
        return
    try:
        result = run_scheduled_reviews()
        logger.info("scheduled review due: %s", result)
    except Exception:
        logger.exception("scheduled review failed")


def _scheduled_news_sync():
    if not settings.news_sync_cron_enabled:
        return
    try:
        result = run_scheduled_news_sync()
        logger.info("scheduled news sync: %s", result)
    except Exception:
        logger.exception("scheduled news sync failed")


def _any_cron_enabled() -> bool:
    return (
        settings.data_sync_cron_enabled
        or settings.rebalance_cron_enabled
        or settings.daily_report_cron_enabled
        or settings.review_cron_enabled
        or settings.news_sync_cron_enabled
    )


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not _any_cron_enabled():
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

    if settings.daily_report_cron_enabled:
        dh, dm = settings.daily_report_cron_time.split(":", 1)
        _scheduler.add_job(
            _scheduled_daily_report,
            CronTrigger(hour=int(dh), minute=int(dm)),
            id="aims_daily_report",
            replace_existing=True,
        )
        logger.info(
            "daily report scheduler at %s (%s)",
            settings.daily_report_cron_time,
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

    if settings.review_cron_enabled:
        rvh, rvm = settings.review_cron_time.split(":", 1)
        _scheduler.add_job(
            _scheduled_review_due,
            CronTrigger(hour=int(rvh), minute=int(rvm)),
            id="aims_review_due",
            replace_existing=True,
        )
        logger.info("review cron at %s", settings.review_cron_time)

    if settings.news_sync_cron_enabled:
        nh, nm = settings.news_sync_cron_time.split(":", 1)
        _scheduler.add_job(
            _scheduled_news_sync,
            CronTrigger(hour=int(nh), minute=int(nm)),
            id="aims_news_sync",
            replace_existing=True,
        )
        logger.info("news sync cron at %s", settings.news_sync_cron_time)

    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
