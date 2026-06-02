"""决策回测质量指标（简化 Deflated Sharpe / 过拟合提示）。"""
import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, DecisionOutcome, OutcomeStatus


def _sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    if std == 0:
        return 0.0
    return mean / std * math.sqrt(252)


def backtest_quality_report(db: Session, portfolio_id: UUID) -> dict:
    rows = db.scalars(
        select(DecisionOutcome)
        .join(Decision)
        .where(
            Decision.portfolio_id == portfolio_id,
            DecisionOutcome.outcome_status == OutcomeStatus.closed,
        )
    ).all()
    returns = [float(o.return_since_decision_pct or 0) for o in rows]
    n = len(returns)
    if n < 3:
        return {
            "portfolio_id": str(portfolio_id),
            "sample_size": n,
            "sharpe": None,
            "deflated_sharpe_hint": None,
            "overfitting_risk": "insufficient_data",
            "message": "复盘样本不足 3 笔，无法评估回测质量",
        }

    sharpe = _sharpe(returns)
    # 简化 deflated：样本越多、夏普越高，风险越低
    trials_penalty = math.log(max(n, 2))
    deflated = sharpe - 0.5 * trials_penalty / math.sqrt(n)
    win_rate = sum(1 for r in returns if r > 0) / n

    if n < 8 or sharpe > 2.5 and win_rate > 0.85:
        risk = "elevated"
        msg = "样本偏少或胜率异常偏高，警惕过拟合叙事"
    elif deflated < 0:
        risk = "weak"
        msg = "风险调整后收益偏弱，宜降低仓位或收紧闸门"
    else:
        risk = "moderate"
        msg = "回测质量可接受，继续积累复盘样本"

    return {
        "portfolio_id": str(portfolio_id),
        "sample_size": n,
        "sharpe": round(sharpe, 3),
        "deflated_sharpe_hint": round(deflated, 3),
        "win_rate_pct": round(win_rate * 100, 1),
        "overfitting_risk": risk,
        "message": msg,
    }
