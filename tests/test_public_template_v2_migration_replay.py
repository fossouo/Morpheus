import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_public_template_v2_migration import (  # noqa: E402
    _packages as failed_packages,
    migrate_template,
)
from scripts.evaluate_public_template_v2_migration_replay import (  # noqa: E402
    BASELINE_FAILURE,
    adapter_change_is_shape_only,
    load_fixture,
    repaired_packages,
    reproduce_baseline_failure,
    run_trial,
    validate_fixture,
)


FIXTURE_PATH = (
    ROOT / "fixtures" / "expert_public_template_v2_migration_replay_cases.json"
)


class PublicTemplateV2MigrationReplayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        source_path = ROOT / self.fixture["source_fixture"]["path"]
        from scripts.evaluate_public_template_v2_migration import load_fixture as load_source

        self.source = load_source(source_path)
        template = json.loads(
            (ROOT / self.source["template"]["path"]).read_text(encoding="utf-8")
        )
        self.candidate = migrate_template(template, self.source["root"])

    def test_pinned_exp032_baseline_failure_is_reproduced(self):
        self.assertEqual(reproduce_baseline_failure(self.source), BASELINE_FAILURE)

    def test_repair_changes_only_knowledge_record_container(self):
        self.assertTrue(adapter_change_is_shape_only(self.candidate))
        before = failed_packages(self.candidate)
        after = repaired_packages(self.candidate)
        self.assertEqual(
            [package["manifest"] for package in after],
            [package["manifest"] for package in before],
        )

    def test_repaired_records_use_historical_list_shape(self):
        for package in repaired_packages(self.candidate):
            self.assertIsInstance(package["knowledge_records"], list)
            self.assertEqual(set(package["knowledge_records"][0]), {"id", "value"})

    def test_repaired_trial_reproduces_locked_exclusion_failure(self):
        trial = run_trial(self.source)
        first = trial["order_runs"][0]
        self.assertEqual(first["baseline_targets"], ["template-answer", "peer-answer"])
        self.assertEqual(first["stable_targets"], first["baseline_targets"])
        self.assertEqual(first["stable_regression"], "route-error:scope-not-found")
        self.assertEqual(first["baseline_exclusion"], "route-error:scope-not-found")
        self.assertEqual(first["stable_exclusion"], first["baseline_exclusion"])
        self.assertEqual(self.source["exclusion"]["expected"], "route-error:scope-excluded")

    def test_repaired_trial_repeats(self):
        self.assertEqual(run_trial(self.source), run_trial(self.source))

    def test_fixture_rejects_source_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["source_fixture"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source fixture hash mismatch"):
            validate_fixture(changed)

    def test_fixture_rejects_unregistered_adapter_change(self):
        changed = copy.deepcopy(self.fixture)
        changed["adapter_change"] = "different-change"
        with self.assertRaisesRegex(ValueError, "unsupported adapter change"):
            validate_fixture(changed)


if __name__ == "__main__":
    unittest.main()
