import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_stable_validator_integration import (  # noqa: E402
    load_fixture,
    run_trial,
    summarize,
    validate_fixture,
)


FIXTURE_PATH = ROOT / "fixtures" / "expert_stable_validator_integration_cases.json"


class StableValidatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.trial = run_trial(self.fixture)
        self.summary = summarize(self.trial)

    def test_stable_native_trial_matches_promoted_candidate_baseline(self):
        self.assertTrue(self.summary["trial_exact_match"])

    def test_targets_and_regressions_are_exact(self):
        self.assertEqual(self.summary["target_parity"], 8)
        self.assertEqual(self.summary["target_correct"], 8)
        self.assertEqual(self.summary["regression_parity"], 3)
        self.assertEqual(self.summary["regression_correct"], 3)

    def test_orders_and_probes_are_preserved(self):
        self.assertTrue(self.summary["order_invariant"])
        self.assertEqual(self.summary["probe_parity"], 2)

    def test_invalid_compositions_remain_transactional(self):
        self.assertEqual(self.summary["invalid_rejected"], 8)
        self.assertEqual(self.summary["invalid_count"], 8)
        self.assertEqual(self.summary["clean_states"], 8)

    def test_unload_restores_all_target_responses(self):
        self.assertEqual(self.summary["rollback_matches"], 16)

    def test_complete_trial_is_repeatable(self):
        repeated = run_trial(self.fixture)
        self.assertEqual(
            json.dumps(self.trial, sort_keys=True), json.dumps(repeated, sort_keys=True)
        )

    def test_fixture_rejects_source_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["integration_fixture"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source fixture hash mismatch"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
