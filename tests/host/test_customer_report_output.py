"""Exercise report publication under real filesystem writes and injected OS locks."""
import errno
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('report_output', ROOT / 'apps/shuup/scripts/customer_report_output.py')
OUTPUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OUTPUT)


class ReportOutputTests(unittest.TestCase):
    """Never truncate the open workbook or suppress a disk/permission failure."""

    def test_atomic_success_and_stale_owner_file(self):
        """The complete new file replaces the old one despite a stale owner marker."""
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'customer_test_cases.xlsx'
            target.write_bytes(b'old reviewed workbook')
            target.with_name('~$' + target.name).touch()
            def render(path):
                """Observe the old destination while rendering the new file."""
                self.assertEqual(target.read_bytes(), b'old reviewed workbook')
                path.write_bytes(b'new complete workbook')
            saved, warnings = OUTPUT.publish_workbook(target, render)
            self.assertEqual(saved, target)
            self.assertEqual(target.read_bytes(), b'new complete workbook')
            self.assertEqual(len(warnings), 1)
            self.assertFalse(list(Path(folder).glob('.*.xlsx')))

    def test_locked_target_saves_an_alternative_and_reports_its_actual_path(self):
        """Simulate Windows sharing errors and Docker's translated busy/access errors."""
        for code in (errno.EACCES, errno.EBUSY, errno.ETXTBSY):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / 'customer_test_cases.xlsx'
                target.write_bytes(b'open reviewed workbook')
                replace = OUTPUT.os.replace
                def locked(source, destination):
                    """Reject only the destination held by Excel."""
                    if destination == target:
                        raise OSError(code, 'simulated sharing lock')
                    return replace(source, destination)
                with patch.object(OUTPUT.os, 'replace', side_effect=locked):
                    saved, warnings = OUTPUT.publish_workbook(target, lambda path: path.write_bytes(b'new report'))
                self.assertNotEqual(saved, target)
                self.assertEqual(saved.parent, target.parent)
                self.assertEqual(saved.read_bytes(), b'new report')
                self.assertEqual(target.read_bytes(), b'open reviewed workbook')
                self.assertIn(str(saved), warnings[0])

    def test_full_disk_during_render_preserves_existing_workbook(self):
        """A partial rendering is removed while the previous workbook stays intact."""
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'customer_test_cases.xlsx'
            target.write_bytes(b'old')
            def incomplete(path):
                """Leave partial bytes before the simulated disk failure."""
                path.write_bytes(b'partial')
                raise OSError(errno.ENOSPC, 'disk full')
            with self.assertRaisesRegex(OUTPUT.ReportOutputError, 'free disk space'):
                OUTPUT.publish_workbook(target, incomplete)
            self.assertEqual(target.read_bytes(), b'old')
            self.assertEqual(list(Path(folder).iterdir()), [target])

    def test_unpublishable_complete_report_is_retained_for_recovery(self):
        """An inaccessible folder does not silently pass or delete completed data."""
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'customer_test_cases.xlsx'
            with patch.object(OUTPUT.os, 'replace', side_effect=PermissionError(errno.EACCES, 'denied')):
                with self.assertRaisesRegex(OUTPUT.ReportOutputError, 'Completed workbook retained at:'):
                    OUTPUT.publish_workbook(target, lambda path: path.write_bytes(b'complete'))
            retained = list(Path(folder).glob('.*.xlsx'))
            self.assertEqual(len(retained), 1)
            self.assertEqual(retained[0].read_bytes(), b'complete')

    def test_non_lock_publication_error_is_not_retried_as_a_lock(self):
        """Disk failures remain explicit errors and keep a completed recovery file."""
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(OUTPUT.os, 'replace', side_effect=OSError(errno.ENOSPC, 'full')) as replace:
                with self.assertRaisesRegex(OUTPUT.ReportOutputError, 'free disk space'):
                    OUTPUT.publish_workbook(Path(folder) / 'report.xlsx', lambda path: path.write_bytes(b'complete'))
                self.assertEqual(replace.call_count, 1)

    def test_destination_creation_error_has_actionable_message(self):
        """A report directory blocked by a file is reported before rendering."""
        with tempfile.TemporaryDirectory() as folder:
            blocked = Path(folder) / 'blocked'
            blocked.write_text('existing file')
            with self.assertRaisesRegex(OUTPUT.ReportOutputError, 'write access and free disk space'):
                OUTPUT.publish_workbook(blocked / 'report.xlsx', lambda path: self.fail('must not render'))
