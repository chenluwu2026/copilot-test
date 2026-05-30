from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Decision,
    DecisionAction,
    DecisionStatus,
    Portfolio,
    Position,
    Security,
    Trade,
    TradeSide,
    TradeSource,
)


COMMISSION_RATE = Decimal("0.0003")
MIN_COMMISSION = Decimal("5")


def _commission(amount: Decimal) -> Decimal:
    return max(amount * COMMISSION_RATE, MIN_COMMISSION)


def get_portfolio(db: Session, portfolio_id: UUID) -> Portfolio | None:
    return db.get(Portfolio, portfolio_id)


def list_portfolios(db: Session, user_id: UUID) -> list[Portfolio]:
    return list(db.scalars(select(Portfolio).where(Portfolio.user_id == user_id)))


def create_portfolio(
    db: Session,
    user_id: UUID,
    name: str,
    initial_cash: Decimal,
    base_currency: str = "CNY",
    benchmark_symbol: str | None = "CSI300",
) -> Portfolio:
    portfolio = Portfolio(
        user_id=user_id,
        name=name,
        initial_cash=initial_cash,
        cash_balance=initial_cash,
        base_currency=base_currency,
        benchmark_symbol=benchmark_symbol,
        risk_limits={
            "max_single_name_pct": 10,
            "max_sector_pct": 25,
            "min_cash_pct": 5,
        },
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def _validate_lot(security: Security, quantity: Decimal) -> None:
    if security.market.value == "HK" and quantity % security.lot_size != 0:
        raise ValueError(f"港股交易数量须为 {security.lot_size} 的整数倍")


def execute_trade(
    db: Session,
    portfolio_id: UUID,
    security_id: UUID,
    side: TradeSide,
    quantity: Decimal,
    price: Decimal,
    trade_date: date | None = None,
    source: TradeSource = TradeSource.manual,
    decision_id: UUID | None = None,
    note: str | None = None,
) -> Trade:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("组合不存在")
    security = db.get(Security, security_id)
    if not security:
        raise ValueError("标的不存在")

    _validate_lot(security, quantity)
    trade_date = trade_date or date.today()
    amount = quantity * price
    commission = _commission(amount)

    if side == TradeSide.buy:
        total_cost = amount + commission
        if portfolio.cash_balance < total_cost:
            raise ValueError("现金不足")
        portfolio.cash_balance -= total_cost
    else:
        pos = db.scalar(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.security_id == security_id,
            )
        )
        if not pos or pos.quantity < quantity:
            raise ValueError("持仓不足")
        portfolio.cash_balance += amount - commission

    trade = Trade(
        portfolio_id=portfolio_id,
        security_id=security_id,
        decision_id=decision_id,
        side=side,
        quantity=quantity,
        price=price,
        amount=amount,
        commission=commission,
        trade_date=trade_date,
        source=source,
        note=note,
    )
    db.add(trade)
    _update_position(db, portfolio, security, side, quantity, price, trade_date)
    db.commit()
    db.refresh(trade)
    refresh_portfolio_valuation(db, portfolio_id)
    return trade


def _update_position(
    db: Session,
    portfolio: Portfolio,
    security: Security,
    side: TradeSide,
    quantity: Decimal,
    price: Decimal,
    trade_date: date,
) -> None:
    pos = db.scalar(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.security_id == security.id,
        )
    )
    if side == TradeSide.buy:
        if pos:
            total_qty = pos.quantity + quantity
            pos.avg_cost = (pos.avg_cost * pos.quantity + price * quantity) / total_qty
            pos.quantity = total_qty
        else:
            pos = Position(
                portfolio_id=portfolio.id,
                security_id=security.id,
                quantity=quantity,
                avg_cost=price,
                opened_at=trade_date,
            )
            db.add(pos)
    elif pos:
        pos.quantity -= quantity
        if pos.quantity <= 0:
            db.delete(pos)


def refresh_portfolio_valuation(db: Session, portfolio_id: UUID) -> Decimal:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("组合不存在")

    positions = db.scalars(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .options(joinedload(Position.security))
    ).all()

    total_market = Decimal("0")
    for pos in positions:
        price = pos.security.last_price or pos.avg_cost
        pos.market_value = pos.quantity * price
        total_market += pos.market_value

    nav = total_market + portfolio.cash_balance
    for pos in positions:
        pos.weight_pct = (pos.market_value / nav * 100) if nav > 0 else Decimal("0")

    db.commit()
    return nav


def get_portfolio_summary(db: Session, portfolio_id: UUID) -> dict:
    portfolio = db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("组合不存在")

    positions = db.scalars(
        select(Position)
        .where(Position.portfolio_id == portfolio_id)
        .options(joinedload(Position.security))
    ).all()

    total_market = sum(p.market_value for p in positions)
    nav = total_market + portfolio.cash_balance
    initial = portfolio.initial_cash
    cum_return = ((nav - initial) / initial * 100) if initial > 0 else Decimal("0")

    return {
        "portfolio_id": str(portfolio_id),
        "name": portfolio.name,
        "nav": float(nav),
        "cash": float(portfolio.cash_balance),
        "market_value": float(total_market),
        "cash_pct": float(portfolio.cash_balance / nav * 100) if nav > 0 else 100.0,
        "position_count": len(positions),
        "cumulative_return_pct": float(cum_return),
        "positions": [
            {
                "security_id": str(p.security_id),
                "symbol": p.security.symbol,
                "name": p.security.name,
                "quantity": float(p.quantity),
                "avg_cost": float(p.avg_cost),
                "last_price": float(p.security.last_price or p.avg_cost),
                "market_value": float(p.market_value),
                "weight_pct": float(p.weight_pct),
                "unrealized_pnl": float(
                    p.market_value - p.quantity * p.avg_cost
                ),
                "sector": p.security.sector,
            }
            for p in positions
        ],
    }


def execute_decision(db: Session, decision_id: UUID, price: Decimal | None = None) -> Trade:
    decision = db.scalar(
        select(Decision)
        .where(Decision.id == decision_id)
        .options(joinedload(Decision.security), joinedload(Decision.portfolio))
    )
    if not decision:
        raise ValueError("决策不存在")
    if decision.status != DecisionStatus.approved:
        raise ValueError("仅 approved 状态可执行")
    if decision.action in (DecisionAction.hold, DecisionAction.watch, DecisionAction.ban):
        raise ValueError("该动作无需成交")

    security = decision.security
    portfolio = decision.portfolio
    price = price or security.last_price or Decimal("100")

    summary = get_portfolio_summary(db, portfolio.id)
    nav = Decimal(str(summary["nav"]))
    target_value = nav * decision.target_weight_pct / 100
    current_pos = next(
        (p for p in summary["positions"] if p["symbol"] == security.symbol),
        None,
    )
    current_value = Decimal(str(current_pos["market_value"])) if current_pos else Decimal("0")
    delta_value = target_value - current_value

    if abs(delta_value) < Decimal("1"):
        decision.status = DecisionStatus.executed
        db.commit()
        raise ValueError("仓位变化过小，无需交易")

    quantity = abs(delta_value / price).quantize(Decimal("1"))
    if security.market.value == "HK":
        lot = security.lot_size
        quantity = (quantity // lot) * lot
        if quantity == 0:
            quantity = Decimal(lot)

    side = TradeSide.buy if delta_value > 0 else TradeSide.sell
    trade = execute_trade(
        db,
        portfolio.id,
        security.id,
        side,
        quantity,
        price,
        source=TradeSource.agent,
        decision_id=decision.id,
        note=f"执行决策 {decision.action.value}",
    )
    decision.status = DecisionStatus.executed
    from datetime import datetime

    decision.executed_at = datetime.utcnow()
    summary = dict(decision.cio_summary or {})
    summary["entry_price"] = float(price)
    decision.cio_summary = summary
    db.commit()
    return trade
