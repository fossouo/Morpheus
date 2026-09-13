import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate_joint_template_pinned_materialization as materialization


class JointTemplatePinnedMaterializationTests(unittest.TestCase):
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

    def test_locked_pinned_materialization_gate_passes(self):
        self.assertTrue(materialization.accepted(self._summary(), self.fixture))

    def test_pinned_candidate_prevents_silent_downgrade(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_correct"], 1)
        self.assertEqual(summary["candidate_correct"], 3)
        self.assertEqual(summary["baseline_locked_outcomes"], 3)
        self.assertEqual(summary["baseline_silent_downgrades"], 2)
        self.assertEqual(summary["candidate_silent_downgrades"], 0)

    def test_removal_and_mutation_are_distinguished(self):
        summary = self._summary()
        self.assertTrue(summary["removal_rejected"])
        self.assertTrue(summary["mutation_rejected"])

    def test_lower_artifact_remains_exact_and_temporary_roots_are_removed(self):
        summary = self._summary()
        self.assertEqual(summary["lower_present_and_exact"], 3)
        self.assertEqual(summary["materialized_artifact_counts"], [2, 2, 2])
        self.assertTrue(summary["temporary_roots_removed"])
        self.assertEqual(summary["repository_writes"], 0)

    def test_pin_drift_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed["prior_experiment"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "fixture.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prior-experiment-hash-mismatch"):
                materialization.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
