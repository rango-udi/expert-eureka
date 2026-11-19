"""Verify native rejection observations with recorded UI states, not a live store."""
import ast
from decimal import Decimal
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


class QuantityRejectionTests(unittest.TestCase):
    """Keep an above-stock acceptance or a generic server failure from passing."""

    def methods(self):
        """Compile only quantity observation helpers without importing Browser."""
        tree = ast.parse((ROOT / 'apps/shuup/tests/robot/CustomerJourney.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        namespace = {'Decimal': Decimal, 're': re}
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name in ('_quantity','_quantity_error'):
                module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
                exec(compile(module, '<quantity-observation>', 'exec'), namespace)
        return namespace

    def test_visible_stock_message_does_not_require_transient_parent_class(self):
        """Observe a visible native message after the overlay's error class changes."""
        observed = []
        def snapshot(selector, script):
            """Record one read-only snapshot rather than racing separate DOM queries."""
            observed.append(script)
            return ['Insufficient quantity in stock.']
        spy = SimpleNamespace(_read=snapshot)
        self.assertTrue(self.methods()['_quantity_error'](spy))
        self.assertIn('.cover-wrap #error-msg', observed[0])
        self.assertNotIn('.cover-wrap.error', observed[0])
        self.assertIn('getBoundingClientRect', observed[0])

    def test_generic_server_error_is_not_a_quantity_rejection(self):
        """An unrelated failure cannot satisfy the domain-specific rejection oracle."""
        spy = SimpleNamespace(_read=lambda *args:['Internal server error'])
        self.assertFalse(self.methods()['_quantity_error'](spy))

    def test_all_visible_native_messages_are_examined(self):
        """A later stock message must not be hidden by the first generic message."""
        spy = SimpleNamespace(_read=lambda *args:['An error occurred','Insufficient stock'])
        self.assertTrue(self.methods()['_quantity_error'](spy))

    def quantity_spy(self, accepted_count):
        """Create deterministic observations for the rejected-quantity branch."""
        counts = iter([0,accepted_count,accepted_count])
        def keyword(name, *arguments):
            """Supply native min/step and an enabled Add button to the observer."""
            return '1' if name=='Get Attribute' else False if name=='Get Property' else None
        def until(probe, description):
            """Evaluate once and model an expired wait when no rejection is visible."""
            if not probe():
                raise AssertionError('Timed out waiting for ' + description)
        return SimpleNamespace(model={'quantity_product':'sku','quantity_model':{'fields':{'quantity':{'min':'1','step':'1'}}}},
                               _login=lambda *args:None,_kw=keyword,_open_product=lambda *args:None,
                               _cart_count=lambda:next(counts),_read=lambda *args:True,_until=until,_quantity_error=lambda:False)

    def test_accepted_above_stock_quantity_fails_explicitly(self):
        """A basket containing 26 items must remain a failure, not become a timeout or PASS."""
        spy=self.quantity_spy(26)
        case={'value':'26','expected':'rejected','inputs':{'account':{'username':'oliver.bennett','password':'Oliver!4826Maple'}}}
        with self.assertRaisesRegex(AssertionError,'basket now contains 26'):
            self.methods()['_quantity'](spy,case)

    def test_missing_rejection_fails_with_observed_state(self):
        """An empty basket alone does not prove rejection; retain a diagnostic failure."""
        spy=self.quantity_spy(0)
        case={'value':'26','expected':'rejected','inputs':{'account':{'username':'oliver.bennett','password':'Oliver!4826Maple'}}}
        with self.assertRaisesRegex(AssertionError,'basket count=0; add button disabled=False'):
            self.methods()['_quantity'](spy,case)

    def test_native_basket_warning_and_multiple_messages_are_supported(self):
        """Warning severity and purchase-multiple errors are genuine native domain signals."""
        scripts=[]
        def read(selector, script):
            """Return the native warning while retaining the queried DOM selector."""
            scripts.append(script)
            return ['Warning! Rose Nocturne: The product can only be ordered in multiples of 1, for example 1 or 2.']
        self.assertTrue(self.methods()['_quantity_error'](SimpleNamespace(_read=read)))
        self.assertIn('.alert-warning',scripts[0])

    def test_generic_warning_does_not_satisfy_quantity_oracle(self):
        """Adding warning severity must not turn unrelated notices into rejection evidence."""
        self.assertFalse(self.methods()['_quantity_error'](SimpleNamespace(_read=lambda *args:['Warning! Please sign in again.'])))
