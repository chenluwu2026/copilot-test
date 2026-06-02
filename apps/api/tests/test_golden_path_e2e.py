"""黄金链 E2E：seed + Phase 1 DoD（通过 onboarding_check 脚本）。"""
import subprocess
import sys
import unittest
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]


class GoldenPathE2ETests(unittest.TestCase):
    def test_onboarding_check_script(self):
        proc = subprocess.run(
            [sys.executable, "scripts/onboarding_check.py"],
            cwd=str(API_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=proc.stderr or proc.stdout,
        )
        self.assertIn("all_complete", proc.stdout)
        self.assertIn("True", proc.stdout)


if __name__ == "__main__":
    unittest.main()
