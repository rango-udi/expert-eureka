"""Protect YAML parsing and semantic model identity before generation."""
import json
from pathlib import Path
import tempfile
import unittest
from test_design.specification import load_specification, semantic_hash
from test_design.engine import design


class SpecificationTests(unittest.TestCase):
    def load_text(self, text, suffix='.yaml'):
        """Load a disposable specification from its declared format."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ('model' + suffix)
            path.write_text(text, encoding='utf-8')
            return load_specification(path)

    def test_quoted_ui_values_and_booleans_keep_types(self):
        """Preserve exact decimal text, blanks and Boolean partition flags."""
        data = self.load_text("value: '5.00'\nempty: ''\nvalid: true\n")
        self.assertEqual(data, {'value': '5.00', 'empty': '', 'valid': True})

    def test_duplicate_keys_and_unsafe_tags_fail(self):
        """Reject ambiguous or unsupported YAML and JSON structures."""
        for text in ('a: 1\na: 2', 'x: !!python/object:builtins.object {}', 'x: 2026-11-19', 'x: &a [*a]'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load_text(text)
        with self.assertRaises(ValueError):
            self.load_text('{"a":1,"a":2}', '.json')

    def test_yaml_json_equivalence_and_semantic_hash(self):
        """Formatting changes preserve identity; input changes do not."""
        a = self.load_text("# comment\na: '25.00'\nb: true\n")
        b = self.load_text(json.dumps({'b': True, 'a': '25.00'}), '.json')
        self.assertEqual(semantic_hash(a), semantic_hash(b))
        self.assertNotEqual(semantic_hash(a), semantic_hash(dict(a, a='25.01')))

    def test_unquoted_ui_nominal_fails_domain_validation(self):
        """A numeric YAML scalar must not silently become UI text."""
        model = {'schema_version': 1, 'fields': {'amount': {'nominal': 25}}}
        with self.assertRaisesRegex(ValueError, 'strings'):
            design(model)
