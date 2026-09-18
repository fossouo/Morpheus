import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate_deepcopy_window_mutation as window


class DeepcopyWindowMutationTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = window.load_fixture(window.DEFAULT_FIXTURE)

    def _summary(self):
        first = window.run_trial(self.fixture)
        second = window.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_importable_logic_matches_locked_expectations(self):
        self.assertTrue(window.accepted(self._summary(), self.fixture))

    def test_baseline_silently_copies_mutation(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_correct"], 1)
        self.assertEqual(summary["baseline_silent_drifts"], 1)
        self.assertTrue(summary["baseline_mutation_copy_matches_post_mutation"])

    def test_candidate_detects_mutation_without_returning_copy(self):
        summary = self._summary()
        self.assertEqual(summary["candidate_correct"], 2)
        self.assertEqual(summary["candidate_detected_mutations"], 1)
        self.assertEqual(
            summary["candidate_mutation_error"],
            "source-changed-during-copy-window",
        )
        self.assertFalse(summary["candidate_mutation_copy_returned"])

    def test_graph_digest_tracks_alias_topology(self):
        case = self.fixture["cases"][0]
        source = window._fresh_graph(case)
        isolated = copy.deepcopy(source)
        self.assertEqual(window.graph_digest(source), window.graph_digest(isolated))
        isolated["payload"][0]["back"] = isolated["payload"]
        self.assertNotEqual(window.graph_digest(source), window.graph_digest(isolated))

    def test_pin_drift_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed["prior_experiment"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "fixture.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "prior-experiment-hash-mismatch"
            ):
                window.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
