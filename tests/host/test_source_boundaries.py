"""Check source selection with synthetic dependency trees, without running an app."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("source_check", ROOT / "scripts/check_code.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class SourceBoundaryTests(unittest.TestCase):
    """Runtime data and imported dependencies must never become authored-source checks."""

    def test_generated_assets_private_settings_and_links_are_not_selected(self):
        """Reproduce collected static with invalid naming/Unicode beside real source."""
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            root = Path(directory)
            authored = root / "apps/shuup/storefront/owned.js"
            authored.parent.mkdir(parents=True)
            authored.write_text("// Maintained source\n")
            ignored = [root / "apps/shuup/.runtime/data/static/vendor.js",
                       root / "apps/shuup/.venv/site-packages/dependency.py",
                       root / "apps/shuup/reports/output.json",
                       root / "apps/shuup/.env",
                       root / "apps/shuup/node_modules/imported/index.js"]
            for path in ignored:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("l" + "ab caf\u00e9\n", encoding="utf-8")
            link = authored.parent / "linked.js"
            link.symlink_to(ignored[0])
            selected = CHECKER.authored_paths(root)
            self.assertIn(authored, selected)
            self.assertTrue(all(path not in selected for path in ignored + [link]))

    def test_owned_source_is_still_validated(self):
        """Excluding generated files must not hide a violation in maintained code."""
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            root = Path(directory)
            path = root / "owned.js"
            path.write_text("// caf\u00e9\n", encoding="utf-8")
            with patch.object(CHECKER, "ROOT", root), patch.object(CHECKER, "authored_paths", return_value=[path]):
                with self.assertRaisesRegex(SystemExit, "keep source text in English"):
                    CHECKER.main()

    def test_public_docs_do_not_reference_internal_governance(self):
        """Check complete public/private document fixtures through the documentation reader."""
        spec = importlib.util.spec_from_file_location("docs_check", ROOT / "scripts/check_docs.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            root = Path(directory)
            (root / "documents").mkdir()
            (root / ".local").mkdir()
            (root / "documents/NAVIGATION.md").write_text("[NAVIGATION](NAVIGATION.md)\n\nIndex\n\n[NAVIGATION](NAVIGATION.md)\n")
            for name in ("PRINCIPLES.md", "INTERFACE_DESIGN.md", "MOCK_DATA.md"):
                (root / ".local" / name).write_text("[NAVIGATION](../documents/NAVIGATION.md)\n\nInternal .local records\n\n[NAVIGATION](../documents/NAVIGATION.md)\n")
            (root / "README.md").write_text("[NAVIGATION](documents/NAVIGATION.md)\n\nSee .local/PRINCIPLES.md\n\n[NAVIGATION](documents/NAVIGATION.md)\n")
            _, errors = checker.check(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("internal project metadata", errors[0])
