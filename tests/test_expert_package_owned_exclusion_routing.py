import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_package_owned_exclusion_routing import (  # noqa: E402
    PackageOwnedExclusionRoutingKernel,
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_package_owned_exclusion_cases.json"


class ExpertPackageOwnedExclusionRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_package_ownership_recovers_held_out_routes(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 4)
        self.assertEqual(self.summary["baseline_cross_package_over_denials"], 2)
        self.assertEqual(self.summary["candidate_target_correct"], 6)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.333333)
        self.assertEqual(self.summary["candidate_cross_package_recoveries"], 2)

    def test_all_applicable_packages_excluded_stays_fail_closed(self):
        self.assertEqual(self.summary["candidate_all_excluded_denials"], 2)

    def test_package_owned_router_preserves_regressions(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)

    def test_specificity_and_ties_remain_deterministic(self):
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

    def test_invalid_owned_exclusion_is_rejected_atomically(self):
        packages = copy.deepcopy(self.fixture["packages"][:2])
        packages[0]["manifest"]["scope"]["exclude"] = ["synthetic/library/*/*"]
        kernel = PackageOwnedExclusionRoutingKernel()
        with self.assertRaisesRegex(ValueError, "wildcard"):
            kernel.compose_quarantined_experts(
                packages, reference_date=date(2026, 8, 17)
            )
        self.assertEqual(
            kernel.answer(self.fixture["held_out_target"][0]["request"]),
            "route-error:scope-not-found",
        )


if __name__ == "__main__":
    unittest.main()
