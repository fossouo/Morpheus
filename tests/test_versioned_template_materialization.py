import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_versioned_template_materialization as materialization


class VersionedTemplateMaterializationTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = materialization.load_fixture(
            materialization.DEFAULT_FIXTURE
        )

    def _summary(self):
        first = materialization.run_trial(self.fixture)
        second = materialization.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_locked_materialization_gate_passes(self):
        self.assertTrue(materialization.accepted(self._summary(), self.fixture))

    def test_historical_v1_edges_remain_exact(self):
        summary = self._summary()
        self.assertTrue(summary["historical_edges_preserved"])
        self.assertEqual(summary["historical_edge_total"], 6)
        self.assertTrue(summary["snapshot_byte_exact"])

    def test_versioned_artifact_is_canonical_and_lifecycle_bounded(self):
        summary = self._summary()
        self.assertTrue(summary["versioned_byte_canonical"])
        self.assertTrue(summary["versioned_valid"])
        self.assertTrue(summary["versioned_expired_next_day"])
        self.assertTrue(summary["projection_exact"])

    def test_materialized_consumer_routes_and_rolls_back(self):
        summary = self._summary()
        self.assertEqual(summary["candidate_materialized_consumers"], 1)
        self.assertEqual(summary["target_correct"], 4)
        self.assertEqual(summary["regression_correct"], 2)
        self.assertEqual(summary["exclusion_correct"], 2)
        self.assertEqual(summary["rollback_correct"], 4)
        self.assertTrue(summary["order_invariant"])

    def test_temporary_removal_fails_closed_and_preserves_v1(self):
        summary = self._summary()
        self.assertEqual(
            summary["versioned_removal_error"], "versioned-template-missing"
        )
        self.assertTrue(summary["versioned_absent_after_removal"])
        self.assertTrue(summary["public_v1_survives_removal"])

    def test_fixture_rejects_versioned_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["versioned_template"]["sha256"] = "0" * 64
        path = ROOT / "templates" / "expert-package-v2.json"
        with self.assertRaisesRegex(ValueError, "versioned-template-hash-mismatch"):
            materialization._read_pinned_at(
                ROOT, changed["versioned_template"], "versioned-template"
            )
        self.assertEqual(json.loads(path.read_text())["schema"], "expert-package-v2")


if __name__ == "__main__":
    unittest.main()
