import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_package_root_ownership import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_package_root_ownership_cases.json"


class ExpertPackageRootOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_owned_roots_improve_held_out_targets(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 4)
        self.assertEqual(self.summary["baseline_cross_root_false_accepts"], 4)
        self.assertEqual(self.summary["candidate_target_correct"], 8)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.5)

    def test_both_roots_route_and_cross_root_matches_fail_closed(self):
        self.assertEqual(self.summary["candidate_own_root_routes"], 4)
        self.assertEqual(self.summary["candidate_cross_root_rejections"], 4)
        self.assertEqual(self.summary["baseline_probe_false_accepts"], 2)
        self.assertEqual(self.summary["candidate_probe_rejections"], 2)

    def test_regressions_orders_absence_and_rollback_are_preserved(self):
        self.assertEqual(self.summary["candidate_regression_correct"], 3)
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["absent_scope_rejections"], 2)
        self.assertEqual(self.summary["rollback_matches_baseline"], 16)

    def test_invalid_declarations_are_transactional(self):
        self.assertEqual(self.summary["invalid_order_count"], 8)
        self.assertEqual(self.summary["baseline_invalid_declarations_accepted"], 8)
        self.assertEqual(self.summary["candidate_invalid_declarations_rejected"], 8)
        self.assertEqual(self.summary["candidate_invalid_states_clean"], 8)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_duplicate_roots(self):
        changed = copy.deepcopy(self.fixture)
        changed["packages"][1]["root"] = changed["packages"][0]["root"]
        with self.assertRaisesRegex(ValueError, "two distinct roots"):
            validate_fixture(changed)

    def test_fixture_rejects_missing_cross_root_case(self):
        changed = copy.deepcopy(self.fixture)
        changed["held_out_target"][2]["policy"] = "own-root-alpha-extra"
        with self.assertRaisesRegex(ValueError, "four own-root targets"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
