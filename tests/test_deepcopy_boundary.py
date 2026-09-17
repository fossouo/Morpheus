import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate_deepcopy_boundary as boundary


class DeepcopyBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = boundary.load_fixture(
            boundary.DEFAULT_FIXTURE
        )

    def _summary(self):
        first = boundary.run_trial(self.fixture)
        second = boundary.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_locked_boundary_gate_passes(self):
        self.assertTrue(boundary.accepted(self._summary(), self.fixture))

    def test_both_paths_preserve_and_isolate_cycle(self):
        summary = self._summary()
        self.assertTrue(summary["baseline_cycle_topology_preserved"])
        self.assertTrue(summary["baseline_cycle_source_isolated"])
        self.assertTrue(summary["candidate_cycle_topology_preserved"])
        self.assertTrue(summary["candidate_cycle_source_isolated"])
        self.assertEqual(summary["candidate_cycle_container_count"], 3)

    def test_gate_rejects_custom_hook_before_execution(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_hook_calls"], 1)
        self.assertTrue(summary["baseline_hook_source_mutated"])
        self.assertTrue(summary["baseline_hook_alias_retained"])
        self.assertTrue(summary["candidate_hook_rejected"])
        self.assertEqual(summary["candidate_hook_calls"], 0)
        self.assertTrue(summary["candidate_hook_source_unchanged"])

    def test_container_budget_fails_closed(self):
        graph = {"nested": []}
        with self.assertRaisesRegex(
            boundary.CopyBoundaryError, "container-budget-exceeded"
        ):
            boundary.validate_data_graph(graph, 1)

    def test_pin_drift_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed["prior_experiment"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "fixture.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "prior-experiment-hash-mismatch"
            ):
                boundary.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
