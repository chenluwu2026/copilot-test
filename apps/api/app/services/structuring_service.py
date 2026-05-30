"""将非结构化新闻转为 structured_event（Phase 2：规则引擎，可替换为 LLM）。"""
import re
from datetime import datetime, timezone
from uuid import UUID

import jsonschema
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ConfidenceLevel,
    ImpactDirection,
    NewsArticle,
    Security,
    SourceType,
    StructuredEvent,
)
from app.services.decision_service import _load_schema


EVENT_KEYWORDS: dict[str, list[str]] = {
    "earnings_release": ["业绩", "财报", "季报", "年报", "盈利", "营收", "净利润"],
    "buyback": ["回购", "增持"],
    "regulation": ["监管", "处罚", "立案", "反垄断"],
    "product_launch": ["发布", "上线", "新品"],
    "macro_policy": ["政策", "降准", "降息", "国务院"],
    "industry_trend": ["行业", "景气", "产能"],
}


def detect_event_type(text: str) -> str:
    for event_type, keywords in EVENT_KEYWORDS.items():
        if any(k in text for k in keywords):
            return event_type
    return "general_news"


def detect_impact(text: str) -> ImpactDirection:
    pos = ["增长", "超预期", "上调", "突破", "回购", "利好", "复苏", "盈利"]
    neg = ["下滑", "不及预期", "下调", "亏损", "调查", "利空", "减持", "处罚"]
    p = sum(1 for k in pos if k in text)
    n = sum(1 for k in neg if k in text)
    if p > n and p > 0:
        return ImpactDirection.positive
    if n > p and n > 0:
        return ImpactDirection.negative
    if p > 0 and n > 0:
        return ImpactDirection.mixed
    return ImpactDirection.neutral


def detect_dimensions(text: str) -> list[str]:
    dims = []
    mapping = {
        "收入": ["收入", "营收", "销售额"],
        "利润率": ["利润", "毛利", "净利", "margin"],
        "回购": ["回购"],
        "监管": ["监管", "合规"],
        "估值": ["估值", "PE", "市盈率"],
        "市场份额": ["份额", "市占"],
    }
    for dim, keys in mapping.items():
        if any(k in text for k in keys):
            dims.append(dim)
    return dims or ["综合"]


def structure_from_text(
    title: str,
    body: str,
    securities: list[Security],
) -> dict:
    text = f"{title} {body or ''}"
    event_type = detect_event_type(text)
    impact = detect_impact(text)
    companies = [
        {"security_id": str(s.id), "symbol": s.symbol, "name": s.name} for s in securities
    ]
    related = companies[1:] if len(companies) > 1 else []
    sensitivity = (
        ConfidenceLevel.high
        if event_type in ("earnings_release", "regulation")
        else ConfidenceLevel.medium
    )
    follow_ups = []
    if event_type == "earnings_release":
        follow_ups.append("下一季度收入与利润率指引")
    if "游戏" in text or "腾讯" in text:
        follow_ups.append("游戏流水与广告收入增速")
    if not follow_ups:
        follow_ups.append("后续公告与股价反应")

    payload = {
        "companies": [{"symbol": c["symbol"], "name": c["name"]} for c in companies],
        "event_type": event_type,
        "impact_direction": impact.value,
        "impact_dimensions": detect_dimensions(text),
        "confidence": ConfidenceLevel.medium.value,
        "time_sensitivity": sensitivity.value,
        "related_securities": [
            {"symbol": r["symbol"]} for r in related
        ],
        "follow_ups": follow_ups,
        "summary": title[:500],
    }
    jsonschema.validate(instance=payload, schema=_load_schema("structured_event.schema.json"))
    return payload


def ingest_news(
    db: Session,
    title: str,
    body: str,
    security_ids: list[UUID],
    source_name: str = "manual",
    source_url: str | None = None,
    published_at: datetime | None = None,
) -> tuple[NewsArticle, StructuredEvent]:
    published_at = published_at or datetime.now(timezone.utc)
    securities = [db.get(Security, sid) for sid in security_ids]
    securities = [s for s in securities if s]

    article = NewsArticle(
        title=title,
        body=body,
        source_name=source_name,
        source_url=source_url,
        published_at=published_at,
    )
    db.add(article)
    db.flush()

    structured = structure_from_text(title, body or "", securities)
    companies = [
        {"security_id": str(s.id), "symbol": s.symbol, "name": s.name} for s in securities
    ]
    related = []
    for item in structured.get("related_securities", []):
        sym = item.get("symbol")
        sec = next((s for s in securities if s.symbol == sym), None)
        if sec:
            related.append({"security_id": str(sec.id), "symbol": sec.symbol})

    event = StructuredEvent(
        source_type=SourceType.news,
        source_id=article.id,
        companies=companies,
        event_type=structured["event_type"],
        impact_direction=ImpactDirection(structured["impact_direction"]),
        impact_dimensions=structured["impact_dimensions"],
        confidence=ConfidenceLevel(structured["confidence"]),
        time_sensitivity=ConfidenceLevel(structured["time_sensitivity"]),
        related_securities=related,
        follow_ups=structured["follow_ups"],
        summary=structured["summary"],
        published_at=published_at,
    )
    db.add(event)
    db.commit()
    db.refresh(article)
    db.refresh(event)
    return article, event


def event_to_dict(event: StructuredEvent, article: NewsArticle | None = None) -> dict:
    return {
        "id": str(event.id),
        "source_type": event.source_type.value,
        "source_id": str(event.source_id) if event.source_id else None,
        "companies": event.companies,
        "event_type": event.event_type,
        "impact_direction": event.impact_direction.value,
        "impact_dimensions": event.impact_dimensions,
        "confidence": event.confidence.value,
        "time_sensitivity": event.time_sensitivity.value,
        "related_securities": event.related_securities,
        "follow_ups": event.follow_ups,
        "summary": event.summary,
        "published_at": event.published_at.isoformat(),
        "article": (
            {
                "title": article.title,
                "body": article.body,
                "source_name": article.source_name,
                "source_url": article.source_url,
            }
            if article
            else None
        ),
    }
