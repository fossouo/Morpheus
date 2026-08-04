import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_metadata_lines import (  # noqa: E402
    apply_mutation,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_experiment_records import validate_record  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "metadata_line_cases.json"
FILENAME = "EXP-903-synthetic-metadata-line-record.md"


class MetadataLineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 16)
        self.assertEqual(summary["candidate_correct"], 16)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_prior_contract_false_accepts_declared_cases(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertGreaterEqual(summary["baseline_false_accepts"], 7)

    def test_candidate_has_no_cross_line_blank_captures(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["candidate_blank_spills"], 0)

    def test_prior_parser_spills_for_every_blank_field_case(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertGreaterEqual(summary["baseline_blank_spills"], 10)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_empty_data_has_specific_error(self):
        errors = validate_record(apply_mutation("empty_data"), FILENAME)
        self.assertIn("missing-metadata:Data", errors)

    def test_template_data_has_specific_error(self):
        errors = validate_record(apply_mutation("template_data"), FILENAME)
        self.assertIn("placeholder-metadata:Data", errors)


if __name__ == "__main__":
    unittest.main()
