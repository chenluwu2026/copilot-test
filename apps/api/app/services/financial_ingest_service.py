"""财报/公告文本解析（简化 HTML/纯文本 → 结构化指标）。"""
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FinancialReport, Security

_METRIC_PATTERNS = [
    (r"营业收入[：:\s]*([\d,.]+)\s*([亿万%]?)", "revenue"),
    (r"净利润[：:\s]*([\d,.]+)\s*([亿万%]?)", "net_income"),
    (r"毛利率[：:\s]*([\d,.]+)\s*%?", "gross_margin_pct"),
    (r"ROE[：:\s]*([\d,.]+)\s*%?", "roe_pct"),
    (r"市盈率[：:\s]*([\d,.]+)", "pe_ratio"),
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _parse_number(raw: str, unit: str) -> float | None:
    try:
        v = float(raw.replace(",", ""))
    except ValueError:
        return None
    if "亿" in unit:
        v *= 1e8
    elif "万" in unit:
        v *= 1e4
    return v


def parse_financial_text(text: str) -> dict:
    plain = _strip_html(text)
    metrics: dict = {}
    for pattern, key in _METRIC_PATTERNS:
        m = re.search(pattern, plain, re.I)
        if m:
            num = _parse_number(m.group(1), m.group(2) if m.lastindex >= 2 else "")
            if num is not None:
                metrics[key] = num
    return {
        "metrics": metrics,
        "excerpt_chars": len(plain),
        "parsed_fields": list(metrics.keys()),
    }


def ingest_financial_document(
    db: Session,
    security_id: UUID,
    *,
    period_key: str,
    report_type: str,
    raw_text: str,
) -> dict:
    sec = db.get(Security, security_id)
    if not sec:
        raise ValueError("标的不存在")
    parsed = parse_financial_text(raw_text)
    existing = db.scalar(
        select(FinancialReport).where(
            FinancialReport.security_id == security_id,
            FinancialReport.period_key == period_key,
            FinancialReport.report_type == report_type,
        )
    )
    metrics = {**(existing.metrics if existing else {}), **parsed["metrics"]}
    if existing:
        existing.metrics = metrics
        raw = dict(existing.raw_data or {})
        raw["ingest_source"] = "text"
        existing.raw_data = raw
        row = existing
    else:
        row = FinancialReport(
            security_id=security_id,
            period_key=period_key,
            report_type=report_type,
            metrics=metrics,
            raw_data={"ingest_source": "text"},
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "report_id": str(row.id),
        "security_id": str(security_id),
        "period_key": period_key,
        "metrics": metrics,
        "parsed": parsed,
    }
