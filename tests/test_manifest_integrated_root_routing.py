import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_manifest_integrated_root_routing import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_manifest_integrated_root_routing_cases.json"


class ManifestIntegratedRootRoutingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.fixture, self.trial)

    def test_manifest_integrated_routing_matches_sidecar_baseline(self):
        self.assertEqual(self.summary["target_count"], 8)
        self.assertEqual(self.summary["target_parity"], 8)
        self.assertEqual(self.summary["candidate_target_correct"], 8)

    def test_regressions_orders_and_probes_are_preserved(self):
        self.assertEqual(self.summary["regression_count"], 3)
        self.assertEqual(self.summary["regression_parity"], 3)
        self.assertEqual(self.summary["candidate_regression_correct"], 3)
        self.assertTrue(self.summary["candidate_order_invariant"])
        self.assertEqual(self.summary["probe_parity"], 2)

    def test_unload_restores_every_target_in_both_orders(self):
        self.assertEqual(self.summary["rollback_matches_baseline"], 16)

    def test_invalid_manifests_are_rejected_transactionally(self):
        self.assertEqual(self.summary["invalid_order_count"], 8)
        self.assertEqual(self.summary["invalid_manifests_rejected"], 8)
        self.assertEqual(self.summary["invalid_states_clean"], 8)

    def test_historical_v1_validation_is_unchanged(self):
        self.assertEqual(self.summary["historical_v1_count"], 4)
        self.assertEqual(self.summary["historical_v1_accepted"], 4)
        self.assertEqual(self.summary["historical_v1_exact_matches"], 4)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_source_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["routing_fixture"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source fixture hash mismatch"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
