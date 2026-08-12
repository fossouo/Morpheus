import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_qualified_expert_routing import (  # noqa: E402
    PackageQualifiedExpertKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_qualified_routing_cases.json"


class ExpertQualifiedRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_candidate_adds_qualified_target_behavior_over_rejecting_baseline(self):
        self.assertEqual(self.summary["baseline_target_correct"], 0)
        self.assertEqual(self.summary["candidate_target_correct"], 4)
        self.assertEqual(self.summary["target_accuracy_gain"], 1.0)

    def test_candidate_preserves_regression_behavior(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)
        self.assertEqual(self.summary["regression_accuracy_drop"], 0.0)

    def test_baseline_rejects_both_orders_without_state_change(self):
        self.assertEqual(self.summary["baseline_collision_rejections"], 2)
        self.assertEqual(self.summary["baseline_clean_states"], 2)

    def test_shared_local_id_routes_to_two_distinct_package_values(self):
        self.assertEqual(self.summary["shared_local_id_distinct_routes"], 2)

    def test_candidate_is_order_invariant_and_unloadable(self):
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["rollback_matches_baseline"], 4)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_duplicate_package_id_is_rejected_without_state_change(self):
        package = copy.deepcopy(self.fixture["packages"][0])
        kernel = PackageQualifiedExpertKernel()
        with self.assertRaisesRegex(ValueError, "duplicate-package-id"):
            kernel.compose_quarantined_experts(
                [package, copy.deepcopy(package)], reference_date=date(2026, 8, 12)
            )
        self.assertEqual(
            kernel.answer(
                {
                    "operation": "qualified_recall",
                    "package_id": "synthetic-north",
                    "local_id": "shared-entry-v1",
                }
            ),
            "unknown",
        )


if __name__ == "__main__":
    unittest.main()
