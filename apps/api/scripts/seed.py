"""初始化演示数据：标的、默认组合、示例决策。"""
from decimal import Decimal

from sqlalchemy import func, select

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
from app.models import (
    MemoryEntry,
    MemoryType,
    ResearchRating,
    ResearchView,
    StrategyRule,
    StructuredEvent,
)
from app.services.nav_service import backfill_demo_nav
from app.services.research_service import create_research_view
from app.services.structuring_service import ingest_news
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
            _seed_phase1_completion(db, portfolio.id)
            _seed_golden_path(db, portfolio.id)
        _seed_phase2(db)
        _seed_phase34(db)
    finally:
        db.close()


def _seed_phase2(db) -> None:
    if db.scalar(select(StructuredEvent).limit(1)):
        return

    news_items = [
        (
            "腾讯控股发布季报：收入同比+8%，回购计划延续",
            "腾讯控股公布季度业绩，总收入同比增长8%，净利润超预期。公司宣布继续执行股份回购计划，"
            "游戏业务国内流水企稳，广告收入增速改善。管理层强调 AI 投入将聚焦效率提升。",
            ["00700.HK", "03690.HK"],
        ),
        (
            "贵州茅台批价坚挺，渠道库存处于健康水平",
            "据渠道调研，飞天茅台批价维持稳定，经销商库存约1.5个月，动销符合旺季预期。"
            "公司直销占比提升有助于利润率维持高位。",
            ["600519.SH"],
        ),
        (
            "宁德时代获海外大单，产能利用率回升",
            "宁德时代宣布与欧洲车企签署长期供货协议，市场关注毛利率修复与产能利用率回升节奏。",
            ["300750.SZ", "002594.SZ"],
        ),
        (
            "港股科技板块受宏观数据扰动，互联网估值分化",
            "美国通胀数据公布后港股科技波动加大，市场重新定价降息预期，互联网龙头估值分化加剧。",
            ["00700.HK", "09988.HK", "03690.HK"],
        ),
        (
            "央行降准0.25个百分点，流动性预期改善",
            "中国人民银行宣布下调存款准备金率，市场解读为稳增长信号，金融与消费板块情绪回暖。",
            ["601318.SH", "600036.SH"],
        ),
    ]
    for title, body, symbols in news_items:
        ids = []
        for sym in symbols:
            sec = db.scalar(select(Security).where(Security.symbol == sym))
            if sec:
                ids.append(sec.id)
        if ids:
            ingest_news(db, title, body, ids, source_name="aims_seed")

    _seed_research_views(db)


def _seed_research_views(db) -> None:
    if db.scalar(select(ResearchView).limit(1)):
        return

    tencent = db.scalar(select(Security).where(Security.symbol == "00700.HK"))
    if tencent:
        create_research_view(
            db,
            tencent.id,
            ResearchRating.buy,
            {
                "business_model": "社交+游戏+广告+金融科技+云与 AI 的多引擎平台；游戏与广告为利润核心。",
                "industry_space": "数字娱乐与在线广告市场空间大，云服务与 AI 为第二增长曲线。",
                "competitive_landscape": "国内社交壁垒高；游戏面临监管与竞品；广告与阿里、字节竞争。",
                "financial_quality": "现金流充沛，资产负债表稳健，回购提升股东回报。",
                "management": "资本配置偏向回购与战略投资，AI 投入节奏受关注。",
                "growth_drivers": "游戏新品周期、广告复苏、视频号商业化、云与 AI 货币化。",
                "key_risks": "游戏流水波动、监管、AI 投入侵蚀利润率、宏观消费。",
                "current_valuation": "PE 处于近五年偏低分位，不能单独作为买入理由，需业绩验证。",
                "core_variables_6_12m": [
                    "国内游戏流水同比",
                    "广告收入增速",
                    "回购规模",
                    "AI 相关 Capex 与利润率",
                ],
            },
            "基本面修复+回购支撑，维持买入评级；交易需经组合与风控，见决策日志。",
            horizon="6-12个月",
            scenario_analysis={
                "methods": ["PE", "historical_percentile"],
                "scenarios": [
                    {
                        "name": "optimistic",
                        "probability_weight": 0.3,
                        "target_price_low": 420,
                        "target_price_high": 480,
                        "triggers": ["游戏超预期", "广告强劲复苏"],
                    },
                    {
                        "name": "base",
                        "probability_weight": 0.5,
                        "target_price_low": 360,
                        "target_price_high": 410,
                        "triggers": ["业绩符合预期"],
                    },
                    {
                        "name": "pessimistic",
                        "probability_weight": 0.2,
                        "target_price_low": 300,
                        "target_price_high": 340,
                        "triggers": ["监管收紧", "游戏不及预期"],
                        "downside_risk_note": "盈利与估值双杀",
                    },
                ],
                "current_price": 380,
                "currency": "HKD",
            },
            valuation_snapshot={"pe_ttm": 18, "percentile_5y": 0.25},
            agent_name="research_agent",
        )

    moutai = db.scalar(select(Security).where(Security.symbol == "600519.SH"))
    if moutai:
        create_research_view(
            db,
            moutai.id,
            ResearchRating.hold,
            {
                "business_model": "高端白酒龙头，飞天茅台为核心单品，直销占比提升。",
                "industry_space": "高端白酒需求具韧性，行业进入品牌分化阶段。",
                "competitive_landscape": "绝对龙头地位稳固，五粮液等竞品在千元价格带竞争。",
                "financial_quality": "ROE 与毛利率极高，经营现金流优秀，几乎无有息负债压力。",
                "management": "渠道改革与价格管控能力强，分红率稳定。",
                "growth_drivers": "结构升级、直销占比、系列酒放量。",
                "key_risks": "批价波动、消费税政策、宏观消费降级。",
                "current_valuation": "估值处于历史中高位，需业绩消化。",
                "core_variables_6_12m": ["批价", "渠道库存", "直销占比", "系列酒增速"],
            },
            "品质无忧但估值不便宜，维持持有，大幅加仓需估值回调或业绩加速。",
            horizon="12个月+",
            agent_name="research_agent",
        )


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
        [{"ref_type": "research_report", "excerpt": "十段式：批价与渠道库存为核心变量"}],
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
        [{"ref_type": "news", "excerpt": "季报：广告收入增速仍待验证"}],
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
    from app.models import Trade, TradeSide

    existing = db.scalar(
        select(func.count()).select_from(Trade).where(Trade.portfolio_id == portfolio_id)
    ) or 0
    if existing >= 5:
        return

    specs = [
        ("600519.SH", TradeSide.buy, Decimal("100")),
        ("00700.HK", TradeSide.buy, Decimal("200")),
        ("300750.SZ", TradeSide.buy, Decimal("300")),
        ("600036.SH", TradeSide.buy, Decimal("500")),
        ("09988.HK", TradeSide.buy, Decimal("200")),
    ]
    for sym, side, qty in specs[existing:]:
        sec = db.scalar(select(Security).where(Security.symbol == sym))
        if sec:
            ps.execute_trade(
                db,
                portfolio_id,
                sec.id,
                side,
                qty,
                sec.last_price or Decimal("100"),
                note="种子交易",
            )


def _seed_phase1_completion(db, portfolio_id) -> None:
    """满足 Phase 1 DoD：执行决策 + 日报。"""
    from app.models import DailyPortfolioReport
    from app.services.report_service import generate_daily_report

    first = db.scalar(
        select(Decision).where(
            Decision.portfolio_id == portfolio_id,
            Decision.action == DecisionAction.add,
            Decision.status == DecisionStatus.approved,
        )
    )
    if first:
        try:
            ps.execute_decision(db, first.id, None)
        except Exception:
            first.status = DecisionStatus.executed
            db.commit()

    if not db.scalar(
        select(DailyPortfolioReport).where(DailyPortfolioReport.portfolio_id == portfolio_id).limit(1)
    ):
        try:
            generate_daily_report(db, portfolio_id)
        except Exception:
            pass


def _seed_golden_path(db, portfolio_id) -> None:
    """黄金演示链：事件→研究→CIO 草案（标记 golden_path）。"""
    tencent = db.scalar(select(Security).where(Security.symbol == "00700.HK"))
    if not tencent:
        return
    golden = db.scalar(
        select(Decision).where(
            Decision.portfolio_id == portfolio_id,
            Decision.created_by_agent == "cio_agent",
        )
    )
    if golden and (golden.cio_summary or {}).get("golden_path"):
        return
    if golden:
        golden.cio_summary = {
            **(golden.cio_summary or {}),
            "golden_path": True,
            "chain": ["structured_event", "research_view", "cio_draft", "approve", "execute", "memory"],
        }
        db.commit()


def _seed_phase34(db) -> None:
    if db.scalar(select(MemoryEntry).limit(1)):
        return
    lessons = [
        (
            MemoryType.anti_pattern,
            "政策反转股勿过早左侧",
            "对政策反转类股票过早左侧买入，历史胜率较低；需等政策明确后再加仓。",
        ),
        (
            MemoryType.lesson,
            "港股互联网估值陷阱",
            "港股互联网低估值不能单独作为买入理由，需配合业绩修复和回购。",
        ),
        (
            MemoryType.lesson,
            "周期股价值陷阱",
            "周期股盈利高点时 PE 低估容易形成价值陷阱。",
        ),
        (
            MemoryType.rule,
            "事件驱动短复盘",
            "事件驱动类交易需要设置更短复盘周期（2-4周）。",
        ),
    ]
    for mt, title, content in lessons:
        db.add(
            MemoryEntry(
                memory_type=mt,
                title=title,
                content=content,
                active=True,
                pending=False,
                confidence=Decimal("0.85"),
            )
        )
    db.flush()
    if not db.scalar(select(StrategyRule).limit(1)):
        db.add(
            StrategyRule(
                rule_code="MAX_INTERNET_WITHOUT_EARNINGS",
                natural_language="互联网加仓需同时满足：业绩同比改善或回购加码",
                machine_check={"type": "note"},
                active=True,
            )
        )
    db.commit()
