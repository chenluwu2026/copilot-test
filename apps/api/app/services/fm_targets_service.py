"""最新 FM 批次目标权重（组合页 / 漂移对比）。"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Security
from app.services import decision_ledger_service as dls
from app.services.portfolio_service import get_portfolio_summary


def get_latest_fm_targets(db: Session, portfolio_id: UUID) -> dict:
    runs = dls.list_run_summaries(db, portfolio_id, limit=1)
    if not runs:
        return {
            "portfolio_id": str(portfolio_id),
            "run_id": None,
            "created_at": None,
            "rejection_rate_pct": 0.0,
            "targets": [],
            "cash_target_pct": None,
        }

    run = runs[0]
    run_id = run["run_id"]
    ledgers = dls.list_ledgers_by_run(db, portfolio_id=portfolio_id, run_id=run_id)
    sec_ids = list({l.security_id for l in ledgers})
    sec_map = {
        s.id: s
        for s in db.scalars(select(Security).where(Security.id.in_(sec_ids))) if sec_ids
    }

    summary = get_portfolio_summary(db, portfolio_id)
    current_by_sec = {
        str(p.get("security_id")): float(p.get("weight_pct") or 0)
        for p in summary.get("positions", [])
        if p.get("security_id")
    }

    seen: set[str] = set()
    targets: list[dict] = []
    allocated = 0.0
    for ledger in ledgers:
        prop = ledger.proposal_json or {}
        sid = str(ledger.security_id)
        if sid in seen:
            continue
        seen.add(sid)
        sec = sec_map.get(ledger.security_id)
        sym = prop.get("symbol") or (sec.symbol if sec else None)
        tw = float(prop.get("target_weight_pct") or 0)
        cw = current_by_sec.get(sid, float(prop.get("current_weight_pct") or 0))
        targets.append(
            {
                "security_id": sid,
                "symbol": sym,
                "name": sec.name if sec else None,
                "current_weight_pct": round(cw, 4),
                "target_weight_pct": round(tw, 4),
            }
        )
        allocated += tw

    pos_meta = {
        str(p.get("security_id")): p
        for p in summary.get("positions", [])
        if p.get("security_id")
    }
    for sid, cw in current_by_sec.items():
        if sid in seen or cw <= 0.01:
            continue
        meta = pos_meta.get(sid, {})
        targets.append(
            {
                "security_id": sid,
                "symbol": meta.get("symbol"),
                "name": meta.get("name"),
                "current_weight_pct": round(cw, 4),
                "target_weight_pct": round(cw, 4),
            }
        )

    targets.sort(key=lambda x: abs(x["target_weight_pct"] - x["current_weight_pct"]), reverse=True)
    cash_target = round(max(0.0, 100 - allocated), 4) if allocated else None

    return {
        "portfolio_id": str(portfolio_id),
        "run_id": run_id,
        "created_at": run.get("created_at"),
        "rejection_rate_pct": run.get("rejection_rate_pct", 0.0),
        "ledger_count": run.get("ledger_count", 0),
        "decision_count": run.get("decision_count", 0),
        "targets": targets,
        "cash_target_pct": cash_target,
    }
