import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_manifest import (  # noqa: E402
    build_manifest,
    evaluate_fixture,
    load_fixture,
    summarize,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "expert_manifest_cases.json"
TEMPLATE_PATH = ROOT / "templates" / "expert-package.json"


class ExpertManifestTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)

    def test_candidate_matches_all_predeclared_labels(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["case_count"], 10)
        self.assertEqual(summary["candidate_correct"], 10)
        self.assertEqual(summary["candidate_false_accepts"], 0)

    def test_key_only_baseline_false_accepts_all_invalid_cases(self):
        summary = summarize(evaluate_fixture(self.fixture))
        self.assertEqual(summary["baseline_false_accepts"], 9)

    def test_repeated_evaluation_is_identical(self):
        first = evaluate_fixture(self.fixture)
        second = evaluate_fixture(self.fixture)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def errors_for(self, case_id: str) -> list[str]:
        case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
        manifest = build_manifest(self.fixture["base_manifest"], case["mutation"])
        return validate_manifest(manifest)

    def test_scope_provenance_and_regression_fail_closed(self):
        self.assertIn("invalid-scope-list:exclude", self.errors_for("empty_scope_exclude"))
        self.assertIn("empty-provenance", self.errors_for("empty_provenance"))
        self.assertIn(
            "invalid-test-list:held_out_regression",
            self.errors_for("empty_held_out_regression"),
        )

    def test_lifecycle_requires_quarantine_and_rollback(self):
        self.assertIn("invalid-lifecycle-state", self.errors_for("premature_promotion"))
        self.assertIn("invalid-lifecycle-keys", self.errors_for("missing_rollback"))

    def test_layers_version_expiry_and_unknown_keys_fail_closed(self):
        self.assertIn("invalid-layer-keys", self.errors_for("merged_layers"))
        self.assertIn("invalid-version", self.errors_for("malformed_version"))
        self.assertIn("invalid-expiry", self.errors_for("invalid_expiry"))
        self.assertIn("unexpected-key:command", self.errors_for("unexpected_executable_field"))

    def test_public_template_satisfies_candidate_contract(self):
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(template), [])


if __name__ == "__main__":
    unittest.main()
