import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_hierarchical_scope_routing import (  # noqa: E402
    HierarchicalScopeRoutingKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_hierarchical_scope_routing_cases.json"


class ExpertHierarchicalScopeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_longest_prefix_adds_held_out_target_behavior(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 2)
        self.assertEqual(self.summary["candidate_target_correct"], 5)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.6)

    def test_hierarchical_router_preserves_regressions(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)

    def test_router_is_order_invariant_and_unloadable(self):
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["rollback_matches_baseline"], 5)

    def test_equal_specificity_is_rejected_atomically_in_both_orders(self):
        self.assertEqual(self.summary["equal_specificity_rejections"], 2)
        self.assertEqual(self.summary["equal_specificity_clean_states"], 2)

    def test_near_prefix_and_absent_scope_are_rejected(self):
        self.assertEqual(self.summary["near_prefix_rejections"], 2)
        self.assertEqual(self.summary["absent_scope_rejections"], 2)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_duplicate_package_id_is_rejected_without_state_change(self):
        package = copy.deepcopy(self.fixture["packages"][0])
        kernel = HierarchicalScopeRoutingKernel()
        with self.assertRaisesRegex(ValueError, "duplicate-package-id"):
            kernel.compose_quarantined_experts(
                [package, copy.deepcopy(package)], reference_date=date(2026, 8, 14)
            )
        self.assertEqual(
            kernel.answer(
                {
                    "operation": "scope_recall",
                    "scope": "synthetic/library/history",
                    "local_id": "shared-entry-v1",
                }
            ),
            "route-error:scope-not-found",
        )


if __name__ == "__main__":
    unittest.main()
