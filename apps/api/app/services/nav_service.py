from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NavSnapshot, Portfolio
from app.services.portfolio_service import get_portfolio_summary, refresh_portfolio_valuation


def record_nav_snapshot(db: Session, portfolio_id: UUID, snapshot_date: date | None = None) -> NavSnapshot:
    snapshot_date = snapshot_date or date.today()
    refresh_portfolio_valuation(db, portfolio_id)
    summary = get_portfolio_summary(db, portfolio_id)
    nav = Decimal(str(summary["nav"]))
    cash = Decimal(str(summary["cash"]))
    market_value = Decimal(str(summary["market_value"]))

    existing = db.scalar(
        select(NavSnapshot).where(
            NavSnapshot.portfolio_id == portfolio_id,
            NavSnapshot.snapshot_date == snapshot_date,
        )
    )
    prev = db.scalar(
        select(NavSnapshot)
        .where(NavSnapshot.portfolio_id == portfolio_id, NavSnapshot.snapshot_date < snapshot_date)
        .order_by(NavSnapshot.snapshot_date.desc())
        .limit(1)
    )

    daily_return = None
    if prev and prev.nav > 0:
        daily_return = (nav - prev.nav) / prev.nav * 100

    portfolio = db.get(Portfolio, portfolio_id)
    initial = portfolio.initial_cash if portfolio else nav
    cum_return = (nav - initial) / initial * 100 if initial > 0 else Decimal("0")

    peak_rows = db.scalars(
        select(NavSnapshot)
        .where(NavSnapshot.portfolio_id == portfolio_id)
        .order_by(NavSnapshot.nav.desc())
        .limit(1)
    ).all()
    peak = peak_rows[0].nav if peak_rows else nav
    if nav > peak:
        peak = nav
    drawdown = (nav - peak) / peak * 100 if peak > 0 else Decimal("0")

    if existing:
        existing.nav = nav
        existing.cash = cash
        existing.gross_exposure = market_value
        existing.daily_return_pct = daily_return
        existing.cumulative_return_pct = cum_return
        existing.drawdown_pct = drawdown
        db.commit()
        db.refresh(existing)
        return existing

    snap = NavSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        nav=nav,
        cash=cash,
        gross_exposure=market_value,
        daily_return_pct=daily_return,
        cumulative_return_pct=cum_return,
        drawdown_pct=drawdown,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def list_nav(db: Session, portfolio_id: UUID, days: int = 90) -> list[NavSnapshot]:
    since = date.today() - timedelta(days=days)
    return list(
        db.scalars(
            select(NavSnapshot)
            .where(
                NavSnapshot.portfolio_id == portfolio_id,
                NavSnapshot.snapshot_date >= since,
            )
            .order_by(NavSnapshot.snapshot_date)
        )
    )


def backfill_demo_nav(db: Session, portfolio_id: UUID, days: int = 30) -> int:
    """为演示生成平滑净值序列（围绕当前 NAV 小幅波动，避免指数级假数据）。"""
    import random

    refresh_portfolio_valuation(db, portfolio_id)
    summary = get_portfolio_summary(db, portfolio_id)
    base_nav = float(summary["nav"])
    cash = Decimal(str(summary["cash"]))
    market_value = Decimal(str(summary.get("market_value", summary["nav"] - summary["cash"])))
    start_nav = base_nav * (1 + random.uniform(-0.02, 0.02))
    count = 0
    for i in range(days, 0, -1):
        d = date.today() - timedelta(days=i)
        snap = db.scalar(
            select(NavSnapshot).where(
                NavSnapshot.portfolio_id == portfolio_id,
                NavSnapshot.snapshot_date == d,
            )
        )
        if snap:
            continue
        progress = (days - i) / max(days, 1)
        trend = start_nav + (base_nav - start_nav) * progress
        noise = base_nav * random.uniform(-0.004, 0.004)
        fake_nav = Decimal(str(round(trend + noise, 2)))
        snap = NavSnapshot(
            portfolio_id=portfolio_id,
            snapshot_date=d,
            nav=fake_nav,
            cash=cash,
            gross_exposure=market_value,
            daily_return_pct=Decimal("0"),
            cumulative_return_pct=Decimal("0"),
            drawdown_pct=Decimal("0"),
        )
        db.add(snap)
        count += 1
    db.commit()
    return count


def reset_nav_snapshots(db: Session, portfolio_id: UUID) -> NavSnapshot:
    """清除历史净值点并仅记录今日真实快照（修复混入演示数据后的曲线）。"""
    from sqlalchemy import delete

    db.execute(delete(NavSnapshot).where(NavSnapshot.portfolio_id == portfolio_id))
    db.commit()
    return record_nav_snapshot(db, portfolio_id)
