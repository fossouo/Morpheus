import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_literal_root_boundary_guard import (  # noqa: E402
    load_fixture,
    repaired_routing_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_literal_root_boundary_cases.json"


class ExpertLiteralRootBoundaryGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.source, _ = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture, self.source)
        self.summary = summarize(self.fixture, self.source, self.trial)

    def test_guard_improves_locked_grammar_cases(self):
        self.assertEqual(self.summary["baseline_grammar_correct"], 4)
        self.assertEqual(self.summary["baseline_grammar_false_accepts"], 2)
        self.assertEqual(self.summary["candidate_grammar_correct"], 6)
        self.assertEqual(self.summary["candidate_grammar_false_accepts"], 0)
        self.assertEqual(self.summary["grammar_accuracy_gain"], 0.333333)

    def test_unsafe_composition_is_rejected_transactionally(self):
        self.assertEqual(self.summary["unsafe_baseline_boundary"], "gamma-fern-59")
        self.assertEqual(self.summary["unsafe_guard_rejections"], 24)
        self.assertEqual(self.summary["unsafe_guard_clean_states"], 24)
        self.assertEqual(self.summary["unsafe_guard_boundary_rejections"], 24)

    def test_literal_repair_exposes_specificity_score_drift(self):
        self.assertFalse(self.summary["baseline_policy_outputs_correct"])
        self.assertEqual(self.summary["baseline_target_correct"], 5)
        self.assertEqual(self.summary["baseline_pre_exclusion_ambiguities"], 0)
        self.assertFalse(self.summary["cardinality_expectations_correct"])
        self.assertEqual(self.summary["candidate_target_correct"], 5)
        self.assertEqual(self.summary["target_accuracy_gain"], 0.0)
        self.assertEqual(self.summary["candidate_three_to_one_selections"], 1)
        self.assertEqual(self.summary["candidate_three_to_two_ambiguities"], 0)
        self.assertEqual(self.summary["candidate_three_to_zero_denials"], 2)
        self.assertEqual(self.summary["candidate_floor_denials"], 2)

    def test_orders_regressions_boundaries_and_rollback_are_preserved(self):
        self.assertEqual(self.summary["candidate_regression_correct"], 3)
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["boundary_rejections"], 24)
        self.assertEqual(self.summary["absent_scope_rejections"], 24)
        self.assertEqual(self.summary["rollback_matches_baseline"], 192)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture, self.source)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_replacements_change_only_the_leading_segment(self):
        repaired = repaired_routing_fixture(self.fixture, self.source)
        for package in repaired["packages"]:
            for name in ("include", "exclude"):
                for pattern in package["manifest"]["scope"][name]:
                    self.assertNotEqual(pattern.split("/")[0], "*")

    def test_fixture_rejects_a_changed_source_hash(self):
        changed = copy.deepcopy(self.fixture)
        changed["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_fixture(changed, self.source)


if __name__ == "__main__":
    unittest.main()
