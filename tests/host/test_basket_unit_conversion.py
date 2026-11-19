"""Verify the actual display-update guard before delegating to native rounding."""
import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DomainError(Exception):
    """Stand in for Django ValidationError without requiring the app runtime."""

    def __init__(self, message, code):
        """Retain the code exposed by the real warning adapter."""
        self.code = code
        super().__init__(message)


class NativeBoundary:
    """Record calls crossing into native mutation and warning behavior."""

    def update_display_quantity(self, line, value, **kwargs):
        """Model native delegation, without simulating a browser or database."""
        self.delegated.append((line, value, kwargs))
        return 'native-result'

    def _handle_orderability_error(self, line, error):
        """Record the warning instead of mutating a basket."""
        self.errors.append(error)


class BasketUnitConversionTests(unittest.TestCase):
    """Reject exact fractional items while preserving legitimate unit conversions."""

    def guard(self, ratio='1', fractions=False, product=True):
        """Compile the real subclass with isolated imported dependencies."""
        source=ROOT/'apps/shuup/storefront/basket.py'
        cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef))
        namespace={'Decimal':Decimal,'ValidationError':DomainError,'_':lambda x:x,
                   'FrontBasketUpdateMethods':NativeBoundary,
                   'parse_decimal_string':lambda value:Decimal(value) if value else None}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(source),'exec'),namespace)
        instance=namespace[cls.name]()
        line=SimpleNamespace(product=SimpleNamespace(sales_unit=SimpleNamespace(allow_fractions=fractions)) if product else None,
                             shop_product=SimpleNamespace(unit=SimpleNamespace(display_unit=SimpleNamespace(ratio=Decimal(ratio)))))
        instance.basket=SimpleNamespace(get_basket_line=lambda line_id:line)
        instance.delegated=[]
        instance.errors=[]
        return instance

    def test_fractional_bottles_are_rejected_before_rounding_or_noop(self):
        """Both 1.5 rounding to the existing 2 and 1.4 rounding down must be rejected."""
        for value in ['1.5','1.4','2.0001','NaN','Infinity']:
            guard=self.guard()
            self.assertFalse(guard.update_display_quantity({'line_id':'line'},value))
            self.assertEqual(guard.delegated,[])
            self.assertEqual([e.code for e in guard.errors],['invalid_quantity'])

    def test_whole_quantity_uses_native_validation_and_mutation(self):
        """Valid whole items retain stock/minimum/custom-multiple checks in the superclass."""
        guard=self.guard()
        self.assertEqual(guard.update_display_quantity({'line_id':'line'},'26',key='dq_line'),'native-result')
        self.assertEqual(guard.errors,[])
        self.assertEqual(guard.delegated[0][1: ],('26',{'key':'dq_line'}))

    def test_fractional_display_unit_that_resolves_to_whole_items_is_valid(self):
        """One and a half two-item display units means three internal items."""
        guard=self.guard(ratio='2')
        self.assertEqual(guard.update_display_quantity({'line_id':'line'},'1.5'),'native-result')
        self.assertEqual(guard.errors,[])

    def test_fractional_sales_units_keep_native_behavior(self):
        """Products explicitly allowing fractions remain supported."""
        guard=self.guard(fractions=True)
        self.assertEqual(guard.update_display_quantity({'line_id':'line'},'1.5'),'native-result')
        self.assertEqual(guard.errors,[])

    def test_empty_and_missing_lines_keep_native_handling(self):
        """Do not turn the documented blank/no-line update into a new validation rule."""
        guard=self.guard()
        self.assertEqual(guard.update_display_quantity({'line_id':'line'},''),'native-result')
        self.assertEqual(guard.update_display_quantity(None,'1.5'),'native-result')
        self.assertEqual(guard.errors,[])

    def test_non_product_lines_are_delegated(self):
        """Keep native non-product line behavior intact."""
        guard=self.guard(product=False)
        self.assertEqual(guard.update_display_quantity({'line_id':'line'},'1.5'),'native-result')
