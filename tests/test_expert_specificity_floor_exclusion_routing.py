import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_specificity_floor_exclusion_routing import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_specificity_floor_exclusion_cases.json"


class ExpertSpecificityFloorExclusionRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_specificity_floor_blocks_broader_fallbacks(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 6)
        self.assertEqual(self.summary["baseline_broader_fallbacks"], 2)
        self.assertEqual(self.summary["candidate_target_correct"], 8)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.25)
        self.assertEqual(self.summary["candidate_specificity_floor_denials"], 2)

    def test_delegation_and_all_excluded_cases_are_preserved(self):
        self.assertEqual(self.summary["candidate_delegations_preserved"], 2)
        self.assertEqual(self.summary["candidate_all_excluded_denials"], 2)

    def test_specificity_floor_router_preserves_regressions(self):
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
        self.assertEqual(self.summary["rollback_matches_baseline"], 8)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_an_unlocked_policy(self):
        self.fixture["held_out_target"][0]["policy"] = "unlocked"
        from scripts.evaluate_specificity_floor_exclusion_routing import validate_fixture

        with self.assertRaisesRegex(ValueError, "locked protocol"):
            validate_fixture(self.fixture)


if __name__ == "__main__":
    unittest.main()
