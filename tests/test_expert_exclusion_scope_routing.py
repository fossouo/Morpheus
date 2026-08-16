import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_exclusion_scope_routing import (  # noqa: E402
    ExclusionScopeRoutingKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_exclusion_scope_routing_cases.json"


class ExpertExclusionScopeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_exclusion_router_adds_held_out_denial_behavior(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 3)
        self.assertEqual(self.summary["baseline_excluded_values_returned"], 5)
        self.assertEqual(self.summary["candidate_target_correct"], 8)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.625)

    def test_exact_and_wildcard_exclusions_precede_lookup(self):
        self.assertEqual(self.summary["candidate_exact_exclusion_denials"], 3)
        self.assertEqual(self.summary["candidate_wildcard_exclusion_denials"], 2)

    def test_exclusion_router_preserves_regressions(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)

    def test_specificity_ties_and_exclusion_precedence_are_deterministic(self):
        self.assertEqual(self.summary["literal_specificity_selections"], 2)
        self.assertEqual(self.summary["equal_specificity_rejections"], 2)
        self.assertEqual(self.summary["post_ambiguity_controls"], 2)
        self.assertEqual(self.summary["exclusion_over_tie_denials"], 2)

    def test_boundaries_order_and_rollback_are_preserved(self):
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["boundary_rejections"], 2)
        self.assertEqual(self.summary["absent_scope_rejections"], 2)
        self.assertEqual(self.summary["rollback_matches_baseline"], 8)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_invalid_exclusion_patterns_are_rejected_atomically(self):
        packages = copy.deepcopy(self.fixture["packages"][:2])
        for invalid_scope in ("synthetic/lib*/private", "synthetic/*/*"):
            packages[0]["manifest"]["scope"]["exclude"] = [invalid_scope]
            kernel = ExclusionScopeRoutingKernel()
            with self.assertRaisesRegex(ValueError, "wildcard|canonical"):
                kernel.compose_quarantined_experts(
                    packages, reference_date=date(2026, 8, 16)
                )
            self.assertEqual(
                kernel.answer(self.fixture["held_out_target"][0]["request"]),
                "route-error:scope-not-found",
            )


if __name__ == "__main__":
    unittest.main()
