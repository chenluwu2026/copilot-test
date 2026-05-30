from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Trade, TradeSide
from app.schemas_api import PortfolioCreate, PortfolioOut, TradeCreate, TradeOut
from app.services import portfolio_service as ps
from app.services.nav_service import backfill_demo_nav, list_nav, record_nav_snapshot
from app.services.report_service import generate_daily_report
from app.services.user_context import get_default_user

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioOut])
def list_portfolios(db: Session = Depends(get_db)):
    user = get_default_user(db)
    items = ps.list_portfolios(db, user.id)
    return [
        PortfolioOut(
            id=p.id,
            name=p.name,
            cash_balance=float(p.cash_balance),
            initial_cash=float(p.initial_cash),
            base_currency=p.base_currency,
            benchmark_symbol=p.benchmark_symbol,
        )
        for p in items
    ]


@router.post("", response_model=PortfolioOut)
def create_portfolio(body: PortfolioCreate, db: Session = Depends(get_db)):
    user = get_default_user(db)
    from decimal import Decimal

    p = ps.create_portfolio(
        db, user.id, body.name, Decimal(str(body.initial_cash)), body.base_currency, body.benchmark_symbol
    )
    return PortfolioOut(
        id=p.id,
        name=p.name,
        cash_balance=float(p.cash_balance),
        initial_cash=float(p.initial_cash),
        base_currency=p.base_currency,
        benchmark_symbol=p.benchmark_symbol,
    )


@router.get("/{portfolio_id}/summary")
def portfolio_summary(portfolio_id: UUID, db: Session = Depends(get_db)):
    try:
        return ps.get_portfolio_summary(db, portfolio_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{portfolio_id}/trades", response_model=list[TradeOut])
def list_trades(portfolio_id: UUID, db: Session = Depends(get_db)):
    trades = db.scalars(
        select(Trade)
        .where(Trade.portfolio_id == portfolio_id)
        .options(joinedload(Trade.security))
        .order_by(Trade.trade_date.desc())
    ).all()
    return [
        TradeOut(
            id=t.id,
            security_id=t.security_id,
            side=t.side.value,
            quantity=float(t.quantity),
            price=float(t.price),
            amount=float(t.amount),
            commission=float(t.commission),
            trade_date=t.trade_date,
            source=t.source.value,
            symbol=t.security.symbol,
            name=t.security.name,
        )
        for t in trades
    ]


@router.post("/{portfolio_id}/trades", response_model=TradeOut)
def create_trade(portfolio_id: UUID, body: TradeCreate, db: Session = Depends(get_db)):
    from decimal import Decimal

    try:
        trade = ps.execute_trade(
            db,
            portfolio_id,
            body.security_id,
            TradeSide(body.side),
            Decimal(str(body.quantity)),
            Decimal(str(body.price)),
            body.trade_date,
            note=body.note,
        )
        t = db.scalar(
            select(Trade)
            .where(Trade.id == trade.id)
            .options(joinedload(Trade.security))
        )
        return TradeOut(
            id=t.id,
            security_id=t.security_id,
            side=t.side.value,
            quantity=float(t.quantity),
            price=float(t.price),
            amount=float(t.amount),
            commission=float(t.commission),
            trade_date=t.trade_date,
            source=t.source.value,
            symbol=t.security.symbol,
            name=t.security.name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/{portfolio_id}/nav")
def get_nav(portfolio_id: UUID, days: int = 90, db: Session = Depends(get_db)):
    snaps = list_nav(db, portfolio_id, days)
    return [
        {
            "snapshot_date": s.snapshot_date.isoformat(),
            "nav": float(s.nav),
            "daily_return_pct": float(s.daily_return_pct) if s.daily_return_pct else None,
            "cumulative_return_pct": float(s.cumulative_return_pct) if s.cumulative_return_pct else None,
            "drawdown_pct": float(s.drawdown_pct) if s.drawdown_pct else None,
        }
        for s in snaps
    ]


@router.post("/{portfolio_id}/nav/snapshot")
def snapshot_nav(portfolio_id: UUID, db: Session = Depends(get_db)):
    snap = record_nav_snapshot(db, portfolio_id)
    return {"snapshot_date": snap.snapshot_date.isoformat(), "nav": float(snap.nav)}


@router.post("/{portfolio_id}/nav/backfill-demo")
def backfill_nav(portfolio_id: UUID, days: int = 30, db: Session = Depends(get_db)):
    count = backfill_demo_nav(db, portfolio_id, days)
    return {"created": count}


@router.post("/{portfolio_id}/reports/daily")
def daily_report(portfolio_id: UUID, db: Session = Depends(get_db)):
    report = generate_daily_report(db, portfolio_id)
    return {
        "id": str(report.id),
        "report_date": report.report_date.isoformat(),
        "summary_md": report.summary_md,
        "metrics": report.metrics,
    }
