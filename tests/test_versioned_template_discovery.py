import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_versioned_template_discovery as discovery


class VersionedTemplateDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = discovery.load_fixture(
            discovery.DEFAULT_FIXTURE
        )

    def _summary(self):
        first = discovery.run_trial(self.fixture)
        second = discovery.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_locked_discovery_gate_passes(self):
        self.assertTrue(discovery.accepted(self._summary(), self.fixture))

    def test_second_consumer_is_independent_and_hash_bound(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_consumers"], 1)
        self.assertEqual(summary["candidate_consumers"], 2)
        self.assertTrue(summary["independent_consumer_valid"])
        self.assertTrue(summary["v2_hash_bound_selection"])

    def test_default_v1_and_incompatible_version_are_distinct(self):
        summary = self._summary()
        self.assertTrue(summary["default_v1_retained"])
        self.assertTrue(summary["incompatible_descriptor_discovered"])
        self.assertTrue(summary["incompatible_rejected"])
        self.assertEqual(summary["candidate_selection_correct"], 3)

    def test_routes_in_both_orders_and_unloads(self):
        summary = self._summary()
        self.assertEqual(summary["target_correct"], 4)
        self.assertEqual(summary["regression_correct"], 2)
        self.assertEqual(summary["exclusion_correct"], 2)
        self.assertEqual(summary["rollback_correct"], 4)
        self.assertTrue(summary["order_invariant"])

    def test_v2_removal_fails_closed_without_default_fallback(self):
        summary = self._summary()
        self.assertEqual(
            summary["versioned_after_removal"], "error:pinned-template-missing"
        )
        self.assertTrue(summary["no_v1_fallback_after_v2_removal"])
        self.assertIn("selected:expert-package-v1", summary["default_after_removal"])

    def test_hash_drift_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed["templates"][1]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "pinned-template-hash-mismatch"):
            discovery._read_pinned_at(
                ROOT, changed["templates"][1], "pinned-template"
            )


if __name__ == "__main__":
    unittest.main()
