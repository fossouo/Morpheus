import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_expert_manifest_root import (  # noqa: E402
    build_manifest,
    load_fixture as load_manifest_fixture,
)
from scripts.evaluate_expert_manifest_v2_promotion import (  # noqa: E402
    promotion_candidate_errors,
)
from scripts.evaluate_expert_manifest_v2_temporal_promotion import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "expert_manifest_v2_temporal_promotion_cases.json"


class ExpertManifestV2TemporalPromotionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.trial)

    def test_candidate_adds_valid_v2_structural_acceptance(self):
        self.assertEqual(self.summary["structural_case_count"], 10)
        self.assertEqual(self.summary["baseline_structural_correct"], 8)
        self.assertEqual(self.summary["baseline_valid_v2_rejected"], 2)
        self.assertEqual(self.summary["candidate_structural_correct"], 10)
        self.assertEqual(self.summary["candidate_structural_false_accepts"], 0)

    def test_temporal_expectations_are_separate_and_exact(self):
        self.assertEqual(self.summary["temporal_source_count"], 4)
        self.assertEqual(self.summary["temporal_structural_exact_matches"], 4)
        self.assertEqual(self.summary["temporal_lifecycle_case_count"], 16)
        self.assertEqual(self.summary["temporal_lifecycle_exact_matches"], 16)
        self.assertEqual(self.summary["temporal_false_accepts"], 0)
        self.assertEqual(self.summary["promotion_date_accepted"], 3)
        self.assertEqual(self.summary["promotion_date_expired"], 1)

    def test_candidate_preserves_targets_and_regressions(self):
        self.assertEqual(self.summary["integration_target_parity"], 8)
        self.assertEqual(self.summary["integration_target_count"], 8)
        self.assertEqual(self.summary["integration_regression_parity"], 3)
        self.assertEqual(self.summary["integration_regression_count"], 3)

    def test_invalid_composition_and_rollback_remain_transactional(self):
        self.assertEqual(self.summary["integration_invalid_rejected"], 8)
        self.assertEqual(self.summary["integration_invalid_count"], 8)
        self.assertEqual(self.summary["integration_clean_states"], 8)
        self.assertEqual(self.summary["integration_rollback_matches"], 16)

    def test_promoted_validator_matches_locked_candidate(self):
        reference_date = date.fromisoformat("2026-08-28")
        manifest_fixture = load_manifest_fixture(
            ROOT / self.fixture["manifest_fixture"]["path"]
        )
        for case in manifest_fixture["cases"]:
            manifest = build_manifest(
                manifest_fixture["base_manifest"], case["mutation"]
            )
            self.assertEqual(
                validate_manifest(manifest, reference_date=reference_date),
                promotion_candidate_errors(manifest, reference_date=reference_date),
            )

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_source_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["temporal_fixture"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source fixture hash mismatch"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
