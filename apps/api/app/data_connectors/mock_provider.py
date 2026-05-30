"""离线/CI 回退：基于种子价生成合成 K 线。"""
import random
from datetime import date, timedelta


def fetch_daily_bars(symbol: str, market: str, start: date, end: date, base_price: float = 100) -> list[dict]:
    rows = []
    d = start
    price = base_price
    rng = random.Random(symbol)
    while d <= end:
        chg = rng.uniform(-0.03, 0.03)
        open_p = price
        close_p = price * (1 + chg)
        high_p = max(open_p, close_p) * (1 + rng.uniform(0, 0.01))
        low_p = min(open_p, close_p) * (1 - rng.uniform(0, 0.01))
        rows.append(
            {
                "bar_date": d,
                "open": round(open_p, 4),
                "high": round(high_p, 4),
                "low": round(low_p, 4),
                "close": round(close_p, 4),
                "volume": float(rng.randint(100000, 5000000)),
                "turnover": float(rng.randint(1_000_000, 100_000_000)),
                "turnover_rate": round(rng.uniform(0.1, 2.5), 4),
            }
        )
        price = close_p
        d += timedelta(days=1)
    return rows


def fetch_a_notices(symbol: str, start: date, end: date) -> list[dict]:
    from datetime import datetime

    return [
        {
            "title": f"[Mock] {symbol} 季度报告摘要",
            "filing_type": "quarterly_report",
            "published_at": datetime.combine(end, datetime.min.time()),
            "source_url": "",
            "raw_content": "模拟公告数据（网络不可用时的回退）",
        }
    ]


def fetch_a_financial_abstract(symbol: str) -> dict:
    return {
        "periods": ["20250331", "20241231"],
        "metrics": {
            "归母净利润": {"20250331": 1e10, "20241231": 9e9},
            "营业总收入": {"20250331": 5e10, "20241231": 4.8e10},
        },
        "report_type": "abstract",
        "source": "mock",
    }
