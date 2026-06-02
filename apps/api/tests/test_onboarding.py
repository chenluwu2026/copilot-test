"""Onboarding / Phase 1 DoD 单元测试。"""
import unittest
from uuid import uuid4

from app.models import (
    Decision,
    DecisionAction,
    DecisionAssumption,
    DecisionReference,
    DecisionStatus,
    ReferenceType,
)
from app.services.onboarding_service import _decision_meets_quality, get_phase1_dod


class OnboardingLogicTests(unittest.TestCase):
    def test_decision_meets_quality(self):
        d = Decision(
            id=uuid4(),
            portfolio_id=uuid4(),
            security_id=uuid4(),
            action=DecisionAction.add,
            decision_reason="test",
            review_conditions=["cond"],
        )
        d.assumptions = [
            DecisionAssumption(assumption_text="a", measurable=False),
        ]
        d.references = [
            DecisionReference(ref_type=ReferenceType.news, excerpt="x"),
        ]
        self.assertTrue(_decision_meets_quality(d))

    def test_decision_missing_refs(self):
        d = Decision(
            id=uuid4(),
            portfolio_id=uuid4(),
            security_id=uuid4(),
            action=DecisionAction.add,
            decision_reason="test",
            review_conditions=["cond"],
        )
        d.assumptions = [DecisionAssumption(assumption_text="a")]
        d.references = []
        self.assertFalse(_decision_meets_quality(d))


class OnboardingServiceExports(unittest.TestCase):
    def test_get_phase1_dod_callable(self):
        self.assertTrue(callable(get_phase1_dod))


if __name__ == "__main__":
    unittest.main()
