import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_manifest_root import (  # noqa: E402
    build_manifest,
    candidate_errors,
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_manifest_root_cases.json"


class ExpertManifestRootTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.trial)

    def test_candidate_discriminates_all_locked_cases(self):
        self.assertEqual(self.summary["case_count"], 10)
        self.assertEqual(self.summary["candidate_correct"], 10)
        self.assertEqual(self.summary["candidate_false_accepts"], 0)
        self.assertEqual(self.summary["candidate_expected_errors"], 10)

    def test_presence_only_baseline_false_accepts_six_invalid_cases(self):
        self.assertEqual(self.summary["baseline_correct"], 4)
        self.assertEqual(self.summary["baseline_false_accepts"], 6)

    def test_missing_wildcard_and_nested_roots_fail_closed(self):
        expected = {
            "missing_root": "missing-key:root",
            "empty_root": "invalid-root",
            "wildcard_root": "invalid-root",
            "partial_wildcard_root": "invalid-root",
            "nested_root": "invalid-root",
            "dot_root": "invalid-root",
        }
        for case_id, error in expected.items():
            case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
            manifest = build_manifest(self.fixture["base_manifest"], case["mutation"])
            self.assertIn(error, candidate_errors(manifest))

    def test_literal_scope_roots_must_match_declared_root(self):
        expected = {
            "include_literal_root_mismatch": (
                "scope-root-mismatch:include:auxiliary/blue/item"
            ),
            "exclude_literal_root_mismatch": (
                "scope-root-mismatch:exclude:auxiliary/red/document/restricted"
            ),
        }
        for case_id, error in expected.items():
            case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
            manifest = build_manifest(self.fixture["base_manifest"], case["mutation"])
            self.assertIn(error, candidate_errors(manifest))

    def test_valid_literal_and_root_owned_wildcard_patterns_are_accepted(self):
        for case_id in ("valid_mixed_patterns", "valid_literal_patterns"):
            case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
            manifest = build_manifest(self.fixture["base_manifest"], case["mutation"])
            self.assertEqual(candidate_errors(manifest), [])

    def test_candidate_preserves_locked_v1_validation_exactly(self):
        self.assertEqual(self.summary["historical_v1_count"], 4)
        self.assertEqual(self.summary["historical_v1_accepted"], 4)
        self.assertEqual(self.summary["historical_v1_exact_matches"], 4)

    def test_trial_is_repeatable_and_fixture_shape_is_locked(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True))
        changed = copy.deepcopy(self.fixture)
        changed["historical_v1_sources"].pop()
        with self.assertRaisesRegex(ValueError, "exactly four historical"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
