"""公告与财报同步，高敏感度公告自动结构化。"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import (
    DataSyncJob,
    Filing,
    FinancialReport,
    Market,
    Security,
    SyncJobStatus,
    SyncJobType,
)
from app.services.structuring_service import ingest_news


def _fetch_notices(symbol: str, market: str, start: date, end: date):
    if market != "CN_A":
        return []
    if settings.data_provider == "mock":
        from app.data_connectors import mock_provider

        return mock_provider.fetch_a_notices(symbol, start, end)
    from app.data_connectors import akshare_provider

    try:
        return akshare_provider.fetch_a_notices(symbol, start, end)
    except Exception:
        from app.data_connectors import mock_provider

        return mock_provider.fetch_a_notices(symbol, start, end)


def _fetch_financial(symbol: str, market: str) -> dict:
    if market == "HK":
        if settings.data_provider == "mock":
            return {}
        from app.data_connectors import akshare_provider

        try:
            return akshare_provider.fetch_hk_financial_report(symbol)
        except Exception:
            return {}
    if settings.data_provider == "mock":
        from app.data_connectors import mock_provider

        return mock_provider.fetch_a_financial_abstract(symbol)
    from app.data_connectors import akshare_provider

    try:
        return akshare_provider.fetch_a_financial_abstract(symbol)
    except Exception:
        from app.data_connectors import mock_provider

        return mock_provider.fetch_a_financial_abstract(symbol)


def _should_structure(filing_type: str, title: str) -> bool:
    keys = (
        "annual_report",
        "quarterly_report",
        "semi_annual",
        "earnings",
        "earnings_guidance",
        "buyback",
    )
    if filing_type in keys:
        return True
    for k in ("业绩", "财报", "年报", "季报", "回购"):
        if k in title:
            return True
    return False


def sync_filings(
    db: Session,
    security_ids: list[UUID] | None = None,
    days: int = 90,
    auto_structure: bool = True,
) -> dict:
    job = DataSyncJob(job_type=SyncJobType.filings, params={"days": days})
    db.add(job)
    db.flush()

    end = date.today()
    start = end - timedelta(days=days)
    if security_ids:
        securities = [db.get(Security, s) for s in security_ids]
        securities = [s for s in securities if s]
    else:
        securities = list(db.scalars(select(Security).where(Security.is_active.is_(True))))

    inserted = 0
    structured = 0
    for sec in securities:
        if sec.market != Market.CN_A:
            continue
        notices = _fetch_notices(sec.symbol, sec.market.value, start, end)
        for n in notices:
            pub = n["published_at"]
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            exists = db.scalar(
                select(Filing).where(
                    Filing.security_id == sec.id,
                    Filing.title == n["title"],
                    Filing.published_at == pub,
                )
            )
            if exists:
                continue
            filing = Filing(
                security_id=sec.id,
                filing_type=n["filing_type"],
                title=n["title"],
                published_at=pub,
                source_url=n.get("source_url"),
                raw_content=n.get("raw_content"),
            )
            db.add(filing)
            db.flush()
            inserted += 1
            if auto_structure and _should_structure(n["filing_type"], n["title"]):
                try:
                    _, ev = ingest_news(
                        db,
                        n["title"],
                        n.get("raw_content") or n["title"],
                        [sec.id],
                        source_name="cninfo",
                        source_url=n.get("source_url"),
                        published_at=pub,
                    )
                    filing.structured_event_id = ev.id
                    structured += 1
                except Exception:
                    pass
    db.commit()
    job.status = SyncJobStatus.success
    job.result = {"filings_inserted": inserted, "structured_events": structured}
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"job_id": str(job.id), **job.result}


def sync_financials(db: Session, security_ids: list[UUID] | None = None) -> dict:
    job = DataSyncJob(job_type=SyncJobType.financials, params={})
    db.add(job)
    db.flush()

    if security_ids:
        securities = [db.get(Security, s) for s in security_ids]
        securities = [s for s in securities if s]
    else:
        securities = list(db.scalars(select(Security).where(Security.is_active.is_(True))))

    upserted = 0
    for sec in securities:
        data = _fetch_financial(sec.symbol, sec.market.value)
        if not data:
            continue
        if sec.market == Market.CN_A:
            periods = data.get("periods", [])
            metrics = data.get("metrics", {})
            for period in periods[:4]:
                period_metrics = {
                    k: v.get(period) for k, v in metrics.items() if isinstance(v, dict)
                }
                existing = db.scalar(
                    select(FinancialReport).where(
                        FinancialReport.security_id == sec.id,
                        FinancialReport.period_key == period,
                        FinancialReport.report_type == "abstract",
                    )
                )
                if existing:
                    existing.metrics = period_metrics
                    existing.raw_data = data
                else:
                    db.add(
                        FinancialReport(
                            security_id=sec.id,
                            period_key=period,
                            report_type="abstract",
                            metrics=period_metrics,
                            raw_data=data,
                        )
                    )
                    upserted += 1
        else:
            period = date.today().strftime("%Y")
            existing = db.scalar(
                select(FinancialReport).where(
                    FinancialReport.security_id == sec.id,
                    FinancialReport.period_key == period,
                    FinancialReport.report_type == "hk_report",
                )
            )
            payload = {"metrics": {}, "raw_data": data}
            if existing:
                existing.raw_data = data
            else:
                db.add(
                    FinancialReport(
                        security_id=sec.id,
                        period_key=period,
                        report_type="hk_report",
                        metrics={},
                        raw_data=data,
                    )
                )
                upserted += 1
    db.commit()
    job.status = SyncJobStatus.success
    job.result = {"reports_upserted": upserted}
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"job_id": str(job.id), **job.result}


def list_filings(db: Session, security_id: UUID | None = None, limit: int = 50) -> list[dict]:
    q = select(Filing).order_by(Filing.published_at.desc()).limit(limit)
    if security_id:
        q = q.where(Filing.security_id == security_id)
    rows = db.scalars(q.options(joinedload(Filing.security))).all()
    return [
        {
            "id": str(f.id),
            "security_id": str(f.security_id),
            "symbol": f.security.symbol if f.security else None,
            "name": f.security.name if f.security else None,
            "filing_type": f.filing_type,
            "title": f.title,
            "published_at": f.published_at.isoformat() if f.published_at else None,
            "source_url": f.source_url,
            "structured_event_id": str(f.structured_event_id) if f.structured_event_id else None,
        }
        for f in rows
    ]
