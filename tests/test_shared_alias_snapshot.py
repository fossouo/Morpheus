import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate_shared_alias_snapshot as snapshot


class SharedAliasSnapshotTests(unittest.TestCase):
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

    def test_locked_shared_alias_gate_passes(self):
        self.assertTrue(snapshot.accepted(self._summary(), self.fixture))

    def test_json_loses_alias_semantics_but_deepcopy_preserves_them(self):
        summary = self._summary()
        self.assertEqual(summary["json_correct"], 0)
        self.assertEqual(summary["json_alias_losses"], 3)
        self.assertEqual(summary["deepcopy_correct"], 3)
        self.assertEqual(summary["deepcopy_alias_preservations"], 3)

    def test_only_deep_strategies_isolate_the_catalog(self):
        summary = self._summary()
        self.assertEqual(summary["shared_source_isolations"], 0)
        self.assertEqual(summary["shallow_source_isolations"], 0)
        self.assertEqual(summary["deepcopy_source_isolations"], 3)
        self.assertEqual(summary["json_source_isolations"], 3)
        self.assertTrue(summary["only_locked_leaves_changed"])

    def test_no_artifact_load_or_repository_write(self):
        summary = self._summary()
        self.assertTrue(summary["pre_payloads_locked"])
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
