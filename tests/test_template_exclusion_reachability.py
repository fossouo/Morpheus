import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_exclusion_reachability as evaluation


class TemplateExclusionReachabilityTests(unittest.TestCase):
    def test_literal_oracle_respects_segment_boundaries(self):
        self.assertTrue(evaluation.literal_prefix_match("root/task", "root/task/child"))
        self.assertFalse(evaluation.literal_prefix_match("root/task", "root/taskish"))
        for unsupported in ("root/*", "root//task", "root/../task"):
            with self.subTest(pattern=unsupported), self.assertRaises(ValueError):
                evaluation.literal_prefix_match(unsupported, "root/task")

    def test_locked_pair_passes_all_thresholds(self):
        fixture = evaluation.load_fixture(evaluation.DEFAULT_FIXTURE)
        first = evaluation.run_trial(fixture)
        summary = evaluation.summarize(fixture, first)
        summary.update(
            repeatable=first == evaluation.run_trial(fixture),
            fixture_bytes=1,
            evaluation_seconds=0,
            external_calls=0,
        )
        self.assertTrue(evaluation.accepted(summary))
        self.assertEqual(summary["exclude_only_baseline_correct"], 1)
        self.assertEqual(summary["reachable_oracle_correct"], 2)

    def test_each_threshold_is_required(self):
        fixture = evaluation.load_fixture(evaluation.DEFAULT_FIXTURE)
        first = evaluation.run_trial(fixture)
        summary = evaluation.summarize(fixture, first)
        summary.update(repeatable=True, fixture_bytes=1, evaluation_seconds=0, external_calls=0)
        for field, value in (
            ("candidate_manifests_valid", 1), ("oracle_counts_correct", 1),
            ("exclude_only_baseline_correct", 2), ("reachable_oracle_correct", 1),
            ("pair_path_parity", 3), ("pair_path_correct", 7),
            ("allowed_path_correct", 7), ("absent_path_correct", 7),
            ("rollback_correct", 7), ("order_invariant", False),
            ("repeatable", False), ("fixture_bytes", 16 * 1024),
            ("evaluation_seconds", 1), ("external_calls", 1),
        ):
            with self.subTest(field=field):
                self.assertFalse(evaluation.accepted(dict(summary, **{field: value})))

    def test_template_pin_drift_stops_loading(self):
        fixture = json.loads(evaluation.DEFAULT_FIXTURE.read_text())
        fixture["template"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with self.assertRaisesRegex(ValueError, "public template hash mismatch"):
                evaluation.load_fixture(path)

    def test_fixture_expectation_is_locked(self):
        fixture = evaluation.load_fixture(evaluation.DEFAULT_FIXTURE)
        changed = copy.deepcopy(fixture)
        changed["cases"][0]["expected"] = "route-error:scope-excluded"
        trial = evaluation.run_trial(changed)
        summary = evaluation.summarize(changed, trial)
        self.assertEqual(summary["pair_path_correct"], 4)
        self.assertEqual(summary["reachable_oracle_correct"], 1)


if __name__ == "__main__":
    unittest.main()
