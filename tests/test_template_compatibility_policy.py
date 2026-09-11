import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_compatibility_policy as compatibility


class TemplateCompatibilityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = compatibility.load_fixture(
            compatibility.DEFAULT_FIXTURE
        )

    def _summary(self):
        first = compatibility.run_trial(self.fixture)
        second = compatibility.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_locked_compatibility_gate_passes(self):
        self.assertTrue(compatibility.accepted(self._summary(), self.fixture))

    def test_candidate_improves_on_patch_and_minor_selection(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_correct"], 1)
        self.assertEqual(summary["candidate_correct"], 5)
        self.assertTrue(summary["highest_patch_correct"])
        self.assertTrue(summary["highest_minor_correct"])

    def test_no_match_and_highest_ambiguity_fail_closed(self):
        summary = self._summary()
        self.assertTrue(summary["no_match_rejected"])
        self.assertTrue(summary["ambiguity_rejected"])

    def test_removal_does_not_downgrade_to_remaining_version(self):
        summary = self._summary()
        self.assertTrue(summary["lower_candidates_remain"])
        self.assertEqual(summary["removal_after"], "error:pinned-template-missing")
        self.assertTrue(summary["no_downgrade_after_removal"])

    def test_materialized_hash_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            compatibility.materialize_artifacts(base, self.fixture)
            descriptor = copy.deepcopy(self.fixture["artifacts"][1])
            target = base / descriptor["path"]
            value = json.loads(target.read_text(encoding="utf-8"))
            value["package_id"] = "drifted-package"
            target.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pinned-template-hash-mismatch"):
                compatibility._read_pinned_at(base, descriptor, "pinned-template")

    def test_noncanonical_policy_version_is_rejected(self):
        changed = copy.deepcopy(self.fixture["selection_cases"][1]["policy"])
        changed["minimum"] = "1.00.1"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            compatibility.materialize_artifacts(base, self.fixture)
            result = compatibility.compatible_select_at(
                base, compatibility._catalog(self.fixture, "patch"), changed
            )
        self.assertEqual(result, "error:invalid-compatibility-policy")


if __name__ == "__main__":
    unittest.main()
