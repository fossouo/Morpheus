import copy
import unittest

from scripts import evaluate_template_joint_compatibility as joint


class TemplateJointCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = joint.load_fixture(joint.DEFAULT_FIXTURE)

    def _summary(self):
        first = joint.run_trial(self.fixture)
        second = joint.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_locked_joint_gate_passes(self):
        self.assertTrue(joint.accepted(self._summary(), self.fixture))

    def test_joint_selection_improves_over_independent_highest(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_correct"], 1)
        self.assertEqual(summary["candidate_correct"], 5)
        self.assertTrue(summary["partial_overlap_correct"])
        self.assertTrue(summary["narrow_overlap_correct"])

    def test_empty_intersection_and_ambiguity_fail_closed(self):
        summary = self._summary()
        self.assertTrue(summary["empty_intersection_rejected"])
        self.assertTrue(summary["ambiguous_joint_highest_rejected"])
        self.assertEqual(summary["load_attempts"], 0)

    def test_consumer_order_does_not_change_joint_selection(self):
        case = self.fixture["selection_cases"][0]
        descriptors = joint._catalog(self.fixture, case["catalog"])
        forward = joint.joint_highest_select(descriptors, case["consumers"])
        reverse = joint.joint_highest_select(descriptors, list(reversed(case["consumers"])))
        self.assertEqual(forward, reverse)

    def test_noncanonical_range_version_is_rejected(self):
        changed = copy.deepcopy(self.fixture["selection_cases"][0]["consumers"][0])
        changed["minimum"] = "1.00.0"
        with self.assertRaisesRegex(ValueError, "canonical numeric components"):
            joint._validate_policy(changed)

    def test_invalid_range_order_is_rejected(self):
        changed = copy.deepcopy(self.fixture["selection_cases"][0]["consumers"][0])
        changed["minimum"] = "1.2.0"
        with self.assertRaisesRegex(ValueError, "range policy is invalid"):
            joint._validate_policy(changed)


if __name__ == "__main__":
    unittest.main()
