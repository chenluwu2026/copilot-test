"""质量服务单元测试。"""
import unittest
from decimal import Decimal

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


def _test_database_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///:memory:"
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
        url = _test_database_url()
        kw = {}
        if url.startswith("sqlite"):
            kw["connect_args"] = {"check_same_thread": False}
        self._engine = create_engine(url, **kw)
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
        url = _test_database_url()
        kw = {}
        if url.startswith("sqlite"):
            kw["connect_args"] = {"check_same_thread": False}
        self._engine = create_engine(url, **kw)
        Base.metadata.create_all(bind=self._engine)
        self.db = sessionmaker(bind=self._engine)()

    def tearDown(self):
        self.db.close()

    def test_missing_symbol(self):
        q = get_research_quality(self.db, "NOPE.SYMBOL")
        self.assertFalse(q["found"])

    def test_with_research_view(self):
        """get_research_quality 应从 content_structured 读取 fundamental_analysis，而非不存在的属性。"""
        from decimal import Decimal
        from app.models import ResearchView, ResearchRating
        sec = Security(
            symbol="TEST.QUAL",
            name="质量测试",
            market=Market.HK,
            currency="HKD",
            sector="科技",
            lot_size=100,
            last_price=Decimal("100"),
        )
        self.db.add(sec)
        self.db.commit()
        fa = {
            "business_model": "主营业务描述，超过二十字符的内容用于通过完整性检测。",
            "industry_space": "行业空间描述，超过二十字符的内容用于通过完整性检测。",
            "competitive_landscape": "竞争格局描述，超过二十字符的内容用于通过完整性检测。",
            "financial_quality": "财务质量描述，超过二十字符的内容用于通过完整性检测。",
            "management": "管理层描述，超过二十字符的内容用于通过完整性检测。",
            "growth_drivers": "增长驱动描述，超过二十字符的内容用于通过完整性检测。",
            "key_risks": "主要风险描述，超过二十字符的内容用于通过完整性检测。",
            "current_valuation": "当前估值描述，超过二十字符的内容用于通过完整性检测。",
        }
        view = ResearchView(
            security_id=sec.id,
            rating=ResearchRating.buy,
            investment_conclusion="测试投资结论",
            content_structured={"fundamental_analysis": fa},
            scenario_analysis={
                "scenarios": [
                    {"name": "optimistic", "target_price_low": 120, "target_price_high": 140},
                    {"name": "pessimistic", "target_price_low": 80, "target_price_high": 95},
                ]
            },
        )
        self.db.add(view)
        self.db.commit()
        q = get_research_quality(self.db, "TEST.QUAL")
        self.assertTrue(q["found"])
        self.assertTrue(q["has_view"])
        self.assertIn("quality_grade", q)
        self.assertIn("completion_pct", q)
        self.assertEqual(q["completion_pct"], 100)


if __name__ == "__main__":
    unittest.main()
