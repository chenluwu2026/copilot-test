"""AkShare 数据源：A 股/港股日线、公告、财报摘要。"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd

logger = logging.getLogger(__name__)


def _import_ak():
    import akshare as ak

    return ak


def fetch_a_daily_bars(symbol: str, start: date, end: date) -> list[dict]:
    from app.data_connectors.symbol_utils import to_akshare_a_code

    ak = _import_ak()
    ak_code = to_akshare_a_code(symbol)
    df = ak.stock_zh_a_daily(symbol=ak_code, adjust="qfq")
    if df is None or df.empty:
        return []
    df = df.rename(columns={"date": "bar_date"})
    df["bar_date"] = pd.to_datetime(df["bar_date"]).dt.date
    mask = (df["bar_date"] >= start) & (df["bar_date"] <= end)
    df = df.loc[mask]
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "bar_date": r["bar_date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r.get("volume", 0) or 0),
                "turnover": float(r.get("amount", 0) or 0),
                "turnover_rate": float(r.get("turnover", 0) or 0) * 100
                if r.get("turnover", 0) and r.get("turnover", 0) < 1
                else float(r.get("turnover", 0) or 0),
            }
        )
    return rows


def fetch_hk_daily_bars(symbol: str, start: date, end: date) -> list[dict]:
    from app.data_connectors.symbol_utils import to_akshare_hk_code

    ak = _import_ak()
    code = to_akshare_hk_code(symbol)
    df = ak.stock_hk_hist(
        symbol=code,
        period="daily",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        adjust="qfq",
    )
    if df is None or df.empty:
        return []
    col_map = {"日期": "bar_date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "volume", "成交额": "turnover", "换手率": "turnover_rate"}
    df = df.rename(columns=col_map)
    df["bar_date"] = pd.to_datetime(df["bar_date"]).dt.date
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "bar_date": r["bar_date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r.get("volume", 0) or 0),
                "turnover": float(r.get("turnover", 0) or 0),
                "turnover_rate": float(r.get("turnover_rate", 0) or 0),
            }
        )
    return rows


def fetch_daily_bars(symbol: str, market: str, start: date, end: date) -> list[dict]:
    if market == "HK":
        return fetch_hk_daily_bars(symbol, start, end)
    return fetch_a_daily_bars(symbol, start, end)


def fetch_a_notices(symbol: str, start: date, end: date) -> list[dict]:
    from app.data_connectors.symbol_utils import parse_symbol

    code, _ = parse_symbol(symbol)
    ak = _import_ak()
    items: list[dict] = []
    try:
        df = ak.stock_individual_notice_report(
            security=code,
            begin_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
        )
        if df is not None and not df.empty:
            for _, r in df.iterrows():
                items.append(
                    {
                        "title": str(r.get("公告标题", "")),
                        "filing_type": str(r.get("公告类型", "公告")),
                        "published_at": _parse_date(r.get("公告日期")),
                        "source_url": str(r.get("网址", "")),
                        "raw_content": str(r.get("公告标题", "")),
                    }
                )
    except Exception as e:
        logger.warning("stock_individual_notice_report failed: %s", e)

    try:
        df2 = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            category="",
        )
        if df2 is not None and not df2.empty:
            for _, r in df2.iterrows():
                title = str(r.get("公告标题", ""))
                if any(x["title"] == title for x in items):
                    continue
                items.append(
                    {
                        "title": title,
                        "filing_type": _guess_filing_type(title),
                        "published_at": _parse_date(r.get("公告时间")),
                        "source_url": str(r.get("公告链接", "")),
                        "raw_content": title,
                    }
                )
    except Exception as e:
        logger.warning("cninfo disclosure failed: %s", e)
    return items


def fetch_a_financial_abstract(symbol: str) -> dict:
    from app.data_connectors.symbol_utils import parse_symbol

    code, _ = parse_symbol(symbol)
    ak = _import_ak()
    df = ak.stock_financial_abstract(symbol=code)
    if df is None or df.empty:
        return {}
    period_cols = [c for c in df.columns if c not in ("选项", "指标") and str(c).isdigit()]
    period_cols = sorted(period_cols, reverse=True)[:6]
    metrics: dict[str, dict[str, float | None]] = {}
    for _, row in df.iterrows():
        indicator = str(row.get("指标", ""))
        if not indicator:
            continue
        metrics[indicator] = {}
        for col in period_cols:
            val = row.get(col)
            try:
                metrics[indicator][str(col)] = float(val) if pd.notna(val) else None
            except (TypeError, ValueError):
                metrics[indicator][str(col)] = None
    return {
        "periods": period_cols,
        "metrics": metrics,
        "report_type": "abstract",
        "source": "akshare",
    }


def fetch_hk_financial_report(symbol: str) -> dict:
    from app.data_connectors.symbol_utils import to_akshare_hk_code

    ak = _import_ak()
    code = to_akshare_hk_code(symbol)
    try:
        df = ak.stock_financial_hk_report_em(stock=code, symbol="资产负债表", indicator="年度")
        if df is None or df.empty:
            return {}
        return {
            "report_type": "hk_balance_annual",
            "source": "akshare",
            "data": df.head(20).to_dict(orient="records"),
        }
    except Exception as e:
        logger.warning("hk financial failed: %s", e)
        return {}


def _parse_date(val) -> datetime:
    if val is None:
        return datetime.utcnow()
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    try:
        return pd.to_datetime(val).to_pydatetime()
    except Exception:
        return datetime.utcnow()


def _guess_filing_type(title: str) -> str:
    for key, ft in [
        ("年报", "annual_report"),
        ("半年报", "semi_annual"),
        ("季报", "quarterly_report"),
        ("一季度", "quarterly_report"),
        ("三季度", "quarterly_report"),
        ("回购", "buyback"),
        ("减持", "insider_selling"),
        ("增持", "insider_buying"),
        ("股权激励", "equity_incentive"),
        ("并购", "mna"),
        ("业绩预告", "earnings_guidance"),
        ("业绩", "earnings"),
    ]:
        if key in title:
            return ft
    return "announcement"
