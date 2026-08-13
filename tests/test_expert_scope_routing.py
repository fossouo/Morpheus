import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_scope_expert_routing import (  # noqa: E402
    ScopeRoutingKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_scope_routing_cases.json"


class ExpertScopeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_scope_router_adds_target_behavior_without_package_id(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 0)
        self.assertEqual(self.summary["candidate_target_correct"], 4)
        self.assertEqual(self.summary["target_accuracy_gain"], 1.0)

    def test_scope_router_preserves_regressions(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)

    def test_scope_router_is_order_invariant_and_unloadable(self):
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["rollback_matches_baseline"], 4)

    def test_overlapping_scope_is_rejected_atomically_in_both_orders(self):
        self.assertEqual(self.summary["ambiguous_scope_rejections"], 2)
        self.assertEqual(self.summary["ambiguous_scope_clean_states"], 2)

    def test_absent_scope_is_rejected_in_both_compatible_orders(self):
        self.assertEqual(self.summary["absent_scope_rejections"], 2)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_duplicate_package_id_is_rejected_without_state_change(self):
        package = copy.deepcopy(self.fixture["packages"][0])
        kernel = ScopeRoutingKernel()
        with self.assertRaisesRegex(ValueError, "duplicate-package-id"):
            kernel.compose_quarantined_experts(
                [package, copy.deepcopy(package)], reference_date=date(2026, 8, 13)
            )
        self.assertEqual(
            kernel.answer(
                {
                    "operation": "scope_recall",
                    "scope": "synthetic-scope-north",
                    "local_id": "shared-entry-v1",
                }
            ),
            "route-error:scope-not-found",
        )


if __name__ == "__main__":
    unittest.main()
