import os
import unittest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Market, Portfolio, Security, User, Watchlist, WatchlistItem, WatchlistTier
from app.services import decision_ledger_service as dls
from app.services.fm_daily_run_service import run_fm_daily


def _db_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///:memory:"


class FmDailyRunTests(unittest.TestCase):
    def setUp(self):
        url = _db_url()
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, **kw)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

        user = User(email=f"fm-{uuid4().hex[:8]}@example.com", display_name="fm")
        self.db.add(user)
        self.db.commit()
        self.portfolio = Portfolio(
            user_id=user.id,
            name="FM",
            initial_cash=Decimal("1000000"),
            cash_balance=Decimal("800000"),
            risk_limits={"max_single_name_pct": 10, "max_sector_pct": 30, "min_cash_pct": 5, "max_adv_pct": 40},
        )
        self.db.add(self.portfolio)
        self.db.flush()
        sec = Security(
            symbol=f"FM.{uuid4().hex[:6]}.HK",
            name="FM Test",
            market=Market.HK,
            currency="HKD",
            sector="科技",
            lot_size=100,
            last_price=Decimal("100"),
            meta={"avg_daily_turnover": 500000},
        )
        self.db.add(sec)
        self.db.flush()
        wl = Watchlist(user_id=user.id, name="core")
        self.db.add(wl)
        self.db.flush()
        self.db.add(
            WatchlistItem(
                watchlist_id=wl.id,
                security_id=sec.id,
                tier=WatchlistTier.core,
            )
        )
        self.db.commit()
        self.sec = sec

    def tearDown(self):
        self.db.close()

    def test_daily_run_creates_pipeline_decisions(self):
        out = run_fm_daily(self.db, portfolio_id=self.portfolio.id, auto_approve=False)
        self.assertTrue(out["run_id"].startswith("fm-"))
        self.assertGreaterEqual(out["candidate_count"], 1)
        self.assertIsNotNone(out["pipeline"])
        self.assertGreaterEqual(out["counts"]["created_decisions"], 1)

    def test_list_run_summaries_after_daily_run(self):
        out = run_fm_daily(self.db, portfolio_id=self.portfolio.id, auto_approve=False)
        runs = dls.list_run_summaries(self.db, self.portfolio.id)
        self.assertTrue(any(r["run_id"] == out["run_id"] for r in runs))
        detail = dls.list_ledgers_by_run(
            self.db, portfolio_id=self.portfolio.id, run_id=out["run_id"]
        )
        self.assertGreaterEqual(len(detail), 1)


if __name__ == "__main__":
    unittest.main()
