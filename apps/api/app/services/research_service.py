import json
from uuid import UUID

import jsonschema
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import ResearchRating, ResearchView, ResearchViewType, Security
from app.services.decision_service import _load_schema


def validate_research_payload(content: dict, rating: str, security: Security) -> dict:
    payload = {
        "security": {
            "security_id": str(security.id),
            "symbol": security.symbol,
            "name": security.name,
        },
        "rating": rating,
        "horizon": content.get("horizon", "6-12个月"),
        "fundamental_analysis": content["fundamental_analysis"],
        "investment_conclusion": content["investment_conclusion"],
    }
    if content.get("scenario_analysis"):
        payload["scenario_analysis"] = content["scenario_analysis"]
    schema = dict(_load_schema("research_view.schema.json"))
    props = dict(schema.get("properties", {}))
    props["scenario_analysis"] = {"type": "object"}
    schema["properties"] = props
    jsonschema.validate(instance=payload, schema=schema)
    return payload


def list_research_summaries(db: Session) -> list[dict]:
    """每只股票最新一条研究观点摘要。"""
    securities = db.scalars(select(Security).where(Security.is_active.is_(True))).all()
    result = []
    for sec in securities:
        view = db.scalar(
            select(ResearchView)
            .where(ResearchView.security_id == sec.id)
            .order_by(ResearchView.version.desc(), ResearchView.created_at.desc())
            .limit(1)
        )
        if view:
            result.append(_view_summary(sec, view))
    return sorted(result, key=lambda x: x["symbol"])


def get_research_by_symbol(db: Session, symbol: str) -> dict | None:
    sec = db.scalar(select(Security).where(Security.symbol == symbol))
    if not sec:
        return None
    views = db.scalars(
        select(ResearchView)
        .where(ResearchView.security_id == sec.id)
        .order_by(ResearchView.version.desc())
    ).all()
    if not views:
        return None
    latest = views[0]
    events_from_db = []  # filled by router with event service
    return {
        "security": {
            "id": str(sec.id),
            "symbol": sec.symbol,
            "name": sec.name,
            "sector": sec.sector,
            "last_price": float(sec.last_price) if sec.last_price else None,
        },
        "latest": _view_detail(latest),
        "history": [_view_detail(v) for v in views[1:6]],
    }


def _view_summary(sec: Security, view: ResearchView) -> dict:
    fa = view.content_structured.get("fundamental_analysis", {})
    return {
        "security_id": str(sec.id),
        "symbol": sec.symbol,
        "name": sec.name,
        "sector": sec.sector,
        "rating": view.rating.value,
        "horizon": view.horizon,
        "version": view.version,
        "investment_conclusion": view.investment_conclusion[:120],
        "updated_at": view.created_at.isoformat() if view.created_at else None,
    }


def _view_detail(view: ResearchView) -> dict:
    return {
        "id": str(view.id),
        "rating": view.rating.value,
        "horizon": view.horizon,
        "version": view.version,
        "agent_name": view.agent_name,
        "created_at": view.created_at.isoformat() if view.created_at else None,
        "fundamental_analysis": view.content_structured.get("fundamental_analysis", {}),
        "investment_conclusion": view.investment_conclusion,
        "valuation_snapshot": view.valuation_snapshot,
        "scenario_analysis": view.scenario_analysis,
    }


def create_research_view(
    db: Session,
    security_id: UUID,
    rating: ResearchRating,
    fundamental_analysis: dict,
    investment_conclusion: str,
    horizon: str = "6-12个月",
    scenario_analysis: dict | None = None,
    valuation_snapshot: dict | None = None,
    agent_name: str = "human",
) -> ResearchView:
    security = db.get(Security, security_id)
    if not security:
        raise ValueError("标的不存在")

    content = {
        "horizon": horizon,
        "fundamental_analysis": fundamental_analysis,
        "investment_conclusion": investment_conclusion,
        "scenario_analysis": scenario_analysis,
    }
    validate_research_payload(content, rating.value, security)

    prev = db.scalar(
        select(ResearchView)
        .where(ResearchView.security_id == security_id)
        .order_by(ResearchView.version.desc())
        .limit(1)
    )
    version = (prev.version + 1) if prev else 1

    view = ResearchView(
        security_id=security_id,
        view_type=ResearchViewType.company,
        rating=rating,
        horizon=horizon,
        content_structured={"fundamental_analysis": fundamental_analysis},
        valuation_snapshot=valuation_snapshot or {},
        scenario_analysis=scenario_analysis or {},
        investment_conclusion=investment_conclusion,
        agent_name=agent_name,
        version=version,
        supersedes_id=prev.id if prev else None,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


def _generate_research_llm(db: Session, security: Security) -> ResearchView:
    from app.services.llm.client import use_llm_agents, complete_json
    from app.services.llm.prompts import RESEARCH_SYSTEM

    if not use_llm_agents():
        raise RuntimeError("LLM not active")
    price = float(security.last_price or 100)
    user = (
        f"标的：{security.symbol} {security.name}，行业：{security.sector or '未知'}，"
        f"现价约 {price} {security.currency}。请输出 research_view JSON。"
    )
    raw = complete_json(RESEARCH_SYSTEM, user)
    fa = raw.get("fundamental_analysis") or {}
    scenario = raw.get("scenario_analysis")
    if scenario and "current_price" not in scenario:
        scenario["current_price"] = price
    rating = ResearchRating.hold
    return create_research_view(
        db,
        security.id,
        rating,
        fa,
        raw.get("investment_conclusion", f"{security.name}：LLM 研究草稿。"),
        horizon=raw.get("horizon", "6-12个月"),
        scenario_analysis=scenario,
        valuation_snapshot={"source": "llm"},
        agent_name="research_agent_llm",
    )


def generate_research_draft(db: Session, security_id: UUID) -> ResearchView:
    """Research Agent：LLM 或规则模板生成可编辑草稿。"""
    security = db.get(Security, security_id)
    if not security:
        raise ValueError("标的不存在")

    from app.services.llm.client import use_llm_agents

    if use_llm_agents():
        try:
            return _generate_research_llm(db, security)
        except Exception:
            pass

    sector = security.sector or "综合"
    name = security.name
    templates = {
        "business_model": f"{name}主营业务集中在{sector}，收入结构需结合最新财报拆分。",
        "industry_space": f"{sector}行业中长期仍受宏观与政策影响，关注渗透率与龙头集中度。",
        "competitive_landscape": f"{name}在细分领域具备品牌/渠道/成本等优势，但竞争格局持续演化。",
        "financial_quality": "关注 ROE、经营现金流与负债率；非金融企业重点看应收与资本开支。",
        "management": "管理层战略执行力与资本配置（分红、回购、并购）是长期价值关键。",
        "growth_drivers": "新产品、海外扩张、提价能力与市场份额提升是主要增长来源。",
        "key_risks": "宏观需求、行业政策、竞争加剧与估值波动。",
        "current_valuation": "结合 PE/PB 历史分位数与同行对比；港股需关注流动性折价。",
        "core_variables_6_12m": [
            "收入增速",
            "利润率变化",
            "政策与监管",
            "回购/分红",
        ],
    }

    scenario = {
        "methods": ["PE", "historical_percentile"],
        "scenarios": [
            {
                "name": "optimistic",
                "probability_weight": 0.25,
                "target_price_low": float(security.last_price or 100) * 1.15,
                "target_price_high": float(security.last_price or 100) * 1.35,
                "triggers": ["业绩超预期", "政策利好"],
                "downside_risk_note": "",
            },
            {
                "name": "base",
                "probability_weight": 0.5,
                "target_price_low": float(security.last_price or 100) * 0.95,
                "target_price_high": float(security.last_price or 100) * 1.1,
                "triggers": ["业绩符合预期"],
                "downside_risk_note": "",
            },
            {
                "name": "pessimistic",
                "probability_weight": 0.25,
                "target_price_low": float(security.last_price or 100) * 0.7,
                "target_price_high": float(security.last_price or 100) * 0.9,
                "triggers": ["业绩不及预期", "监管风险"],
                "downside_risk_note": "估值与盈利双杀风险",
            },
        ],
        "current_price": float(security.last_price or 100),
        "currency": security.currency,
    }

    return create_research_view(
        db,
        security_id,
        ResearchRating.hold,
        templates,
        f"{name}：暂维持观察，待核心变量验证后再调整评级。",
        horizon="6-12个月",
        scenario_analysis=scenario,
        valuation_snapshot={"pe_ttm": None, "note": "待接入财报数据"},
        agent_name="research_agent",
    )
