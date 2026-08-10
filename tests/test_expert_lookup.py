import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_lookup import (  # noqa: E402
    StableKernel,
    load_fixture,
    run_transition,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_lookup_cases.json"


class ExpertLookupTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.transition = run_transition(self.fixture)
        self.summary = summarize(self.fixture, self.transition)

    def test_locked_case_counts(self):
        self.assertEqual(self.summary["target_count"], 6)
        self.assertEqual(self.summary["regression_count"], 4)

    def test_loaded_expert_adds_target_behavior(self):
        self.assertEqual(self.summary["baseline_target_correct"], 0)
        self.assertEqual(self.summary["loaded_target_correct"], 6)
        self.assertEqual(self.summary["target_accuracy_gain"], 1.0)

    def test_loaded_expert_preserves_regression_behavior(self):
        self.assertEqual(self.summary["baseline_regression_correct"], 4)
        self.assertEqual(self.summary["loaded_regression_correct"], 4)
        self.assertEqual(self.summary["regression_accuracy_drop"], 0.0)

    def test_unload_restores_baseline_target_responses(self):
        self.assertEqual(self.summary["rollback_matches_baseline"], 6)
        self.assertEqual(
            self.transition["post_unload_target"], self.transition["baseline_target"]
        )

    def test_complete_transition_is_repeatable(self):
        repeated = run_transition(self.fixture)
        self.assertEqual(
            json.dumps(self.transition, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_manifest_and_records_must_have_identical_knowledge_ids(self):
        package = copy.deepcopy(self.fixture["package"])
        package["knowledge_records"].pop()
        kernel = StableKernel()
        with self.assertRaisesRegex(ValueError, "exactly match declared knowledge ids"):
            kernel.load_quarantined_expert(
                package["manifest"],
                package["knowledge_records"],
                reference_date=date(2026, 8, 10),
            )

    def test_unknown_recall_remains_unknown_while_loaded(self):
        self.assertEqual(self.transition["baseline_regression"][2], "unknown")
        self.assertEqual(self.transition["loaded_regression"][2], "unknown")


if __name__ == "__main__":
    unittest.main()
