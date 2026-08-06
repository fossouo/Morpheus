import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_experiment_titles import (  # noqa: E402
    build_case,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_experiment_index import consistency_findings, validate_tree  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "experiment_title_cases.json"


class ExperimentTitleTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 7)
        self.assertEqual(summary["candidate_correct"], 7)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_exp007_baseline_false_accepts_all_invalid_title_cases(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["baseline_false_accepts"], 5)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def findings_for(self, case_id: str) -> list[str]:
        case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
        index_text, records = build_case(case)
        return consistency_findings(index_text, records)

    def test_escaped_pipe_matches_rendered_record_title(self):
        self.assertEqual(self.findings_for("valid_escaped_pipe"), [])

    def test_title_and_heading_id_mismatches_are_specific(self):
        self.assertIn("title-mismatch:EXP-900", self.findings_for("title_mismatch"))
        self.assertIn(
            "record-heading-id-mismatch:EXP-900",
            self.findings_for("heading_id_mismatch"),
        )

    def test_missing_duplicate_and_empty_headings_are_specific(self):
        self.assertIn("missing-record-heading:EXP-900", self.findings_for("missing_heading"))
        self.assertIn("duplicate-record-heading:EXP-900", self.findings_for("duplicate_heading"))
        self.assertIn("missing-record-title:EXP-900", self.findings_for("empty_heading_title"))

    def test_current_repository_titles_are_consistent(self):
        self.assertEqual(validate_tree(ROOT), [])


if __name__ == "__main__":
    unittest.main()
