"""Validate metadata normalization without executing upstream application code."""
import hashlib
import importlib.util
import io
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("upstream_preparation", ROOT / "scripts/prepare_upstream.py")
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


class UpstreamWheelTests(unittest.TestCase):
    def wheel(self):
        """Build a tiny wheel fixture with the known malformed dependency line and an asset."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("shuup-3.1.0.dist-info/METADATA", "Name: shuup\nVersion: 3.1.0\nRequires-Dist: toml (<1pytz>=2015.4,>=0.10.0)\n")
            archive.writestr("shuup/static/theme.css", "body { color: black; }")
            archive.writestr("shuup-3.1.0.dist-info/RECORD", "")
        return buffer.getvalue()

    def test_original_checksum_is_required_before_rewriting(self):
        """Reject untrusted bytes before any metadata is changed."""
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            upstream.normalize_wheel(self.wheel(), "0" * 64)

    def test_metadata_is_repaired_without_changing_assets(self):
        """Split the invalid requirement and retain payload bytes while rebuilding RECORD."""
        payload = self.wheel()
        output = upstream.normalize_wheel(payload, hashlib.sha256(payload).hexdigest())
        with zipfile.ZipFile(io.BytesIO(output)) as archive:
            metadata = archive.read("shuup-3.1.0.dist-info/METADATA").decode()
            self.assertIn("Requires-Dist: toml (<1,>=0.10.0)\nRequires-Dist: pytz (>=2015.4)", metadata)
            self.assertEqual(archive.read("shuup/static/theme.css"), b"body { color: black; }")
            self.assertIn(b"sha256=", archive.read("shuup-3.1.0.dist-info/RECORD"))
