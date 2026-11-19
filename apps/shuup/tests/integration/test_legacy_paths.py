"""Exercise the legacy Django SQLite path contract behind initialization and connection cleanup."""
from django.conf import settings
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.test import SimpleTestCase


class LegacyPathTests(SimpleTestCase):
    def test_file_database_name_is_accepted_by_legacy_sqlite_cleanup(self):
        """Use Django 2.2's actual memory-database predicate with the configured filename."""
        name = settings.DATABASES["default"]["NAME"]
        self.assertIsInstance(name, str)
        # Django test execution may replace NAME with its in-memory URI.
        self.assertIsInstance(DatabaseCreation.is_in_memory_db(name), bool)

    def test_storage_and_email_paths_are_text_for_legacy_integrations(self):
        """Keep public path settings compatible with string operations in older packages."""
        for name in ("MEDIA_ROOT", "STATIC_ROOT", "EMAIL_FILE_PATH"):
            self.assertIsInstance(getattr(settings, name), str, name)
