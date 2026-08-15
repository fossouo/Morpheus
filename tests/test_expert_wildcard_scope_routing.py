import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_wildcard_scope_routing import (  # noqa: E402
    WildcardScopeRoutingKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_wildcard_scope_routing_cases.json"


class ExpertWildcardScopeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_wildcard_router_adds_held_out_target_behavior(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 2)
        self.assertEqual(self.summary["candidate_target_correct"], 6)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.666667)

    def test_wildcard_router_preserves_regressions(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)

    def test_specificity_and_request_time_ties_are_deterministic(self):
        self.assertEqual(self.summary["literal_specificity_selections"], 2)
        self.assertEqual(self.summary["equal_specificity_rejections"], 2)
        self.assertEqual(self.summary["post_ambiguity_controls"], 2)

    def test_boundaries_order_and_rollback_are_preserved(self):
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["boundary_rejections"], 2)
        self.assertEqual(self.summary["absent_scope_rejections"], 2)
        self.assertEqual(self.summary["rollback_matches_baseline"], 6)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_partial_and_multiple_wildcards_are_rejected_atomically(self):
        packages = copy.deepcopy(self.fixture["packages"][:2])
        for invalid_scope in ("synthetic/lib*/science", "synthetic/*/*"):
            packages[1]["manifest"]["scope"]["include"] = [invalid_scope]
            kernel = WildcardScopeRoutingKernel()
            with self.assertRaisesRegex(ValueError, "wildcard|canonical"):
                kernel.compose_quarantined_experts(
                    packages, reference_date=date(2026, 8, 15)
                )
            self.assertEqual(
                kernel.answer(self.fixture["held_out_target"][0]["request"]),
                "route-error:scope-not-found",
            )

    def test_duplicate_pattern_is_rejected_without_state_change(self):
        packages = copy.deepcopy(self.fixture["packages"][:2])
        packages[1]["manifest"]["scope"]["include"] = ["synthetic/library"]
        kernel = WildcardScopeRoutingKernel()
        with self.assertRaisesRegex(ValueError, "duplicate-scope-pattern"):
            kernel.compose_quarantined_experts(
                packages, reference_date=date(2026, 8, 15)
            )
        self.assertEqual(
            kernel.answer(self.fixture["held_out_target"][0]["request"]),
            "route-error:scope-not-found",
        )


if __name__ == "__main__":
    unittest.main()
