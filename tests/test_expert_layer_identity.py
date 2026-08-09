import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_layer_identity import (  # noqa: E402
    build_manifest,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "expert_layer_identity_cases.json"


class ExpertLayerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.results = evaluate_fixture(self.fixture)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(self.results)
        self.assertEqual(summary["case_count"], 8)
        self.assertEqual(summary["candidate_correct"], 8)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_prior_contract_false_accepts_cross_layer_collisions(self):
        self.assertEqual(summarize(self.results)["baseline_false_accepts"], 5)

    def test_repeated_evaluation_is_identical(self):
        repeated = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(self.results, sort_keys=True), json.dumps(repeated, sort_keys=True))

    def manifest_for(self, case_id: str) -> dict:
        case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
        return build_manifest(self.fixture["base_manifest"], case["layers"])

    def test_exact_cross_layer_identity_is_reported_with_both_owners(self):
        errors = validate_manifest(self.manifest_for("knowledge_experience_collision"))
        self.assertEqual(
            errors,
            ["cross-layer-id-collision:shared-claim-v1:experience:knowledge"],
        )

    def test_three_layer_collision_reports_each_later_owner(self):
        errors = validate_manifest(self.manifest_for("three_layer_collision"))
        self.assertEqual(
            errors,
            [
                "cross-layer-id-collision:shared-component-v1:experience:skills",
                "cross-layer-id-collision:shared-component-v1:experience:tools",
            ],
        )

    def test_intra_layer_duplicate_remains_a_baseline_rejection(self):
        result = next(result for result in self.results if result["id"] == "intra_layer_duplicate")
        self.assertEqual(result["baseline"], "invalid")
        self.assertEqual(result["candidate"], "invalid")


if __name__ == "__main__":
    unittest.main()
