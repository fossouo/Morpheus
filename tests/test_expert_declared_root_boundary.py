import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_declared_root_boundary import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_declared_root_boundary_cases.json"


class ExpertDeclaredRootBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.source, self.source_path = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture, self.source)
        self.summary = summarize(self.fixture, self.source, self.trial)

    def test_fence_rejects_locked_cross_root_cases(self):
        self.assertEqual(self.summary["unrestricted_cross_root_correct"], 4)
        self.assertEqual(self.summary["unrestricted_cross_root_false_accepts"], 4)
        self.assertEqual(self.summary["candidate_cross_root_correct"], 4)
        self.assertEqual(self.summary["candidate_cross_root_rejections"], 24)
        self.assertEqual(self.summary["cross_root_accuracy_gain"], 1.0)

    def test_original_held_out_behavior_is_restored(self):
        self.assertTrue(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 4)
        self.assertEqual(self.summary["baseline_pre_exclusion_ambiguities"], 6)
        self.assertEqual(self.summary["candidate_target_correct"], 8)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.5)

    def test_cardinality_and_floor_expectations_are_preserved(self):
        self.assertTrue(self.summary["cardinality_expectations_correct"])
        self.assertEqual(self.summary["candidate_three_to_one_selections"], 2)
        self.assertEqual(self.summary["candidate_three_to_two_ambiguities"], 2)
        self.assertEqual(self.summary["candidate_three_to_zero_denials"], 2)
        self.assertEqual(self.summary["candidate_floor_denials"], 2)

    def test_orders_regressions_boundaries_and_rollback_are_preserved(self):
        self.assertEqual(self.summary["candidate_regression_correct"], 3)
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertTrue(self.summary["unrestricted_cross_root_order_invariant"])
        self.assertEqual(self.summary["boundary_rejections"], 24)
        self.assertEqual(self.summary["absent_scope_rejections"], 24)
        self.assertEqual(self.summary["rollback_matches_baseline"], 192)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture, self.source)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_a_changed_source_hash(self):
        changed = copy.deepcopy(self.fixture)
        changed["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_fixture(changed, self.source)

    def test_fixture_rejects_wildcard_or_duplicate_roots(self):
        wildcard = copy.deepcopy(self.fixture)
        wildcard["allowed_roots"] = ["*"]
        with self.assertRaisesRegex(ValueError, "literal single segments"):
            validate_fixture(wildcard, self.source, self.source_path.read_bytes())
        duplicate = copy.deepcopy(self.fixture)
        duplicate["allowed_roots"] = ["synthetic", "synthetic"]
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_fixture(duplicate, self.source, self.source_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
