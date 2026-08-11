import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_composition import (  # noqa: E402
    TransactionalExpertKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_composition_cases.json"


class ExpertCompositionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_compatible_composition_adds_target_behavior(self):
        self.assertEqual(self.summary["baseline_target_correct"], 0)
        self.assertEqual(self.summary["composed_target_correct"], 4)
        self.assertEqual(self.summary["target_accuracy_gain"], 1.0)

    def test_compatible_composition_preserves_regressions(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["composed_regression_correct"], 3)
        self.assertEqual(self.summary["regression_accuracy_drop"], 0.0)

    def test_compatible_composition_is_order_invariant_and_unloadable(self):
        self.assertTrue(self.summary["compatible_order_invariant"])
        self.assertEqual(self.summary["rollback_matches_baseline"], 4)

    def test_conflicting_composition_is_rejected_atomically_in_both_orders(self):
        self.assertEqual(self.summary["candidate_conflict_rejections"], 2)
        self.assertEqual(self.summary["candidate_conflict_state_clean"], 2)

    def test_last_write_wins_baseline_depends_on_conflict_order(self):
        self.assertTrue(self.summary["baseline_conflict_outputs_correct"])
        self.assertEqual(self.summary["baseline_distinct_conflict_outputs"], 2)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_duplicate_package_id_is_rejected_without_state_change(self):
        package = copy.deepcopy(self.fixture["packages"][0])
        kernel = TransactionalExpertKernel()
        with self.assertRaisesRegex(ValueError, "duplicate-package-id"):
            kernel.compose_quarantined_experts(
                [package, copy.deepcopy(package)], reference_date=date(2026, 8, 11)
            )
        self.assertEqual(
            kernel.answer({"operation": "recall", "key": "alpha-entry-v1"}), "unknown"
        )


if __name__ == "__main__":
    unittest.main()
