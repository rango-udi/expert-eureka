"""Verify private settings, destructive boundaries and process ownership without stopping real servers."""

from pathlib import Path
from unittest.mock import patch, Mock
import importlib.util
import json
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("container_cmdc", ROOT / "scripts/commands.py")
cmdc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmdc)
configuration = __import__("scripts.configuration", fromlist=["ensure"])


class RuntimeTests(unittest.TestCase):
    def test_linked_database_root_is_rejected_before_writing(self):
        """Reject a runtime data link before reset or initialization can touch outside files."""
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".runtime").mkdir()
        try:
            (self.root / ".runtime/data").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlinks are not available for this account.")
        with self.assertRaisesRegex(ValueError, "filesystem link"):
            configuration.ensure(self.root)
        self.assertFalse((self.root / ".env").exists())

    def setUp(self):
        """Create a project-local disposable directory with the real configuration template."""
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix="runtime-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / ".env.template", self.root)

    def test_env_is_generated_from_dot_template(self):
        """Use a custom value from .env.template when creating the first private environment."""
        template = self.root / ".env.template"
        template.write_text(template.read_text().replace("WEB_THREADS=1", "WEB_THREADS=3"))
        values = configuration.ensure(self.root)
        self.assertEqual(values["WEB_THREADS"], "3")
        self.assertIn("WEB_THREADS=3", (self.root / ".env").read_text())
        self.assertTrue(template.exists())

    def test_missing_dot_template_has_actionable_error(self):
        """Reject the old template name instead of silently generating from an obsolete file."""
        (self.root / ".env.template").rename(self.root / "env.template")
        with self.assertRaisesRegex(ValueError, "The .env.template file is missing"):
            configuration.ensure(self.root)
        self.assertFalse((self.root / ".env").exists())

    def test_secrets_are_distinct_and_preserved(self):
        """Generate independent account secrets once and preserve them on repeated initialization."""
        first = configuration.ensure(self.root)
        second = configuration.ensure(self.root)
        self.assertEqual(first, second)
        self.assertEqual(len({first[key] for key in configuration.SECRET_KEYS}), 4)

    def test_blank_limit_uses_compose_default(self):
        """Preserve a blank Docker limit for Compose default interpolation."""
        (self.root / ".env").write_text("APP_MEMORY_LIMIT=\n")
        self.assertEqual(configuration.ensure(self.root)["APP_MEMORY_LIMIT"], "")

    def test_invalid_limit_does_not_create_configuration(self):
        """Reject a malformed memory setting before saving private configuration."""
        path = self.root / ".env.template"
        path.write_text(path.read_text().replace("APP_MEMORY_LIMIT=384m", "APP_MEMORY_LIMIT=bad"))
        with self.assertRaisesRegex(ValueError, "APP_MEMORY_LIMIT"):
            configuration.ensure(self.root)
        self.assertFalse((self.root / ".env").exists())

    def test_explicit_zero_disables_container_limit(self):
        """Accept an operator's explicit choice to remove a Docker limit."""
        values = configuration.ensure(self.root)
        values["APP_MEMORY_LIMIT"] = "0"
        configuration.validate(values)

    def test_duplicate_setting_is_rejected(self):
        """Reject repeated dotenv keys instead of silently using an ambiguous value."""
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            configuration.parse("WEB_THREADS=1\nWEB_THREADS=2")

    def test_unknown_setting_is_preserved(self):
        """Keep an operator's additional setting when secrets and defaults are filled."""
        (self.root / ".env").write_text("CUSTOM_SETTING=kept\n")
        self.assertEqual(configuration.ensure(self.root)["CUSTOM_SETTING"], "kept")

    def test_restore_rejects_traversal_before_stopping_server(self):
        """Reject a malicious ZIP member before touching the database or running process."""
        import zipfile

        (self.root / "backups").mkdir()
        with zipfile.ZipFile(self.root / "backups/bad.zip", "w") as archive:
            archive.writestr("db.sqlite3", "placeholder")
            archive.writestr("../outside", "unsafe")
        with patch.object(cmdc, "ROOT", self.root), patch.object(cmdc, "stop") as stop:
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                cmdc.restore("bad")
            stop.assert_not_called()

    def test_bad_backup_name_is_rejected(self):
        """Reject traversal and command-like backup names before filesystem operations."""
        for name in ("../data", "a/b", "a b"):
            with self.assertRaisesRegex(ValueError, "Backup names"):
                cmdc.valid_backup_name(name)

    def test_cleanup_unlinks_directory_symlinks(self):
        """Remove a generated-directory link while retaining the external directory contents."""
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep").write_text("retained")
        link = self.root / "reports"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlinks are not available for this account.")
        cmdc.remove_directory(link)
        self.assertEqual((outside / "keep").read_text(), "retained")

    def test_restore_requires_explicit_confirmation(self):
        """Refuse restore and destruction without --yes before executing any command."""
        for arguments in (["restore", "sample"], ["destroy"], ["reset", "db"]):
            with self.assertRaises(SystemExit) as result:
                cmdc.parser().parse_args(arguments)
            self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
