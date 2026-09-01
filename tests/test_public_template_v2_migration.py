import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_public_template_v2_migration import (  # noqa: E402
    load_fixture,
    migrate_template,
    project_to_source_v1,
    run_trial,
    validate_fixture,
)
from scripts.validate_expert_manifest import validate_manifest  # noqa: E402


FIXTURE_PATH = ROOT / "fixtures" / "expert_public_template_v2_migration_cases.json"


class PublicTemplateV2MigrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = load_fixture(FIXTURE_PATH)
        self.template = json.loads(
            (ROOT / "templates" / "expert-package.json").read_text(encoding="utf-8")
        )
        self.candidate = migrate_template(self.template, self.fixture["root"])

    def test_v1_baseline_and_v2_candidate_validate(self):
        from datetime import date

        reference_date = date.fromisoformat(self.fixture["reference_date"])
        self.assertEqual(validate_manifest(self.template, reference_date=reference_date), [])
        self.assertEqual(validate_manifest(self.candidate, reference_date=reference_date), [])

    def test_candidate_expires_only_after_pinned_expiry_day(self):
        from datetime import date

        expired_date = date.fromisoformat(self.fixture["expired_date"])
        self.assertEqual(
            validate_manifest(self.candidate, reference_date=expired_date), ["expired"]
        )

    def test_migration_projection_restores_exact_source_template(self):
        self.assertEqual(project_to_source_v1(self.candidate), self.template)

    def test_locked_trial_reproduces_record_shape_failure(self):
        with self.assertRaisesRegex(
            ValueError, "knowledge_records must be a non-empty list"
        ):
            run_trial(self.fixture)

    def test_fixture_rejects_template_hash_drift(self):
        changed = copy.deepcopy(self.fixture)
        changed["template"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "public template hash mismatch"):
            validate_fixture(changed)

    def test_projection_rejects_unrooted_scope(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["scope"]["include"][0] = "other/task"
        with self.assertRaisesRegex(ValueError, "unrooted scope"):
            project_to_source_v1(candidate)


if __name__ == "__main__":
    unittest.main()
