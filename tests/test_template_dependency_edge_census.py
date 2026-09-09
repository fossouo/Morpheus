import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_dependency_edge_census as census


class TemplateDependencyEdgeCensusTests(unittest.TestCase):
    def test_locked_census_and_strategy_comparison_pass(self):
        fixture, prior_config, prior_fixture, fixture_bytes = census.load_fixture(
            census.DEFAULT_FIXTURE
        )
        first = census.run_trial(fixture, prior_config, prior_fixture)
        second = census.run_trial(fixture, prior_config, prior_fixture)
        summary = dict(first)
        summary.update(
            repeatable=first == second,
            fixture_bytes=fixture_bytes,
            evaluation_seconds=0,
            external_calls=0,
        )
        self.assertTrue(census.accepted(summary, fixture))

    def test_census_separates_consumer_and_evidence_edges(self):
        fixture, _, prior_fixture, _ = census.load_fixture(census.DEFAULT_FIXTURE)
        edges = census.census_edges(
            prior_fixture["direct_pins"], fixture["evidence_fixture"]["path"]
        )
        self.assertEqual(edges, sorted(fixture["expected_edges"], key=lambda item: (
            item["class"], item["referrer"], item["pointer"], item["source_id"]
        )))

    def test_versioned_path_preserves_all_six_edges(self):
        fixture, prior_config, prior_fixture, _ = census.load_fixture(
            census.DEFAULT_FIXTURE
        )
        summary = census.run_trial(fixture, prior_config, prior_fixture)
        self.assertEqual(summary["in_place"]["edges_preserved"], 0)
        self.assertEqual(summary["versioned"]["edges_preserved"], 6)
        self.assertTrue(summary["versioned_path_available_at_measurement"])
        self.assertFalse(summary["migration_ready"])

    def test_sha_edge_pointer_escapes_tokens(self):
        value = {"a/b": [{"sha256": "digest"}], "til~de": {"sha256": "other"}}
        self.assertEqual(
            list(census._sha_edges(value)),
            [("/a~1b/0/sha256", "digest"), ("/til~0de/sha256", "other")],
        )

    def test_prior_experiment_hash_drift_stops(self):
        fixture = json.loads(census.DEFAULT_FIXTURE.read_text())
        fixture["prior_experiment"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with self.assertRaisesRegex(ValueError, "EXP-038 hash mismatch"):
                census.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
