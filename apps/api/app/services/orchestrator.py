"""CIO 调仓工作流编排（Phase 3）。"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AgentRun,
    AgentRunStatus,
    Decision,
    DecisionAction,
    DecisionStatus,
    ResearchRating,
    ResearchView,
    Security,
)
from app.services import decision_service as ds
from app.services.factor_service import compute_factors
from app.services.memory_service import search_memory
from app.services.portfolio_agent_service import propose_weights
from app.services.portfolio_service import get_portfolio_summary
from app.services.risk_service import check_risk
from app.services.user_context import get_default_user

RATING_TO_ACTION = {
    ResearchRating.strong_buy: DecisionAction.add,
    ResearchRating.buy: DecisionAction.add,
    ResearchRating.hold: DecisionAction.hold,
    ResearchRating.neutral: DecisionAction.watch,
    ResearchRating.reduce: DecisionAction.reduce,
    ResearchRating.sell: DecisionAction.sell,
}


def run_rebalance_workflow(db: Session, portfolio_id: UUID, trigger: str = "manual") -> AgentRun:
    run = AgentRun(
        portfolio_id=portfolio_id,
        workflow_name="rebalance_cio",
        trigger=trigger,
        status=AgentRunStatus.running,
        input_context={"portfolio_id": str(portfolio_id)},
    )
    db.add(run)
    db.flush()

    trace: dict = {"steps": []}
    try:
        user = get_default_user(db)
        summary = get_portfolio_summary(db, portfolio_id)
        current_map = {p["symbol"]: p["weight_pct"] for p in summary["positions"]}

        from app.models import Position

        positions = db.scalars(
            select(Position).where(Position.portfolio_id == portfolio_id)
        ).all()
        universe_ids = [p.security_id for p in positions]
        from app.models import Watchlist, WatchlistItem

        for wl in db.scalars(select(Watchlist).where(Watchlist.user_id == user.id)):
            for item in db.scalars(
                select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
            ):
                if item.security_id not in universe_ids:
                    universe_ids.append(item.security_id)

        factors = compute_factors(db, universe_ids)
        trace["steps"].append({"agent": "factor_agent", "output": factors})

        portfolio_out = propose_weights(db, portfolio_id, user.id, factors)
        trace["steps"].append({"agent": "portfolio_agent", "output": portfolio_out})

        proposed = portfolio_out["proposed_weights"]
        risk_round = 0
        risk_result = check_risk(db, portfolio_id, proposed)
        while not risk_result["approved"] and risk_round < 2:
            proposed = risk_result["adjusted_weights"]
            risk_result = check_risk(db, portfolio_id, proposed)
            risk_round += 1
        trace["steps"].append({"agent": "risk_agent", "output": risk_result})

        memories = search_memory(db, "投资", limit=5)
        trace["memories"] = [{"title": m.title, "content": m.content} for m in memories]

        decision_ids = []
        cio_outputs = []
        for pw in proposed:
            symbol = pw["symbol"]
            target = float(pw["weight_pct"])
            current = float(current_map.get(symbol, 0))
            delta = target - current
            if abs(delta) < 1.0:
                continue

            sec = db.scalar(select(Security).where(Security.symbol == symbol))
            if not sec:
                continue
            view = db.scalar(
                select(ResearchView)
                .where(ResearchView.security_id == sec.id)
                .order_by(ResearchView.version.desc())
                .limit(1)
            )
            rating = view.rating if view else ResearchRating.hold
            if delta > 0:
                action = DecisionAction.add if current > 0 else DecisionAction.buy
            elif target <= 0.5:
                action = DecisionAction.sell if current > 1 else DecisionAction.watch
            else:
                action = DecisionAction.reduce

            if not risk_result["approved"] and action in (
                DecisionAction.buy,
                DecisionAction.add,
            ):
                action = DecisionAction.watch
                target = current

            reason = (
                f"[CIO Workflow] {pw.get('rationale', '')}。"
                f"目标权重 {target:.1f}%（当前 {current:.1f}%）。"
            )
            if memories:
                reason += f" 参考记忆：{memories[0].title}。"

            core_vars = []
            if view:
                fa = view.content_structured.get("fundamental_analysis", {})
                cv = fa.get("core_variables_6_12m", [])
                core_vars = cv if isinstance(cv, list) else [str(cv)]
            assumptions = [
                {
                    "text": core_vars[0] if core_vars else "价格与基本面一致",
                    "measurable": True,
                }
            ]
            review_conds = [
                "核心假设被证伪时复盘，非单纯价格止损",
                f"权重偏离目标超过 3% 且基本面无变化时检视",
            ]
            risks = (
                view.content_structured.get("fundamental_analysis", {}).get("key_risks", "")
                if view
                else "市场波动"
            )
            main_risks = [risks] if isinstance(risks, str) else list(risks)[:2] or ["市场波动"]

            decision = ds.create_decision(
                db,
                portfolio_id,
                sec.id,
                action,
                reason,
                current,
                target,
                main_risks,
                review_conds,
                assumptions,
                [{"ref_type": "valuation", "excerpt": view.investment_conclusion[:200]}]
                if view
                else [],
                "B" if abs(delta) < 3 else "B+",
                view.horizon if view else "3-6个月",
                cio_summary={
                    "security": {"symbol": symbol, "name": sec.name},
                    "action": action.value,
                    "research_rating": rating.value,
                    "current_weight_pct": current,
                    "target_weight_pct": target,
                    "delta_weight_pct": delta,
                    "decision_reason": reason,
                    "assumptions": assumptions,
                    "main_risks": main_risks,
                    "review_conditions": review_conds,
                    "confidence_grade": "B" if abs(delta) < 3 else "B+",
                    "holding_period": view.horizon if view else "3-6个月",
                    "decision_by": "cio_agent",
                },
                created_by_agent="cio_agent",
            )
            decision_ids.append(str(decision.id))
            cio_outputs.append(
                {
                    "decision_id": str(decision.id),
                    "symbol": symbol,
                    "action": action.value,
                    "current_weight_pct": current,
                    "target_weight_pct": target,
                }
            )

        run.status = AgentRunStatus.success
        run.output = {
            "decision_ids": decision_ids,
            "cio_decisions": cio_outputs,
            "trace": trace,
        }
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
    except Exception as e:
        run.status = AgentRunStatus.failed
        run.error_message = str(e)
        run.output = {"trace": trace}
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise


def list_agent_runs(db: Session, portfolio_id: UUID | None = None, limit: int = 20) -> list:
    q = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if portfolio_id:
        q = q.where(AgentRun.portfolio_id == portfolio_id)
    runs = db.scalars(q).all()
    return [
        {
            "id": str(r.id),
            "workflow_name": r.workflow_name,
            "status": r.status.value,
            "trigger": r.trigger,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "decision_ids": r.output.get("decision_ids", []) if r.output else [],
            "error_message": r.error_message,
        }
        for r in runs
    ]


def get_agent_run(db: Session, run_id: UUID) -> dict | None:
    r = db.get(AgentRun, run_id)
    if not r:
        return None
    return {
        "id": str(r.id),
        "workflow_name": r.workflow_name,
        "status": r.status.value,
        "input_context": r.input_context,
        "output": r.output,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }
