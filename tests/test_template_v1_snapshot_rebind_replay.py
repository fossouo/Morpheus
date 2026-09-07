import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_v1_snapshot_rebind_replay as replay


class TemplateV1SnapshotRebindReplayTests(unittest.TestCase):
    def test_locked_replay_reproduces_transitive_pin_failure(self):
        fixture, prior, fixture_bytes = replay.load_fixture(replay.DEFAULT_FIXTURE)
        first = replay.run_trial(fixture, prior)
        second = replay.run_trial(fixture, prior)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        self.assertFalse(replay.accepted(summary, fixture))
        self.assertEqual(summary["transitive_pins"], 6)
        self.assertEqual(fixture["expected_transitive_pins"], 3)

    def test_legacy_selector_failure_is_preserved(self):
        fixture, prior, _ = replay.load_fixture(replay.DEFAULT_FIXTURE)
        self.assertEqual(replay._legacy_error(prior), fixture["expected_legacy_error"])

    def test_full_source_rebind_changes_only_path(self):
        _, prior, _ = replay.load_fixture(replay.DEFAULT_FIXTURE)
        source = next(item for item in prior["direct_pins"] if item["id"] == "temporal-corpus")
        original = json.loads((ROOT / source["path"]).read_text())
        rebound, repaired = replay._rebound_path_member(source, prior["snapshot"])
        original_source = next(item for item in original["sources"] if item["id"] == "public-template")
        rebound_source = next(item for item in rebound["sources"] if item["id"] == "public-template")
        expected = copy.deepcopy(original_source)
        expected["path"] = prior["snapshot"]["path"]
        self.assertTrue(repaired)
        self.assertEqual(rebound_source, expected)

    def test_prior_experiment_hash_drift_stops(self):
        fixture = json.loads(replay.DEFAULT_FIXTURE.read_text())
        fixture["prior_experiment"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with self.assertRaisesRegex(ValueError, "EXP-037 hash mismatch"):
                replay.load_fixture(path)

    def test_prior_fixture_hash_drift_stops(self):
        fixture = json.loads(replay.DEFAULT_FIXTURE.read_text())
        fixture["prior_fixture"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with self.assertRaisesRegex(ValueError, "EXP-037 fixture hash mismatch"):
                replay.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
