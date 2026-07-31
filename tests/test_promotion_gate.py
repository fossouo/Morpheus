import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_promotion_gate import (  # noqa: E402
    evaluate_fixture,
    load_fixture,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "promotion_gate_cases.json"


class PromotionGateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_guarded_gate_matches_predeclared_oracle(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 5)
        self.assertEqual(summary["guarded_correct"], 5)
        self.assertEqual(summary["guarded_false_promotions"], 0)

    def test_target_only_baseline_false_promotes_regressive_gain(self):
        results = {result["id"]: result for result in evaluate_fixture(self.fixture)}
        self.assertEqual(results["regressive_gain"]["baseline"], "promote")
        self.assertEqual(results["regressive_gain"]["guarded"], "quarantine")

    def test_boundary_is_inclusive(self):
        results = {result["id"]: result for result in evaluate_fixture(self.fixture)}
        self.assertEqual(results["inclusive_boundary"]["guarded"], "promote")

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_rejects_out_of_range_score(self):
        invalid = copy.deepcopy(self.fixture)
        invalid["cases"][0]["candidate"]["target"] = 1001
        with self.assertRaises(ValueError):
            validate_fixture(invalid)

    def test_rejects_duplicate_case_id(self):
        invalid = copy.deepcopy(self.fixture)
        invalid["cases"][1]["id"] = invalid["cases"][0]["id"]
        with self.assertRaises(ValueError):
            validate_fixture(invalid)


if __name__ == "__main__":
    unittest.main()
