import json
from datetime import date
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_expiry import (  # noqa: E402
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "expert_expiry_cases.json"


class ExpertExpiryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.results = evaluate_fixture(self.fixture)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(self.results)
        self.assertEqual(summary["case_count"], 7)
        self.assertEqual(summary["candidate_correct"], 7)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_syntax_only_baseline_false_accepts_expired_dates(self):
        self.assertEqual(summarize(self.results)["baseline_false_accepts"], 2)

    def test_repeated_evaluation_is_identical(self):
        repeated = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(self.results, sort_keys=True), json.dumps(repeated, sort_keys=True))

    def result_for(self, case_id: str) -> dict[str, str]:
        return next(result for result in self.results if result["id"] == case_id)

    def test_same_day_and_future_are_valid(self):
        self.assertEqual(self.result_for("same_day")["candidate"], "valid")
        self.assertEqual(self.result_for("future_date")["candidate"], "valid")

    def test_dates_before_reference_are_expired(self):
        reference_date = date.fromisoformat(self.fixture["reference_date"])
        for expiry in ("2026-08-07", "2025-08-08"):
            manifest = dict(self.fixture["base_manifest"], expires_on=expiry)
            self.assertIn("expired", validate_manifest(manifest, reference_date=reference_date))

    def test_syntax_faults_remain_invalid(self):
        for case_id in ("invalid_calendar", "noncanonical_compact", "non_string"):
            self.assertEqual(self.result_for(case_id)["candidate"], "invalid")


if __name__ == "__main__":
    unittest.main()
