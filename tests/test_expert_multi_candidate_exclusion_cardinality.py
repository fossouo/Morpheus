import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_multi_candidate_exclusion_cardinality import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_multi_candidate_exclusion_cases.json"


class ExpertMultiCandidateExclusionCardinalityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_cardinality_transitions_improve_locked_targets(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 4)
        self.assertEqual(self.summary["baseline_pre_exclusion_ambiguities"], 6)
        self.assertTrue(self.summary["cardinality_expectations_correct"])
        self.assertEqual(self.summary["candidate_target_correct"], 8)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.5)

    def test_candidate_handles_all_three_candidate_outcomes(self):
        self.assertEqual(self.summary["candidate_three_to_one_selections"], 2)
        self.assertEqual(self.summary["candidate_three_to_two_ambiguities"], 2)
        self.assertEqual(self.summary["candidate_three_to_zero_denials"], 2)

    def test_specificity_floor_still_blocks_broader_fallback(self):
        self.assertEqual(self.summary["candidate_floor_denials"], 2)

    def test_regressions_are_preserved(self):
        self.assertEqual(self.summary["unloaded_regression_correct"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)

    def test_all_orders_and_rollback_are_preserved_but_boundary_fails(self):
        self.assertEqual(self.summary["order_count"], 24)
        self.assertTrue(self.summary["baseline_order_invariant"])
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["boundary_rejections"], 0)
        self.assertEqual(self.summary["absent_scope_rejections"], 24)
        self.assertEqual(self.summary["rollback_matches_baseline"], 8 * 24)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_an_unlocked_cardinality(self):
        self.fixture["held_out_target"][0]["expected_top_candidates"] = 2
        with self.assertRaisesRegex(ValueError, "cardinalities"):
            validate_fixture(self.fixture)


if __name__ == "__main__":
    unittest.main()
