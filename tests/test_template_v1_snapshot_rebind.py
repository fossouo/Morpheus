import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import evaluate_template_v1_snapshot_rebind as snapshot_rebind


class TemplateV1SnapshotRebindTests(unittest.TestCase):
    def test_locked_run_reproduces_selector_shape_failure(self):
        fixture, _ = snapshot_rebind.load_fixture(snapshot_rebind.DEFAULT_FIXTURE)
        with self.assertRaisesRegex(ValueError, "temporal-corpus direct pin changed"):
            snapshot_rebind.run_trial(fixture)

    def test_snapshot_is_byte_exact_before_failed_trial(self):
        fixture, _ = snapshot_rebind.load_fixture(snapshot_rebind.DEFAULT_FIXTURE)
        template = (ROOT / fixture["template"]["path"]).read_bytes()
        snapshot = (ROOT / fixture["snapshot"]["path"]).read_bytes()
        self.assertEqual(snapshot, template)

    def test_source_hash_drift_stops_before_evaluation(self):
        fixture = json.loads(snapshot_rebind.DEFAULT_FIXTURE.read_text())
        fixture["direct_pins"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            with self.assertRaisesRegex(ValueError, "temporal-corpus hash mismatch"):
                snapshot_rebind.load_fixture(path)

    def test_direct_pin_set_is_locked(self):
        fixture = json.loads(snapshot_rebind.DEFAULT_FIXTURE.read_text())
        changed = copy.deepcopy(fixture)
        changed["direct_pins"].pop()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "direct pin set changed"):
                snapshot_rebind.load_fixture(path)


if __name__ == "__main__":
    unittest.main()
