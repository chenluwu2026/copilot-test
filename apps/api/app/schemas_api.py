from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class SecurityOut(BaseModel):
    id: UUID
    symbol: str
    name: str
    market: str
    currency: str
    sector: str | None
    lot_size: int
    last_price: float | None

    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    name: str = "主模拟组合"
    initial_cash: float = 1_000_000
    base_currency: str = "CNY"
    benchmark_symbol: str | None = "CSI300"


class PortfolioOut(BaseModel):
    id: UUID
    name: str
    cash_balance: float
    initial_cash: float
    base_currency: str
    benchmark_symbol: str | None

    class Config:
        from_attributes = True


class TradeCreate(BaseModel):
    security_id: UUID
    side: str
    quantity: float
    price: float
    trade_date: date | None = None
    note: str | None = None


class TradeOut(BaseModel):
    id: UUID
    security_id: UUID
    side: str
    quantity: float
    price: float
    amount: float
    commission: float
    trade_date: date
    source: str
    symbol: str | None = None
    name: str | None = None

    class Config:
        from_attributes = True


class AssumptionIn(BaseModel):
    text: str
    measurable: bool = False
    metric_key: str | None = None
    target_value: str | None = None
    deadline: date | None = None


class ReferenceIn(BaseModel):
    ref_type: str
    ref_id: str | None = None
    excerpt: str | None = None


class DecisionCreate(BaseModel):
    portfolio_id: UUID
    security_id: UUID
    action: str
    decision_reason: str
    current_weight_pct: float = 0
    target_weight_pct: float = 0
    main_risks: list[str] = Field(default_factory=list)
    review_conditions: list[str] = Field(default_factory=list)
    assumptions: list[AssumptionIn] = Field(default_factory=list)
    references: list[ReferenceIn] = Field(default_factory=list)
    confidence_grade: str | None = None
    holding_period: str | None = None
    cio_summary: dict | None = None


class DecisionStatusUpdate(BaseModel):
    status: str


class DecisionExecute(BaseModel):
    price: float | None = None


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    correction: str | None = None
    tags: list[str] = Field(default_factory=list)


class WatchlistCreate(BaseModel):
    name: str
    description: str | None = None


class WatchlistItemCreate(BaseModel):
    security_id: UUID
    tier: str = "track"
    thesis_summary: str | None = None


class NavOut(BaseModel):
    snapshot_date: date
    nav: float
    daily_return_pct: float | None
    cumulative_return_pct: float | None
    drawdown_pct: float | None

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: UUID
    report_date: date
    summary_md: str
    metrics: dict

    class Config:
        from_attributes = True
