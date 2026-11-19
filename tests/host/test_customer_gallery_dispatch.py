"""Record Browser keyword orchestration; never import Robot or run a browser."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class GalleryDispatchTests(unittest.TestCase):
    """Keep unrelated photograph checks out of single-input quantity probes."""

    def setUp(self):
        """Compile only the two UI orchestration methods against keyword recorders."""
        tree = ast.parse((ROOT / 'apps/shuup/tests/robot/CustomerJourney.py').read_text())
        source = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        methods = [node for node in source.body if isinstance(node, ast.FunctionDef)
                   and node.name in ('_open_product', '_inspect_product_gallery')]
        namespace = {'json': json}
        for method in methods:
            module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
            exec(compile(module, '<isolated-gallery-dispatch>', 'exec'), namespace)
        self.methods = namespace
        self.calls = []
        self.spy = type('KeywordRecorder', (), {})()
        self.spy._at = lambda *args: None
        self.spy._capture = lambda *args: None
        self.spy.catalogue = {'sku': {'name': 'Test Fragrance', 'description': 'Test description',
                                     'size': '50 ml', 'price': '89.00'}}
        self.spy._search = self.record_search
        self.spy._count = self.count
        self.spy._kw = self.record_keyword
        self.spy._assert_money = self.record_money
        self.spy._inspect_product_gallery = self.record_gallery

    def record_search(self, value):
        """Record a search without opening any page."""
        self.calls.append(('search', value))

    def count(self, selector):
        """Provide one synthetic match for dispatch verification only."""
        return 1

    def record_keyword(self, name, *arguments):
        """Capture actions instead of executing Playwright."""
        self.calls.append((name, *arguments))

    def record_money(self, selector, value):
        """Record a requested price assertion without claiming a displayed value."""
        self.calls.append(('price', selector, value))

    def record_gallery(self):
        """Identify the optional branch without running its photograph check."""
        self.calls.append(('gallery',))

    def test_quantity_entry_does_not_open_the_gallery(self):
        """Normal product opening must reach price and quantity without a zoom prerequisite."""
        self.methods['_open_product'](self.spy, 'sku')
        self.assertNotIn(('gallery',), self.calls)
        self.assertTrue(any(row[0] == 'price' for row in self.calls))
        self.assertTrue(any('quantity' in str(row) for row in self.calls))

    def test_detail_journey_keeps_gallery_and_image_load_checks(self):
        """The integrated journey still checks the photograph itself and closes it."""
        self.methods['_open_product'](self.spy, 'sku', inspect_gallery=True)
        self.assertIn(('gallery',), self.calls)
        self.calls.clear()
        self.spy._until = self.observe_probe
        self.spy._read = self.read_loaded_image
        self.methods['_inspect_product_gallery'](self.spy)
        image = 'css=.sl-wrapper .sl-image img:visible'
        self.assertIn(('Wait For Elements State', image, 'visible'), self.calls)
        self.assertIn(('Wait For Elements State', image, 'hidden'), self.calls)
        self.assertTrue(any(row[0] == 'read' and 'naturalWidth' in row[2] for row in self.calls))

    def observe_probe(self, probe, description):
        """Evaluate a synthetic probe once; this is not polling or UI execution."""
        self.assertTrue(probe())

    def read_loaded_image(self, selector, expression):
        """Record the requested load observation without reading a real DOM."""
        self.calls.append(('read', selector, expression))
        return True
