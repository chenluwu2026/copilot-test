import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.config import settings

if settings.database_url.startswith("sqlite"):
    UUID = Uuid
    JSONType = JSON
else:
    UUID = PG_UUID
    JSONType = JSONB


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Market(str, enum.Enum):
    CN_A = "CN_A"
    HK = "HK"
    US = "US"


class WatchlistTier(str, enum.Enum):
    core = "core"
    track = "track"
    idea = "idea"


class TradeSide(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class TradeSource(str, enum.Enum):
    manual = "manual"
    agent = "agent"
    rebalance = "rebalance"


class DecisionAction(str, enum.Enum):
    buy = "buy"
    sell = "sell"
    hold = "hold"
    add = "add"
    reduce = "reduce"
    watch = "watch"
    ban = "ban"


class DecisionStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    executed = "executed"
    cancelled = "cancelled"
    superseded = "superseded"


class ReferenceType(str, enum.Enum):
    news = "news"
    filing = "filing"
    research_report = "research_report"
    valuation = "valuation"
    factor = "factor"
    user_note = "user_note"
    memory = "memory"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    investment_profile: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="user")
    watchlists: Mapped[list["Watchlist"]] = relationship(back_populates="user")


class Security(Base):
    __tablename__ = "securities"
    __table_args__ = (UniqueConstraint("symbol", "market", name="uq_security_symbol_market"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    market: Mapped[Market] = mapped_column(Enum(Market), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    sector: Mapped[str | None] = mapped_column(String(64))
    industry: Mapped[str | None] = mapped_column(String(64))
    lot_size: Mapped[int] = mapped_column(default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("1000000"))
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("1000000"))
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32))
    risk_limits: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")

    user: Mapped["User"] = relationship(back_populates="portfolios")
    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio")
    trades: Mapped[list["Trade"]] = relationship(back_populates="portfolio")
    nav_snapshots: Mapped[list["NavSnapshot"]] = relationship(back_populates="portfolio")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="portfolio")
    reports: Mapped[list["DailyPortfolioReport"]] = relationship(back_populates="portfolio")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "security_id", name="uq_position"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    security_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("securities.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=Decimal("0"))
    market_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    weight_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    opened_at: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    portfolio: Mapped["Portfolio"] = relationship(back_populates="positions")
    security: Mapped["Security"] = relationship()


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    security_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("securities.id"), nullable=False)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("decisions.id"))
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[TradeSource] = mapped_column(Enum(TradeSource), default=TradeSource.manual)
    note: Mapped[str | None] = mapped_column(Text)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="trades")
    security: Mapped["Security"] = relationship()


class NavSnapshot(Base):
    __tablename__ = "nav_snapshots"
    __table_args__ = (UniqueConstraint("portfolio_id", "snapshot_date", name="uq_nav_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    gross_exposure: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    daily_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    cumulative_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    drawdown_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))

    portfolio: Mapped["Portfolio"] = relationship(back_populates="nav_snapshots")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="watchlists")
    items: Mapped[list["WatchlistItem"]] = relationship(back_populates="watchlist", cascade="all, delete")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("watchlist_id", "security_id", name="uq_watchlist_item"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"))
    security_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("securities.id"), nullable=False)
    tier: Mapped[WatchlistTier] = mapped_column(Enum(WatchlistTier), default=WatchlistTier.track)
    thesis_summary: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    security: Mapped["Security"] = relationship()


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    security_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("securities.id"), nullable=False)
    action: Mapped[DecisionAction] = mapped_column(Enum(DecisionAction), nullable=False)
    current_weight_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    target_weight_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    delta_weight_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    status: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus), default=DecisionStatus.draft)
    confidence_grade: Mapped[str | None] = mapped_column(String(8))
    holding_period: Mapped[str | None] = mapped_column(String(32))
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    main_risks: Mapped[list] = mapped_column(JSONType, default=list)
    review_conditions: Mapped[list] = mapped_column(JSONType, default=list)
    cio_summary: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_by_agent: Mapped[str] = mapped_column(String(64), default="human")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    portfolio: Mapped["Portfolio"] = relationship(back_populates="decisions")
    security: Mapped["Security"] = relationship()
    assumptions: Mapped[list["DecisionAssumption"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    references: Mapped[list["DecisionReference"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["UserFeedback"]] = relationship(back_populates="decision")


class DecisionAssumption(Base):
    __tablename__ = "decision_assumptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"))
    assumption_text: Mapped[str] = mapped_column(Text, nullable=False)
    measurable: Mapped[bool] = mapped_column(Boolean, default=False)
    metric_key: Mapped[str | None] = mapped_column(String(64))
    target_value: Mapped[str | None] = mapped_column(String(64))
    deadline: Mapped[date | None] = mapped_column(Date)

    decision: Mapped["Decision"] = relationship(back_populates="assumptions")


class DecisionReference(Base):
    __tablename__ = "decision_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"))
    ref_type: Mapped[ReferenceType] = mapped_column(Enum(ReferenceType), nullable=False)
    ref_id: Mapped[str | None] = mapped_column(String(64))
    excerpt: Mapped[str | None] = mapped_column(Text)
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    decision: Mapped["Decision"] = relationship(back_populates="references")


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    correction: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision: Mapped["Decision"] = relationship(back_populates="feedbacks")


class ImpactDirection(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class ConfidenceLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SourceType(str, enum.Enum):
    news = "news"
    filing = "filing"
    social = "social"
    report = "report"


class ResearchRating(str, enum.Enum):
    strong_buy = "strong_buy"
    buy = "buy"
    hold = "hold"
    reduce = "reduce"
    sell = "sell"
    neutral = "neutral"


class ResearchViewType(str, enum.Enum):
    company = "company"
    industry = "industry"
    event = "event"


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(64), default="aims_seed")
    source_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StructuredEvent(Base):
    __tablename__ = "structured_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), default=SourceType.news)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    companies: Mapped[list] = mapped_column(JSONType, default=list)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    impact_direction: Mapped[ImpactDirection] = mapped_column(Enum(ImpactDirection))
    impact_dimensions: Mapped[list] = mapped_column(JSONType, default=list)
    confidence: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel))
    time_sensitivity: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel))
    related_securities: Mapped[list] = mapped_column(JSONType, default=list)
    follow_ups: Mapped[list] = mapped_column(JSONType, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResearchView(Base):
    __tablename__ = "research_views"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    security_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("securities.id"), nullable=False)
    view_type: Mapped[ResearchViewType] = mapped_column(
        Enum(ResearchViewType), default=ResearchViewType.company
    )
    rating: Mapped[ResearchRating] = mapped_column(Enum(ResearchRating), default=ResearchRating.neutral)
    horizon: Mapped[str | None] = mapped_column(String(32))
    content_structured: Mapped[dict] = mapped_column(JSONType, default=dict)
    valuation_snapshot: Mapped[dict] = mapped_column(JSONType, default=dict)
    scenario_analysis: Mapped[dict] = mapped_column(JSONType, default=dict)
    investment_conclusion: Mapped[str] = mapped_column(Text, default="")
    agent_name: Mapped[str] = mapped_column(String(64), default="research_agent")
    version: Mapped[int] = mapped_column(default=1)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    security: Mapped["Security"] = relationship()


class AgentRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class MemoryType(str, enum.Enum):
    lesson = "lesson"
    rule = "rule"
    anti_pattern = "anti_pattern"
    user_preference = "user_preference"


class OutcomeStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    invalidated = "invalidated"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("portfolios.id"))
    workflow_name: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus), default=AgentRunStatus.running)
    input_context: Mapped[dict] = mapped_column(JSONType, default=dict)
    output: Mapped[dict] = mapped_column(JSONType, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), unique=True)
    outcome_status: Mapped[OutcomeStatus] = mapped_column(Enum(OutcomeStatus), default=OutcomeStatus.open)
    return_since_decision_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    max_drawdown_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    assumption_results: Mapped[list] = mapped_column(JSONType, default=list)
    what_went_right: Mapped[list] = mapped_column(JSONType, default=list)
    what_went_wrong: Mapped[list] = mapped_column(JSONType, default=list)
    outcome_summary: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str] = mapped_column(String(64), default="review_agent")


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    memory_type: Mapped[MemoryType] = mapped_column(Enum(MemoryType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_decision_ids: Mapped[list] = mapped_column(JSONType, default=list)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0.8"))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    pending: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StrategyRule(Base):
    __tablename__ = "strategy_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    natural_language: Mapped[str] = mapped_column(Text, nullable=False)
    machine_check: Mapped[dict] = mapped_column(JSONType, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_memory_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyPortfolioReport(Base):
    __tablename__ = "daily_portfolio_reports"
    __table_args__ = (UniqueConstraint("portfolio_id", "report_date", name="uq_report_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONType, default=dict)
    top_movers: Mapped[list] = mapped_column(JSONType, default=list)
    agent_commentary: Mapped[dict] = mapped_column(JSONType, default=dict)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="reports")
