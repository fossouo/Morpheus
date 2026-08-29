import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_manifest_temporal_corpus import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_manifest_temporal_corpus_cases.json"


class ExpertManifestTemporalCorpusTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.trial)

    def test_structural_compatibility_is_preserved_separately(self):
        self.assertEqual(self.summary["source_count"], 4)
        self.assertEqual(self.summary["source_expiry_matches"], 4)
        self.assertEqual(self.summary["structural_exact_matches"], 4)
        self.assertEqual(self.summary["structural_accepted"], 4)

    def test_date_aware_candidate_matches_all_lifecycle_expectations(self):
        self.assertEqual(self.summary["lifecycle_case_count"], 16)
        self.assertEqual(self.summary["candidate_lifecycle_exact_matches"], 16)
        self.assertEqual(self.summary["candidate_false_accepts"], 0)

    def test_structure_only_baseline_false_accepts_expired_states(self):
        self.assertEqual(self.summary["baseline_lifecycle_correct"], 11)
        self.assertEqual(self.summary["baseline_false_accepts"], 5)

    def test_inclusive_expiry_boundary_is_locked_for_every_source(self):
        self.assertEqual(self.summary["on_expiry_accepted"], 4)
        self.assertEqual(self.summary["after_expiry_rejected"], 4)

    def test_exp028_reference_date_has_three_active_sources(self):
        self.assertEqual(self.summary["promotion_date_exact_matches"], 4)
        self.assertEqual(self.summary["promotion_date_accepted"], 3)
        self.assertEqual(self.summary["promotion_date_expired"], 1)

    def test_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True))

    def test_fixture_rejects_contradictory_temporal_expectation(self):
        changed = copy.deepcopy(self.fixture)
        changed["sources"][0]["lifecycle_cases"][2]["expected_errors"] = []
        with self.assertRaisesRegex(ValueError, "contradicts inclusive expiry policy"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
