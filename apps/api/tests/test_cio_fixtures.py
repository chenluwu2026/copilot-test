"""CIO 评测 fixture 加载与质量阈值。"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "examples" / "golden_path_fixtures.json"


class CioFixtureTests(unittest.TestCase):
    def test_fixture_loads(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertIn("symbols", data)
        self.assertGreaterEqual(len(data["symbols"]), 3)
        self.assertIn("min_evidence_score", data)

    def test_golden_decision_keys(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        gd = data.get("golden_decision") or {}
        self.assertEqual(gd.get("symbol"), "00700.HK")


if __name__ == "__main__":
    unittest.main()
