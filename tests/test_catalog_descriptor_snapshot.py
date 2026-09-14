import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate_catalog_descriptor_snapshot as snapshot


class CatalogDescriptorSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = snapshot.load_fixture(
            snapshot.DEFAULT_FIXTURE
        )

    def _summary(self):
        first = snapshot.run_trial(self.fixture)
        second = snapshot.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_locked_snapshot_gate_passes(self):
        self.assertTrue(snapshot.accepted(self._summary(), self.fixture))

    def test_shared_reference_drifts_and_snapshot_does_not(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_correct"], 0)
        self.assertEqual(summary["candidate_correct"], 3)
        self.assertEqual(summary["baseline_locked_outcomes"], 3)
        self.assertEqual(summary["shared_reference_drifts"], 3)
        self.assertEqual(summary["snapshot_drifts"], 0)

    def test_mutations_are_isolated_from_other_descriptor(self):
        summary = self._summary()
        self.assertEqual(summary["mutations_visible_in_catalog"], 3)
        self.assertTrue(summary["only_locked_fields_changed"])
        self.assertTrue(summary["unselected_descriptors_unchanged"])
        self.assertTrue(summary["snapshot_bytes_unchanged"])

    def test_no_artifact_load_or_repository_write(self):
        summary = self._summary()
        self.assertTrue(summary["pre_mutation_selection_correct"])
        self.assertEqual(summary["artifact_load_attempts"], 0)
        self.assertEqual(summary["repository_writes"], 0)

    def test_pin_drift_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed["prior_experiment"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "fixture.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prior-experiment-hash-mismatch"):
                snapshot.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
