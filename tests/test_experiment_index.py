import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_experiment_index import (  # noqa: E402
    apply_mutation,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_experiment_index import consistency_findings, validate_tree  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "experiment_index_cases.json"


class ExperimentIndexTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 8)
        self.assertEqual(summary["candidate_correct"], 8)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_count_only_baseline_false_accepts_declared_cases(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertGreaterEqual(summary["baseline_false_accepts"], 5)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_duplicate_identifier_has_specific_findings(self):
        index_text, records = apply_mutation("duplicate_index_id")
        findings = consistency_findings(index_text, records)
        self.assertIn("duplicate-index-id:EXP-901", findings)
        self.assertIn("missing-index-entry:EXP-902", findings)

    def test_orphan_replacement_has_specific_findings(self):
        index_text, records = apply_mutation("orphan_replacement")
        findings = consistency_findings(index_text, records)
        self.assertIn("orphan-index-entry:EXP-999", findings)
        self.assertIn("missing-index-entry:EXP-902", findings)

    def test_status_and_verdict_mismatches_are_specific(self):
        status_index, status_records = apply_mutation("status_mismatch")
        verdict_index, verdict_records = apply_mutation("verdict_mismatch")
        self.assertIn("status-mismatch:EXP-901", consistency_findings(status_index, status_records))
        self.assertIn("verdict-mismatch:EXP-902", consistency_findings(verdict_index, verdict_records))

    def test_current_repository_index_is_consistent(self):
        self.assertEqual(validate_tree(ROOT), [])


if __name__ == "__main__":
    unittest.main()
