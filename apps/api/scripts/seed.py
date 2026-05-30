"""初始化演示数据：标的、默认组合、示例决策。"""
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Decision,
    DecisionAction,
    DecisionAssumption,
    DecisionReference,
    DecisionStatus,
    Market,
    Portfolio,
    ReferenceType,
    Security,
    User,
    Watchlist,
    WatchlistItem,
    WatchlistTier,
)
from app.config import settings
from app.services import decision_service as ds
from app.services import portfolio_service as ps
from app.services.nav_service import backfill_demo_nav
from app.services.user_context import get_default_user


SECURITIES = [
    ("600519.SH", "贵州茅台", Market.CN_A, "CNY", "食品饮料", 100, 1680.0),
    ("000858.SZ", "五粮液", Market.CN_A, "CNY", "食品饮料", 100, 145.0),
    ("300750.SZ", "宁德时代", Market.CN_A, "CNY", "电力设备", 100, 185.0),
    ("601318.SH", "中国平安", Market.CN_A, "CNY", "非银金融", 100, 52.0),
    ("600036.SH", "招商银行", Market.CN_A, "CNY", "银行", 100, 38.5),
    ("000333.SZ", "美的集团", Market.CN_A, "CNY", "家用电器", 100, 72.0),
    ("002594.SZ", "比亚迪", Market.CN_A, "CNY", "汽车", 100, 268.0),
    ("600900.SH", "长江电力", Market.CN_A, "CNY", "公用事业", 100, 28.5),
    ("00700.HK", "腾讯控股", Market.HK, "HKD", "传媒", 100, 380.0),
    ("09988.HK", "阿里巴巴-SW", Market.HK, "HKD", "商贸零售", 100, 85.0),
    ("03690.HK", "美团-W", Market.HK, "HKD", "社会服务", 100, 125.0),
    ("01810.HK", "小米集团-W", Market.HK, "HKD", "电子", 200, 18.5),
    ("00941.HK", "中国移动", Market.HK, "HKD", "通信", 500, 68.0),
    ("02318.HK", "中国平安", Market.HK, "HKD", "非银金融", 500, 42.0),
    ("09618.HK", "京东集团-SW", Market.HK, "HKD", "商贸零售", 50, 130.0),
]


def run_seed() -> None:
    db = SessionLocal()
    try:
        _seed_securities(db)
        user = get_default_user(db)
        portfolio = _seed_portfolio(db, user.id)
        if portfolio:
            _seed_watchlist(db, user.id)
            _seed_sample_decisions(db, portfolio.id)
            _seed_demo_trades(db, portfolio.id)
            backfill_demo_nav(db, portfolio.id, 30)
    finally:
        db.close()


def _seed_securities(db) -> None:
    for sym, name, market, cur, sector, lot, price in SECURITIES:
        exists = db.scalar(
            select(Security).where(Security.symbol == sym, Security.market == market)
        )
        if not exists:
            db.add(
                Security(
                    symbol=sym,
                    name=name,
                    market=market,
                    currency=cur,
                    sector=sector,
                    lot_size=lot,
                    last_price=Decimal(str(price)),
                )
            )
    db.commit()


def _seed_portfolio(db, user_id) -> Portfolio | None:
    existing = db.scalar(select(Portfolio).where(Portfolio.user_id == user_id))
    if existing:
        return existing
    return ps.create_portfolio(db, user_id, "主模拟组合", Decimal("1000000"))


def _seed_watchlist(db, user_id) -> None:
    if db.scalar(select(Watchlist).where(Watchlist.user_id == user_id)):
        return
    wl = Watchlist(user_id=user_id, name="核心股票池", description="AIMS 默认跟踪池")
    db.add(wl)
    db.flush()
    symbols = ["00700.HK", "600519.SH", "300750.SZ", "09988.HK", "03690.HK"]
    for sym in symbols:
        sec = db.scalar(select(Security).where(Security.symbol == sym))
        if sec:
            db.add(
                WatchlistItem(
                    watchlist_id=wl.id,
                    security_id=sec.id,
                    tier=WatchlistTier.core,
                )
            )
    db.commit()


def _seed_sample_decisions(db, portfolio_id) -> None:
    if db.scalar(select(Decision).where(Decision.portfolio_id == portfolio_id)):
        return
    tencent = db.scalar(select(Security).where(Security.symbol == "00700.HK"))
    moutai = db.scalar(select(Security).where(Security.symbol == "600519.SH"))
    if not tencent or not moutai:
        return

    ds.create_decision(
        db,
        portfolio_id,
        tencent.id,
        DecisionAction.add,
        "估值处于历史偏低区间，业绩修复与回购支撑；需验证游戏与广告核心变量。",
        3.0,
        7.0,
        ["游戏流水不及预期", "监管扰动"],
        ["下季报游戏收入同比下滑超10%则降级为 watch", "回购规模明显低于指引"],
        [
            {"text": "未来两季度游戏流水同比企稳", "measurable": True, "metric_key": "game_rev_yoy"},
        ],
        [{"ref_type": "filing", "excerpt": "季报：收入同比+8%"}],
        "B+",
        "3-6个月",
        created_by_agent="cio_agent",
    )
    d2 = ds.create_decision(
        db,
        portfolio_id,
        moutai.id,
        DecisionAction.hold,
        "基本面稳健但估值不低，维持核心仓位观察批价与渠道库存。",
        8.0,
        8.0,
        ["批价下行", "需求不及预期"],
        ["批价连续两季下行则减仓至5%"],
        [{"text": "直销渠道占比持续提升"}],
        [],
        "A-",
        "12个月+",
    )
    ds.create_decision(
        db,
        portfolio_id,
        tencent.id,
        DecisionAction.watch,
        "等待广告复苏数据确认后再加仓。",
        0,
        0,
        ["宏观消费疲软"],
        ["广告收入增速转正"],
        [{"text": "广告收入增速由负转正"}],
        [],
        "C",
        "1-3个月",
    )
    # 批准第一条供演示执行
    first = db.scalar(
        select(Decision).where(
            Decision.portfolio_id == portfolio_id,
            Decision.action == DecisionAction.add,
        )
    )
    if first:
        first.status = DecisionStatus.approved
        db.commit()


def _seed_demo_trades(db, portfolio_id) -> None:
    from app.models import Trade

    if db.scalar(select(Trade).where(Trade.portfolio_id == portfolio_id)):
        return
    moutai = db.scalar(select(Security).where(Security.symbol == "600519.SH"))
    from app.models import TradeSide

    if moutai:
        ps.execute_trade(
            db,
            portfolio_id,
            moutai.id,
            TradeSide.buy,
            Decimal("100"),
            moutai.last_price or Decimal("1680"),
            note="种子建仓",
        )
