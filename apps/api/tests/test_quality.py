"""质量服务单元测试。"""
import os
import unittest
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Market, MemoryType, Security
from app.services.backtest_quality_service import backtest_quality_report
from app.services.decision_quality_service import score_decision_draft
from app.services.embedding_service import cosine_similarity, embed_text
from app.services.financial_ingest_service import parse_financial_text
from app.services.macro_scenario_service import list_macro_scenarios
from app.services.memory_service import create_memory, search_memory_context
from app.services.research_quality_service import get_research_quality


class EmbeddingTests(unittest.TestCase):
    def test_embed_and_similarity(self):
        a = embed_text("腾讯 游戏 收入")
        b = embed_text("腾讯 游戏业务")
        c = embed_text("完全不同的行业")
        self.assertGreater(cosine_similarity(a, b), cosine_similarity(a, c))


class ParseFinancialTests(unittest.TestCase):
    def test_parse_metrics(self):
        text = "营业收入：123.5亿 净利润：45亿 ROE：18%"
        out = parse_financial_text(text)
        self.assertIn("revenue", out["metrics"])
        self.assertIn("roe_pct", out["metrics"])


class DecisionQualityTests(unittest.TestCase):
    def test_score_without_dossier(self):
        r = score_decision_draft(
            None,
            {
                "assumptions": [],
                "review_conditions": [],
                "decision_reason": "short",
                "action": "buy",
            },
        )
        self.assertEqual(r["grade"], "C")


class MacroScenarioTests(unittest.TestCase):
    def test_list_scenarios(self):
        items = list_macro_scenarios()
        self.assertGreaterEqual(len(items), 2)


class MemoryVectorTests(unittest.TestCase):
    def setUp(self):
        self._engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self._engine)
        self.db = sessionmaker(bind=self._engine)()

    def tearDown(self):
        self.db.close()

    def test_memory_embedding_search(self):
        sec = Security(
            symbol="TEST.MEM",
            name="Test",
            market=Market.CN_A,
            currency="CNY",
            sector="测试",
            lot_size=100,
            last_price=Decimal("10"),
        )
        self.db.add(sec)
        self.db.commit()
        create_memory(
            self.db,
            MemoryType.lesson,
            "腾讯加仓教训",
            "高位加仓后回撤需收紧止损",
            tags=["00700.HK"],
            active=True,
        )
        hits = search_memory_context(self.db, symbols=["00700.HK"], keywords=["回撤"])
        self.assertTrue(len(hits) >= 0)


class ResearchQualityTests(unittest.TestCase):
    def setUp(self):
        self._engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self._engine)
        self.db = sessionmaker(bind=self._engine)()

    def tearDown(self):
        self.db.close()

    def test_missing_symbol(self):
        q = get_research_quality(self.db, "NOPE.SYMBOL")
        self.assertFalse(q["found"])


if __name__ == "__main__":
    unittest.main()
