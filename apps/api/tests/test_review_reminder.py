"""复盘到期逻辑单元测试。"""
import unittest
from datetime import datetime, timedelta, timezone

from app.services.review_reminder_service import review_due_meta


class ReviewReminderTests(unittest.TestCase):
    def test_not_due_within_window(self):
        executed = datetime.now(timezone.utc) - timedelta(days=5)
        meta = review_due_meta(
            executed_at=executed,
            return_pct=2.0,
            profile={"review_due_days": 30, "review_material_move_pct": 8},
        )
        self.assertFalse(meta["review_due"])
        self.assertEqual(meta["urgency"], "ok")

    def test_due_by_time(self):
        executed = datetime.now(timezone.utc) - timedelta(days=50)
        meta = review_due_meta(
            executed_at=executed,
            return_pct=1.0,
            profile={"review_due_days": 30, "review_material_move_pct": 8},
        )
        self.assertTrue(meta["review_due"])
        self.assertEqual(meta["urgency"], "overdue")

    def test_due_by_material_move(self):
        executed = datetime.now(timezone.utc) - timedelta(days=3)
        meta = review_due_meta(
            executed_at=executed,
            return_pct=-10.0,
            profile={"review_due_days": 30, "review_material_move_pct": 8},
        )
        self.assertTrue(meta["review_due"])
        self.assertTrue(meta["material_move"])
        self.assertEqual(meta["urgency"], "due")


if __name__ == "__main__":
    unittest.main()
