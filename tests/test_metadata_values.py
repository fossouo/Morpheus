import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_metadata_values import (  # noqa: E402
    apply_mutation,
    candidate_errors,
    evaluate_fixture,
    load_fixture,
    summarize,
)


FIXTURE_PATH = ROOT / "fixtures" / "metadata_value_cases.json"


class MetadataValueTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_candidate_reproduces_observed_failed_threshold(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 8)
        self.assertEqual(summary["candidate_correct"], 6)
        self.assertEqual(summary["candidate_false_accepts"], 2)

    def test_prior_contract_false_accepts_placeholders(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertGreaterEqual(summary["baseline_false_accepts"], 5)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_template_data_has_specific_error(self):
        errors = candidate_errors(apply_mutation("template_data"))
        self.assertIn("placeholder-metadata:Data", errors)

    def test_marker_data_has_specific_error(self):
        errors = candidate_errors(apply_mutation("tbd_data"))
        self.assertIn("placeholder-metadata:Data", errors)

    def test_empty_data_exposes_multiline_regex_gap(self):
        self.assertEqual(candidate_errors(apply_mutation("empty_data")), [])

    def test_whitespace_data_exposes_multiline_regex_gap(self):
        self.assertEqual(candidate_errors(apply_mutation("whitespace_data")), [])


if __name__ == "__main__":
    unittest.main()
