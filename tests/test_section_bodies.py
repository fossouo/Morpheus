import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_section_bodies import (  # noqa: E402
    FILENAME,
    apply_mutation,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_experiment_records import validate_record  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "section_body_cases.json"


class SectionBodyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 9)
        self.assertEqual(summary["candidate_correct"], 9)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_presence_only_baseline_false_accepts(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertGreaterEqual(summary["baseline_false_accepts"], 7)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_empty_body_has_specific_error(self):
        errors = validate_record(apply_mutation("empty_question"), FILENAME)
        self.assertIn("empty-section:Question", errors)

    def test_whitespace_body_has_specific_error(self):
        errors = validate_record(apply_mutation("whitespace_hypothesis"), FILENAME)
        self.assertIn("empty-section:Hypothesis", errors)

    def test_marker_body_has_specific_error(self):
        errors = validate_record(apply_mutation("tbd_baseline"), FILENAME)
        self.assertIn("placeholder-section:Baseline", errors)

    def test_template_prompt_has_specific_error(self):
        errors = validate_record(apply_mutation("template_question"), FILENAME)
        self.assertIn("placeholder-section:Question", errors)


if __name__ == "__main__":
    unittest.main()
