"""能力路线图：质量指标与记忆打分（无需数据库）。"""
import unittest

from app.models import MemoryEntry, MemoryType
from app.services.memory_service import _memory_match_score, _tokenize_context
from app.services.quality_metrics_service import get_quality_metrics


class CapabilityRoadmapTests(unittest.TestCase):
    def test_tokenize_symbol_base(self):
        tokens = _tokenize_context(symbols=["600519.SH"])
        self.assertIn("600519.SH", tokens)
        self.assertIn("600519", tokens)

    def test_memory_title_boost(self):
        entry = MemoryEntry(
            memory_type=MemoryType.lesson,
            title="茅台估值纪律",
            content="单票上限 8%",
            tags=["消费"],
            confidence=80,
            active=True,
            pending=False,
        )
        score = _memory_match_score(entry, ["600519", "茅台"])
        self.assertGreater(score, 2)

    def test_quality_metrics_module_exports(self):
        self.assertTrue(callable(get_quality_metrics))


if __name__ == "__main__":
    unittest.main()
