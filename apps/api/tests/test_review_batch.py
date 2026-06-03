import os
import unittest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Decision,
    DecisionAction,
    DecisionStatus,
    Market,
    Portfolio,
    Security,
    User,
)
from app.services.decision_service import batch_decision_actions, create_decision
from app.services.review_service import batch_review_decisions


def _db_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///:memory:"


class ReviewBatchTests(unittest.TestCase):
    def setUp(self):
        url = _db_url()
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, **kw)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

        user = User(email=f"rb-{uuid4().hex[:8]}@example.com", display_name="rb")
        self.db.add(user)
        self.db.commit()
        self.portfolio = Portfolio(
            user_id=user.id,
            name="RB",
            initial_cash=Decimal("1000000"),
            cash_balance=Decimal("1000000"),
        )
        self.db.add(self.portfolio)
        self.db.flush()
        sec = Security(
            symbol=f"RB.{uuid4().hex[:6]}.HK",
            name="RB",
            market=Market.HK,
            currency="HKD",
            lot_size=100,
            last_price=Decimal("50"),
        )
        self.db.add(sec)
        self.db.commit()
        self.sec = sec

    def tearDown(self):
        self.db.close()

    def test_batch_approve_draft_decisions(self):
        d1 = create_decision(
            self.db,
            self.portfolio.id,
            self.sec.id,
            action=DecisionAction.buy,
            decision_reason="b1",
            current_weight_pct=0,
            target_weight_pct=5,
            main_risks=[],
            review_conditions=[],
            assumptions=[],
            references=[{"ref_type": "news", "excerpt": "x"}],
        )
        d2 = create_decision(
            self.db,
            self.portfolio.id,
            self.sec.id,
            action=DecisionAction.add,
            decision_reason="b2",
            current_weight_pct=5,
            target_weight_pct=8,
            main_risks=[],
            review_conditions=[],
            assumptions=[],
            references=[{"ref_type": "news", "excerpt": "y"}],
        )
        out = batch_decision_actions(
            self.db,
            decision_ids=[d1.id, d2.id],
            action="approve",
        )
        self.assertEqual(out["succeeded"], 2)
        self.assertEqual(self.db.get(Decision, d1.id).status, DecisionStatus.approved)

    def test_batch_review_empty_when_no_executed(self):
        out = batch_review_decisions(
            self.db,
            portfolio_id=self.portfolio.id,
            urgency="all",
            limit=5,
        )
        self.assertEqual(out["requested"], 0)
        self.assertEqual(out["succeeded"], 0)


if __name__ == "__main__":
    unittest.main()
