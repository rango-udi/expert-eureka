"""Validate shared reference boundaries inside the selected app tools container."""
import unittest
from fuzcake_data import asset_path, reference, validate


class SharedDataTests(unittest.TestCase):
    def test_profile_and_all_original_images_are_valid(self):
        """Check shared references and original hashes before a database import."""
        validate("wowy")

    def test_unknown_documents_and_path_traversal_are_rejected(self):
        """Reference helpers must not become arbitrary filesystem readers."""
        with self.assertRaises(ValueError):
            reference("../.env")
        with self.assertRaises(ValueError):
            asset_path("../../apps/wowy/.env")

    def test_callers_cannot_mutate_cached_records(self):
        """An adapter's local mapping must not change another consumer's source data."""
        original = reference("store")["name"]
        changed = reference("store")
        changed["name"] = "Temporary local edit"
        self.assertEqual(reference("store")["name"], original)
