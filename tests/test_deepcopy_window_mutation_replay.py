import copy
import unittest

from scripts import evaluate_deepcopy_window_mutation as prior
from scripts import evaluate_deepcopy_window_mutation_replay as replay


class DeepcopyWindowMutationReplayTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fixture_bytes = replay.load_replay_fixture(
            replay.DEFAULT_FIXTURE
        )

    def _summary(self):
        first = prior.run_trial(self.fixture)
        second = prior.run_trial(self.fixture)
        summary = dict(first)
        summary.update(
            replay_of="EXP-049",
            repeatable=first == second,
            fixture_bytes=self.fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        return summary

    def test_replay_reuses_exact_prior_fixture(self):
        prior_fixture, prior_bytes = prior.load_fixture(prior.DEFAULT_FIXTURE)
        self.assertEqual(self.fixture, prior_fixture)
        self.assertEqual(
            self.fixture_bytes,
            prior_bytes + replay.PRIOR_EXPERIMENT.stat().st_size,
        )

    def test_replay_matches_locked_scores(self):
        summary = self._summary()
        self.assertTrue(prior.accepted(summary, self.fixture))
        self.assertEqual(summary["baseline_correct"], 1)
        self.assertEqual(summary["candidate_correct"], 2)

    def test_replay_preserves_locked_mutation_outcome(self):
        summary = self._summary()
        self.assertEqual(summary["baseline_silent_drifts"], 1)
        self.assertEqual(summary["candidate_detected_mutations"], 1)
        self.assertEqual(
            summary["candidate_mutation_error"],
            "source-changed-during-copy-window",
        )
        self.assertFalse(summary["candidate_mutation_copy_returned"])

    def test_changed_threshold_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed["expected_candidate_correct"] = 1
        self.assertFalse(prior.accepted(self._summary(), changed))


if __name__ == "__main__":
    unittest.main()
