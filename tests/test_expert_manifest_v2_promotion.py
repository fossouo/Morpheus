import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_manifest_v2_promotion import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)
from scripts.evaluate_expert_manifest_root import (  # noqa: E402
    build_manifest,
    load_fixture as load_manifest_fixture,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "expert_manifest_v2_promotion_cases.json"


class ExpertManifestV2PromotionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.trial)

    def test_candidate_v2_matches_quarantined_contract(self):
        self.assertEqual(self.summary["structural_case_count"], 10)
        self.assertEqual(self.summary["candidate_v2_exact_matches"], 10)
        self.assertEqual(self.summary["candidate_v2_correct"], 10)
        self.assertEqual(self.summary["candidate_v2_false_accepts"], 0)

    def test_current_date_expires_one_historical_v1_source(self):
        self.assertEqual(self.summary["historical_v1_count"], 4)
        self.assertEqual(self.summary["historical_v1_accepted"], 3)
        self.assertEqual(self.summary["historical_v1_exact_matches"], 3)

    def test_candidate_gate_preserves_targets_and_regressions(self):
        self.assertEqual(self.summary["integration_target_parity"], 8)
        self.assertEqual(self.summary["integration_target_count"], 8)
        self.assertEqual(self.summary["integration_regression_parity"], 3)
        self.assertEqual(self.summary["integration_regression_count"], 3)

    def test_candidate_gate_rejects_invalid_manifests_transactionally(self):
        self.assertEqual(self.summary["integration_invalid_rejected"], 8)
        self.assertEqual(self.summary["integration_invalid_count"], 8)
        self.assertEqual(self.summary["integration_clean_states"], 8)

    def test_candidate_gate_preserves_rollback(self):
        self.assertEqual(self.summary["integration_rollback_matches"], 16)

    def test_complete_candidate_trial_matches_quarantine_and_repeats(self):
        self.assertTrue(self.summary["quarantine_candidate_trial_exact_match"])
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_failed_candidate_is_not_promoted(self):
        manifest_fixture = load_manifest_fixture(
            ROOT / "fixtures" / "expert_manifest_root_cases.json"
        )
        manifest = build_manifest(
            manifest_fixture["base_manifest"], manifest_fixture["cases"][0]["mutation"]
        )
        self.assertEqual(validate_manifest(manifest), ["unexpected-key:root"])

    def test_fixture_rejects_source_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["manifest_fixture"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source fixture hash mismatch"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
