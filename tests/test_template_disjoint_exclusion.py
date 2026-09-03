import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_disjoint_exclusion as diagnostic


class TemplateDisjointExclusionTests(unittest.TestCase):
    def test_response_equality_is_not_correctness(self):
        trial = {"order_runs": [
            {"baseline_exclusion": "same-wrong", "stable_exclusion": "same-wrong"},
            {"baseline_exclusion": "expected", "stable_exclusion": "different"},
        ]}
        self.assertEqual(diagnostic.exclusion_scores(trial, "expected"), {
            "response_equal": 1, "baseline_correct": 1, "candidate_correct": 0,
        })

    def test_literal_probe_respects_segment_boundaries(self):
        self.assertTrue(diagnostic.literal_prefix_match("root/task", "root/task/child"))
        self.assertFalse(diagnostic.literal_prefix_match("root/task", "root/taskish"))
        self.assertFalse(diagnostic.literal_prefix_match("root/task", "other/task"))
        for unsupported in ("root/*", "root//task", "root/../task"):
            with self.subTest(pattern=unsupported), self.assertRaises(ValueError):
                diagnostic.literal_prefix_match(unsupported, "root/task")

    def test_pinned_experiment_reproduces_without_source_mutation(self):
        source, size = diagnostic.load_inputs(diagnostic.DEFAULT_FIXTURE)
        before = copy.deepcopy(source)
        summary = diagnostic.evaluate(source)
        summary.update(fixture_bytes=size, evaluation_seconds=0, external_calls=0)
        self.assertTrue(diagnostic.accepted(summary))
        self.assertEqual(source, before)
        self.assertEqual(source["exclusion"]["expected"], diagnostic.OLD_EXPECTED)
        for field, value in (
            ("projection_exact", False), ("scope_lists_preserved", False),
            ("rollback_matches", 3), ("complete_outputs_unchanged", False),
            ("literal_matches", {"include": 1, "exclude": 1}),
            ("evaluation_seconds", 1), ("fixture_bytes", 16 * 1024),
        ):
            with self.subTest(field=field):
                changed = dict(summary, **{field: value})
                self.assertFalse(diagnostic.accepted(changed))

    def test_projection_failure_is_detected_independently_of_routing(self):
        source, _ = diagnostic.load_inputs(diagnostic.DEFAULT_FIXTURE)
        original_projection = diagnostic.project_to_source_v1

        def drop_exclusions(manifest):
            projected = original_projection(manifest)
            projected["scope"]["exclude"] = []
            return projected

        with patch.object(diagnostic, "project_to_source_v1", side_effect=drop_exclusions):
            summary = diagnostic.evaluate(source)
        self.assertTrue(summary["complete_outputs_unchanged"])
        self.assertEqual(summary["target_correct_pairs"], 4)
        self.assertFalse(summary["projection_exact"])
        self.assertFalse(summary["scope_lists_preserved"])

    def test_source_pin_drift_stops_before_trial(self):
        fixture = json.loads(diagnostic.DEFAULT_FIXTURE.read_text())
        fixture["source_fixture"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with patch.object(diagnostic, "run_trial") as trial:
                with self.assertRaisesRegex(ValueError, "EXP-033 fixture hash mismatch"):
                    diagnostic.load_inputs(path)
                trial.assert_not_called()


if __name__ == "__main__":
    unittest.main()
