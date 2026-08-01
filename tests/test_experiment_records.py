import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_experiment_records import (  # noqa: E402
    apply_mutation,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_experiment_records import validate_record, validate_tree  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "experiment_record_cases.json"
FILENAME = "EXP-900-synthetic-strict-record.md"


class ExperimentRecordTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_strict_validator_matches_all_predeclared_labels(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 7)
        self.assertEqual(summary["strict_correct"], 7)
        self.assertEqual(summary["strict_false_accepts"], 0)

    def test_title_only_baseline_false_accepts_structural_faults(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertGreaterEqual(summary["baseline_false_accepts"], 4)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_missing_hypothesis_has_specific_error(self):
        errors = validate_record(apply_mutation("missing_hypothesis"), FILENAME)
        self.assertIn("missing-section:Hypothesis", errors)

    def test_duplicate_metrics_has_specific_error(self):
        errors = validate_record(apply_mutation("duplicate_metrics"), FILENAME)
        self.assertIn("duplicate-section:Metrics", errors)

    def test_invalid_status_has_specific_error(self):
        errors = validate_record(apply_mutation("invalid_status"), FILENAME)
        self.assertIn("invalid-status", errors)

    def test_mismatched_id_has_specific_error(self):
        errors = validate_record(apply_mutation("mismatched_id"), FILENAME)
        self.assertIn("id-mismatch", errors)

    def test_current_repository_records_validate(self):
        self.assertEqual(validate_tree(ROOT), [])


if __name__ == "__main__":
    unittest.main()
