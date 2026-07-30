from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.check_public_safety import scan_tree  # noqa: E402


class PublicSafetyTests(unittest.TestCase):
    def scan(self, text: str):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.md").write_text(text, encoding="utf-8")
            return scan_tree(root)

    def test_safe_research_text_passes(self):
        self.assertEqual(self.scan("compute_class: C2\nlatency_ms: 42\n"), [])

    def test_private_ipv4_is_blocked(self):
        value = "endpoint: http://192.168." + "1.12/service\n"
        self.assertTrue(self.scan(value))

    def test_tailscale_range_is_blocked(self):
        value = "endpoint: http://100." + "70.80.90/service\n"
        self.assertTrue(self.scan(value))

    def test_home_path_is_blocked(self):
        value = "artifact: /" + "Users/person/private/result.json\n"
        self.assertTrue(self.scan(value))

    def test_secret_assignment_is_blocked(self):
        value = "api" + "_key = 'not-a-real-but-long-secret'\n"
        self.assertTrue(self.scan(value))

    def test_gpu_uuid_is_blocked(self):
        value = "device: GPU-" + "12345678-abcd-1234-abcd-123456789abc\n"
        self.assertTrue(self.scan(value))

    def test_allow_marker_is_line_scoped(self):
        text = "example 192.168.1.1  # public-safety: allow-example\n"
        self.assertEqual(self.scan(text), [])


if __name__ == "__main__":
    unittest.main()
