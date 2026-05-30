from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DataSyncJob, FinancialReport, Portfolio, Security, SyncJobStatus, SyncJobType
from app.services.data_quality_service import get_data_quality
from app.services.filing_sync_service import list_filings, sync_filings, sync_financials
from app.services.market_data_service import get_bars, sync_quotes
from app.services.sync_runner import start_sync_all_background
from app.services.user_context import get_default_user

router = APIRouter(prefix="/data", tags=["data"])


class SyncRequest(BaseModel):
    security_ids: list[UUID] | None = None
    days: int | None = None
    portfolio_id: UUID | None = None
    auto_structure: bool = True


@router.post("/sync/quotes")
def sync_quotes_endpoint(body: SyncRequest, db: Session = Depends(get_db)):
    from app.config import settings

    days = body.days or settings.quote_sync_days
    pid = body.portfolio_id
    if not pid:
        user = get_default_user(db)
        p = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
        pid = p.id if p else None
    try:
        return sync_quotes(db, body.security_ids, days, pid)
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.post("/sync/filings")
def sync_filings_endpoint(body: SyncRequest, db: Session = Depends(get_db)):
    from app.config import settings

    days = body.days or settings.filing_sync_days
    try:
        return sync_filings(db, body.security_ids, days, body.auto_structure)
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.post("/sync/financials")
def sync_financials_endpoint(body: SyncRequest, db: Session = Depends(get_db)):
    try:
        return sync_financials(db, body.security_ids)
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.get("/quality")
def data_quality(db: Session = Depends(get_db)):
    return get_data_quality(db)


@router.post("/sync/all/async")
def sync_all_async(body: SyncRequest, db: Session = Depends(get_db)):
    """后台全量同步，立即返回 job_id（适合 Railway 长任务）。"""
    days_q = body.days or settings.quote_sync_days
    days_f = body.days or settings.filing_sync_days
    user = get_default_user(db)
    p = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
    pid = body.portfolio_id or (p.id if p else None)
    job = DataSyncJob(
        job_type=SyncJobType.all,
        status=SyncJobStatus.running,
        params={"async": True, "days_q": days_q, "days_f": days_f},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    start_sync_all_background(job.id, body.security_ids, days_q, days_f, pid)
    return {"job_id": str(job.id), "status": "running", "message": "后台同步已启动"}


@router.get("/sync/jobs/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(DataSyncJob, job_id)
    if not job:
        raise HTTPException(404, "作业不存在")
    return {
        "id": str(job.id),
        "job_type": job.job_type.value,
        "status": job.status.value,
        "result": job.result,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.post("/sync/cron")
def sync_cron(
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
):
    """外部 Cron（Railway Cron / curl）触发全量同步。"""
    if settings.cron_secret and x_cron_secret != settings.cron_secret:
        raise HTTPException(401, "Invalid cron secret")
    body = SyncRequest()
    return sync_all_async(body, db)


@router.post("/sync/all")
def sync_all(body: SyncRequest, db: Session = Depends(get_db)):
    from app.config import settings

    days_q = body.days or settings.quote_sync_days
    days_f = body.days or settings.filing_sync_days
    user = get_default_user(db)
    p = db.scalar(select(Portfolio).where(Portfolio.user_id == user.id))
    pid = body.portfolio_id or (p.id if p else None)
    results = {}
    results["quotes"] = sync_quotes(db, body.security_ids, days_q, pid)
    results["filings"] = sync_filings(db, body.security_ids, days_f, body.auto_structure)
    results["financials"] = sync_financials(db, body.security_ids)
    return results


@router.get("/sync/jobs")
def list_jobs(limit: int = 20, db: Session = Depends(get_db)):
    jobs = db.scalars(select(DataSyncJob).order_by(DataSyncJob.started_at.desc()).limit(limit)).all()
    return [
        {
            "id": str(j.id),
            "job_type": j.job_type.value,
            "status": j.status.value,
            "result": j.result,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "error_message": j.error_message,
        }
        for j in jobs
    ]


@router.get("/bars/{security_id}")
def bars(security_id: UUID, days: int = 90, db: Session = Depends(get_db)):
    return get_bars(db, security_id, days)


@router.get("/bars/symbol/{symbol}")
def bars_by_symbol(symbol: str, days: int = 90, db: Session = Depends(get_db)):
    sec = db.scalar(select(Security).where(Security.symbol == symbol))
    if not sec:
        raise HTTPException(404, "标的不存在")
    return get_bars(db, sec.id, days)


@router.get("/filings")
def filings(
    security_id: UUID | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    return list_filings(db, security_id, limit)


@router.get("/financials/{security_id}")
def financials(security_id: UUID, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(FinancialReport)
        .where(FinancialReport.security_id == security_id)
        .order_by(FinancialReport.period_key.desc())
    ).all()
    return [
        {
            "id": str(r.id),
            "period_key": r.period_key,
            "report_type": r.report_type,
            "metrics": r.metrics,
        }
        for r in rows
    ]


@router.get("/financials/symbol/{symbol}")
def financials_by_symbol(symbol: str, db: Session = Depends(get_db)):
    sec = db.scalar(select(Security).where(Security.symbol == symbol))
    if not sec:
        raise HTTPException(404, "标的不存在")
    rows = db.scalars(
        select(FinancialReport)
        .where(FinancialReport.security_id == sec.id)
        .order_by(FinancialReport.period_key.desc())
    ).all()
    return {
        "symbol": symbol,
        "name": sec.name,
        "reports": [
            {
                "period_key": r.period_key,
                "report_type": r.report_type,
                "metrics": r.metrics,
            }
            for r in rows
        ],
    }
