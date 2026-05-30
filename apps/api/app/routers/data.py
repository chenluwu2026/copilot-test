from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DataSyncJob, Security, SyncJobType
from app.services.filing_sync_service import list_filings, sync_filings, sync_financials
from app.services.market_data_service import get_bars, sync_quotes
from app.services.user_context import get_default_user
from app.models import FinancialReport, Portfolio

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
