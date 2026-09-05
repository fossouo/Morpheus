import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_public_template_v2_decision as decision


class PublicTemplateV2DecisionTests(unittest.TestCase):
    def test_locked_decision_defers_in_place_migration(self):
        fixture, size = decision.load_fixture(decision.DEFAULT_FIXTURE)
        first = decision.run_trial(fixture)
        summary = dict(first, repeatable=first == decision.run_trial(fixture),
                       fixture_bytes=size, evaluation_seconds=0, external_calls=0)
        self.assertTrue(decision.accepted(summary))
        self.assertTrue(summary["functional_ready"])
        self.assertFalse(summary["migration_ready"])
        self.assertEqual(summary["candidate_direct_pins_preserved"], 0)

    def test_each_migration_safety_threshold_is_required(self):
        fixture, size = decision.load_fixture(decision.DEFAULT_FIXTURE)
        first = decision.run_trial(fixture)
        summary = dict(first, repeatable=True, fixture_bytes=size,
                       evaluation_seconds=0, external_calls=0)
        for field, value in (
            ("candidate_valid", False), ("projection_exact", False),
            ("disjoint_evidence_passed", False),
            ("reachability_evidence_passed", False),
            ("disjoint_target_pairs", 3), ("reachability_path_correct", 7),
            ("current_direct_pins_valid", 2),
            ("candidate_direct_pins_preserved", 1),
            ("migration_ready", True), ("repeatable", False),
            ("evaluation_seconds", 1), ("external_calls", 1),
        ):
            with self.subTest(field=field):
                self.assertFalse(decision.accepted(dict(summary, **{field: value})))

    def test_evidence_hash_drift_stops_before_evaluation(self):
        fixture = json.loads(decision.DEFAULT_FIXTURE.read_text())
        fixture["evidence"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with self.assertRaisesRegex(ValueError, "EXP-034 hash mismatch"):
                decision.load_fixture(path)

    def test_direct_pin_set_is_locked(self):
        fixture = json.loads(decision.DEFAULT_FIXTURE.read_text())
        changed = copy.deepcopy(fixture)
        changed["direct_template_pins"].pop()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "direct template pin set changed"):
                decision.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
