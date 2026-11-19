"""Check restore archive boundaries before database changes are authorized."""
from pathlib import Path
import importlib.util
import io
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('backup_environment', ROOT / 'scripts/configuration.py')
environment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment)


class BackupGuardTests(unittest.TestCase):
    def setUp(self):
        """Create a disposable backup directory and a placeholder database dump."""
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'backups/sample'
        self.folder.mkdir(parents=True)
        (self.folder / 'database.dump').write_bytes(b'PGDMP')

    def archive(self, name, kind=tarfile.REGTYPE):
        """Write one selected member type for a boundary test."""
        with tarfile.open(self.folder / 'data.tar.gz', 'w:gz') as output:
            member = tarfile.TarInfo(name)
            member.type = kind
            if kind == tarfile.REGTYPE:
                member.size = 1
                output.addfile(member, io.BytesIO(b'x'))
            else:
                member.linkname = '../outside'
                output.addfile(member)

    def test_regular_media_is_accepted(self):
        """Accept a regular media file from a trusted backup."""
        self.archive('media/ticket.pdf')
        environment.validate_backup_archive(self.root, 'sample')

    def test_traversal_and_absolute_members_are_rejected(self):
        """Reject archive names that escape the data directory."""
        for name in ('../outside', '/etc/passwd', 'media/../../outside', 'media\\outside'):
            self.archive(name)
            with self.assertRaisesRegex(ValueError, 'unsafe member'):
                environment.validate_backup_archive(self.root, 'sample')

    def test_links_and_special_members_are_rejected(self):
        """Reject hard links, symbolic links and device members before extraction."""
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE):
            self.archive('media/item', kind)
            with self.assertRaisesRegex(ValueError, 'unsafe member'):
                environment.validate_backup_archive(self.root, 'sample')
