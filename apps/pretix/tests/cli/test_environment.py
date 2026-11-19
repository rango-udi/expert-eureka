"""Verify project behavior with isolated inputs and no real Docker mutations."""
import importlib.util
from pathlib import Path
import tempfile
import shutil
import unittest
import subprocess
import sys
import os
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("environment", ROOT / "scripts/configuration.py")
environment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class EnvironmentTests(unittest.TestCase):
    def test_resource_defaults_preserve_an_explicit_existing_worker_count(self):
        """Add lighter defaults without silently changing an operator's chosen concurrency."""
        (self.root / ".env").write_text("WEB_WORKERS=3\n")
        environment.ensure(self.root)
        values = environment.parse((self.root / ".env").read_text())
        self.assertEqual(values["WEB_WORKERS"], "3")
        self.assertEqual(values["TASK_CONCURRENCY"], "1")
        self.assertEqual(values["PERIODIC_INTERVAL_SECONDS"], "300")
        self.assertEqual(values["PG_SHARED_BUFFERS"], "64MB")

    def test_invalid_resource_settings_fail_before_creating_configuration(self):
        """Reject zero worker count before writing a misleading runnable configuration."""
        template = self.root / ".env.template"
        template.write_text(template.read_text().replace("WEB_WORKERS=1", "WEB_WORKERS=0"))
        with self.assertRaisesRegex(ValueError, "WEB_WORKERS"):
            environment.ensure(self.root)
        self.assertFalse((self.root / ".env").exists())
    def test_windows_configuration_succeeds_without_posix_chmod(self):
        """Create and reuse secrets on a simulated Windows mount where chmod is unavailable."""
        with patch.dict(os.environ, {"CMDC_HOST_PLATFORM": "windows"}), patch.object(
            Path, "chmod", side_effect=OSError("POSIX permissions are unavailable on this host mount")
        ):
            environment.ensure(self.root)
            environment.ensure(self.root)
        values = environment.parse((self.root / ".env").read_text())
        self.assertTrue(all(values[key] for key in environment.SECRET_KEYS))
    def test_nonnumeric_port_identifies_the_setting_and_recovery_command(self):
        """Explain a malformed port using its key and a refresh command, without int-conversion details."""
        with self.assertRaisesRegex(ValueError, "PRETIX_PUBLIC_PORT.*cmdc urls"):
            environment.validate_public_port("not-a-port", "PRETIX_PUBLIC_PORT")
    def test_cli_reports_bad_configuration_without_a_traceback(self):
        """Show the invalid setting and recovery command instead of a Python traceback."""
        (self.root / ".env").write_text("PUBLIC_PORT_RANGE=8000-9000\n")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/configuration.py"), "ensure", "--root", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("PUBLIC_PORT_RANGE", result.stderr)
        self.assertIn("cmdc env init", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
    def test_credential_aliases_keep_saved_values_and_create_private_backup(self):
        """Normalize prior prefixed keys while preserving credentials and the original file."""
        original = "OLD_ADMIN_EMAIL=admin@example.test\nOLD_ADMIN_PASSWORD=keep-admin\nOLD_STAFF_PASSWORD=keep-staff\nCUSTOM=keep\n"
        (self.root / ".env").write_text(original)
        environment.ensure(self.root)
        values = environment.parse((self.root / ".env").read_text())
        self.assertEqual(values["ADMIN_PASSWORD"], "keep-admin")
        self.assertEqual(values["STAFF_PASSWORD"], "keep-staff")
        self.assertEqual(values["CUSTOM"], "keep")
        self.assertNotIn("OLD_ADMIN_PASSWORD", values)
        self.assertEqual((self.root / ".env.credentials-backup").read_text(), original)
        environment.ensure(self.root)
        self.assertEqual(environment.parse((self.root / ".env").read_text()), values)

    def test_conflicting_credential_aliases_leave_saved_configuration_untouched(self):
        """Reject ambiguous passwords before writing a backup or changing the configuration."""
        original = "ADMIN_PASSWORD=one\nOLD_ADMIN_PASSWORD=two\n"
        (self.root / ".env").write_text(original)
        with self.assertRaisesRegex(ValueError, "Conflicting saved credentials"):
            environment.ensure(self.root)
        self.assertEqual((self.root / ".env").read_text(), original)
        self.assertFalse((self.root / ".env.credentials-backup").exists())

    def test_invalid_alias_configuration_does_not_write_migration_backup(self):
        """Validate resources before creating any credential migration files."""
        original = "OLD_ADMIN_PASSWORD=keep\nWEB_WORKERS=0\n"
        (self.root / ".env").write_text(original)
        with self.assertRaisesRegex(ValueError, "WEB_WORKERS"):
            environment.ensure(self.root)
        self.assertEqual((self.root / ".env").read_text(), original)
        self.assertFalse((self.root / ".env.credentials-backup").exists())

    def setUp(self):
        """Create an isolated project copy and test fixtures; return None without changing real Docker resources."""
        temporary_parent = None if os.environ.get("CMDC_HOST_PLATFORM") == "windows" else ROOT
        self.temp = tempfile.TemporaryDirectory(prefix="env-test-", dir=temporary_parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / ".env.template", self.root)
        shutil.copytree(ROOT / "config", self.root / "config")

    def test_secrets_are_distinct_and_persist_across_runs(self):
        """Verify secrets are distinct and persist across runs. Return None or raise AssertionError on a regression."""
        environment.ensure(self.root)
        first = environment.parse((self.root / ".env").read_text())
        secrets = [first[key] for key in environment.SECRET_KEYS]
        self.assertEqual(len(set(secrets)), 3)
        self.assertTrue(all(len(secret) == 48 for secret in secrets))
        environment.ensure(self.root)
        self.assertEqual(first, environment.parse((self.root / ".env").read_text()))
        if os.environ.get("CMDC_HOST_PLATFORM") != "windows":
            self.assertEqual((self.root / ".env").stat().st_mode & 0o777, 0o600)

    def test_preexisting_passwords_and_unknown_keys_are_preserved(self):
        """Verify preexisting passwords and unknown keys are preserved. Return None or raise AssertionError on a regression."""
        (self.root / ".env").write_text("POSTGRES_PASSWORD='keep-$-literal'\nCUSTOM=keep\n")
        environment.ensure(self.root)
        values = environment.parse((self.root / ".env").read_text())
        self.assertEqual(values["POSTGRES_PASSWORD"], "keep-$-literal")
        self.assertEqual(values["CUSTOM"], "keep")

    def test_common_port_range_is_rejected_without_creating_env(self):
        """Verify common port range is rejected without creating env. Return None or raise AssertionError on a regression."""
        template = self.root / ".env.template"
        template.write_text(template.read_text().replace("49152-65535", "8000-9000"))
        with self.assertRaises(ValueError):
            environment.ensure(self.root)
        self.assertFalse((self.root / ".env").exists())

    def test_duplicate_keys_are_rejected(self):
        """Verify duplicate keys are rejected. Return None or raise AssertionError on a regression."""
        with self.assertRaises(ValueError):
            environment.parse("CUSTOM=one\nCUSTOM=two\n")

    def test_generated_endpoint_document_links_to_navigation_at_both_ends(self):
        """Verify generated endpoint document links to navigation at both ends. Return None or raise AssertionError on a regression."""
        environment.ensure(self.root)
        environment.update(self.root / ".env", {"PRETIX_PUBLIC_PORT": "55123", "MAILPIT_PUBLIC_PORT": "55124"})
        environment.endpoints(self.root)
        text = (self.root / ".runtime/ENDPOINTS.md").read_text().strip()
        self.assertTrue(text.startswith("[NAVIGATION](../../../documents/NAVIGATION.md)"))
        self.assertTrue(text.endswith("[NAVIGATION](../../../documents/NAVIGATION.md)"))
        self.assertIn("http://pretix.localhost:55123/control/", text)
        environment.update(self.root / ".env", dict.fromkeys(environment.PORT_KEYS, ""))
        environment.endpoints(self.root)
        self.assertFalse((self.root / ".runtime/ENDPOINTS.md").exists())
