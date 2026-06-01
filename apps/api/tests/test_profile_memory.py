"""投资画像与记忆检索单元测试（无需数据库）。"""
import unittest

from app.services.memory_service import _memory_match_score, _tokenize_context
from app.services.profile_service import DEFAULT_INVESTMENT_PROFILE, normalize_profile, user_is_forbidden


class ProfileMemoryTests(unittest.TestCase):
    def test_normalize_profile_merges_risk_budget(self):
        raw = {"risk_budget": {"max_single_name_pct": 8}, "notes": "测试"}
        profile = normalize_profile(raw)
        self.assertEqual(profile["risk_budget"]["max_single_name_pct"], 8)
        self.assertEqual(profile["risk_budget"]["max_sector_pct"], 25)
        self.assertEqual(profile["notes"], "测试")

    def test_default_profile_has_research_max_age(self):
        self.assertIn("research_max_age_days", DEFAULT_INVESTMENT_PROFILE)

    def test_user_is_forbidden(self):
        profile = normalize_profile(
            {"forbidden_symbols": ["600519.SH"], "forbidden_sectors": ["传媒"]}
        )
        self.assertTrue(user_is_forbidden(profile, symbol="600519.SH"))
        self.assertTrue(user_is_forbidden(profile, sector="传媒"))
        self.assertFalse(user_is_forbidden(profile, symbol="00700.HK", sector="科技"))

    def test_tokenize_context(self):
        tokens = _tokenize_context(
            symbols=["600519.SH", "00700.HK"],
            sectors=["消费"],
            keywords=["复盘"],
        )
        self.assertIn("600519.SH", tokens)
        self.assertIn("600519", tokens)
        self.assertIn("消费", tokens)

    def test_memory_match_score(self):
        from types import SimpleNamespace

        entry = SimpleNamespace(
            title="复盘 600519",
            content="白酒行业教训",
            tags=["消费"],
        )
        score = _memory_match_score(entry, ["600519", "消费"])
        self.assertGreaterEqual(score, 2)


if __name__ == "__main__":
    unittest.main()
