import os
import unittest
from decimal import Decimal
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    DecisionAction,
    DecisionLedgerStatus,
    DecisionStatus,
    Market,
    Portfolio,
    Position,
    Security,
    User,
)
from app.services.decision_ledger_service import create_ledger, transition_ledger
from app.services.decision_ledger_service import get_latest_ledger_by_decision
from app.services.decision_pipeline_service import run_decision_pipeline
from app.services.decision_service import create_decision, update_decision_status
from app.services.execution_simulator_service import simulate_execution
from app.services.portfolio_construction_service import construct_target_weights
from app.services.portfolio_service import execute_decision
from app.services.pretrade_risk_service import run_pretrade_checks


def _db_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///:memory:"


class DecisionClosedLoopTests(unittest.TestCase):
    def setUp(self):
        url = _db_url()
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, **kw)
        Base.metadata.create_all(bind=self.engine)
        self.db = sessionmaker(bind=self.engine)()

        user = User(email="test@example.com", display_name="tester")
        self.db.add(user)
        self.db.commit()
        self.portfolio = Portfolio(
            user_id=user.id,
            name="test",
            initial_cash=Decimal("1000000"),
            cash_balance=Decimal("600000"),
            risk_limits={
                "max_single_name_pct": 10,
                "max_sector_pct": 30,
                "min_cash_pct": 5,
                "max_adv_pct": 20,
                "max_correlation": 0.85,
            },
        )
        self.db.add(self.portfolio)
        self.db.flush()
        self.sec1 = Security(
            symbol="AAA.HK",
            name="AAA",
            market=Market.HK,
            currency="HKD",
            sector="科技",
            lot_size=100,
            last_price=Decimal("100"),
            meta={"avg_daily_turnover": 1_000_000},
        )
        self.sec2 = Security(
            symbol="BBB.HK",
            name="BBB",
            market=Market.HK,
            currency="HKD",
            sector="消费",
            lot_size=100,
            last_price=Decimal("50"),
            meta={"avg_daily_turnover": 2_000_000},
        )
        self.db.add_all([self.sec1, self.sec2])
        self.db.flush()
        self.db.add(
            Position(
                portfolio_id=self.portfolio.id,
                security_id=self.sec1.id,
                quantity=Decimal("1000"),
                avg_cost=Decimal("100"),
                market_value=Decimal("100000"),
                weight_pct=Decimal("10"),
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_pretrade_checks_pass(self):
        out = run_pretrade_checks(
            self.db,
            self.portfolio.id,
            self.sec2.id,
            target_weight_pct=8,
            order_notional=50000,
            corr_value=0.5,
        )
        self.assertTrue(out["allowed"])
        self.assertEqual(len(out["checks"]), 5)

    def test_portfolio_construction_and_execution(self):
        plan = construct_target_weights(
            self.db,
            self.portfolio.id,
            [{"security_id": self.sec1.id, "score": 0.7}, {"security_id": self.sec2.id, "score": 0.3}],
            max_turnover_pct=30,
        )
        self.assertIn("targets", plan)
        self.assertGreater(len(plan["targets"]), 0)

        sim = simulate_execution(
            side="buy",
            quantity=1000,
            reference_price=100,
            adv_notional=1_000_000,
            fill_ratio=0.6,
        )
        self.assertGreater(sim["executed_price"], sim["reference_price"])
        self.assertEqual(sim["fill_ratio"], 0.6)

    def test_decision_ledger_transition(self):
        ledger = create_ledger(
            self.db,
            portfolio_id=self.portfolio.id,
            security_id=self.sec1.id,
            proposal_json={"action": "buy", "target_weight_pct": 8},
        )
        self.assertEqual(ledger.status, DecisionLedgerStatus.draft)
        ledger = transition_ledger(
            self.db,
            ledger_id=ledger.id,
            to_status=DecisionLedgerStatus.approved,
            risk_result_json={"allowed": True},
        )
        self.assertEqual(ledger.status, DecisionLedgerStatus.approved)
        ledger = transition_ledger(
            self.db,
            ledger_id=ledger.id,
            to_status=DecisionLedgerStatus.submitted,
        )
        self.assertEqual(ledger.status, DecisionLedgerStatus.submitted)

    def test_decision_auto_sync_to_ledger(self):
        decision = create_decision(
            self.db,
            self.portfolio.id,
            self.sec1.id,
            action=DecisionAction.buy,
            decision_reason="测试联动",
            current_weight_pct=10,
            target_weight_pct=8,
            main_risks=[],
            review_conditions=[],
            assumptions=[],
            references=[{"ref_type": "news", "ref_id": "n1", "excerpt": "盈利改善"}],
        )
        ledger = get_latest_ledger_by_decision(self.db, decision.id)
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.status, DecisionLedgerStatus.draft)

        update_decision_status(self.db, decision.id, status=DecisionStatus.approved)
        ledger = get_latest_ledger_by_decision(self.db, decision.id)
        self.assertEqual(ledger.status, DecisionLedgerStatus.approved)

        execute_decision(self.db, decision.id)
        ledger = get_latest_ledger_by_decision(self.db, decision.id)
        self.assertEqual(ledger.status, DecisionLedgerStatus.filled)

    def test_pipeline_runs_and_creates_decisions(self):
        out = run_decision_pipeline(
            self.db,
            portfolio_id=self.portfolio.id,
            candidates=[
                {"security_id": self.sec1.id, "score": 0.2},
                {"security_id": self.sec2.id, "score": 0.8},
            ],
            max_turnover_pct=30,
        )
        self.assertIn("results", out)
        self.assertGreaterEqual(len(out["results"]), 1)
        created = [r for r in out["results"] if r["decision_id"]]
        self.assertGreaterEqual(len(created), 1)
        self.assertIn("execution_plan", out["results"][0])
        self.assertIn("schedule", out["results"][0]["execution_plan"])

    def test_pipeline_auto_approve_and_simulated_execution(self):
        out = run_decision_pipeline(
            self.db,
            portfolio_id=self.portfolio.id,
            candidates=[{"security_id": self.sec2.id, "score": 1.0}],
            max_turnover_pct=30,
            auto_approve=True,
            auto_execute_simulated=True,
            simulated_fill_ratio=0.7,
        )
        created = [r for r in out["results"] if r["decision_id"]]
        self.assertGreaterEqual(len(created), 1)
        row = created[0]
        self.assertTrue(row["auto_approved"])
        self.assertIsNotNone(row["simulated_execution"])
        self.assertEqual(row["simulated_execution"]["fill_ratio"], 0.7)
        ledger = get_latest_ledger_by_decision(self.db, UUID(row["decision_id"]))
        self.assertEqual(ledger.status, DecisionLedgerStatus.filled)
        self.assertEqual(ledger.execution_result_json.get("mode"), "simulated")


if __name__ == "__main__":
    unittest.main()
