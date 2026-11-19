"""Check one-time stock policy repair without importing the application runtime."""
import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]


class StockPolicyTests(unittest.TestCase):
    """Use isolated ORM doubles; native supplier behavior has separate integration tests."""

    def fixture(self, completed=False, empty=False):
        """Load the real repair function with isolated configuration and ORM boundaries."""
        source = ROOT / 'apps/shuup/storefront/stock_policy.py'
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
        products = [] if empty else [SimpleNamespace(product_id=1, backorder_maximum=None, save=Mock())]
        counts = SimpleNamespace(stock_managed=False, logical_count=Decimal('19'), physical_count=Decimal('23'))
        count_query = Mock()
        count_query.update.side_effect = lambda **values: setattr(counts, 'stock_managed', values['stock_managed'])
        configuration = Mock()
        configuration.get.return_value = completed
        product_manager = Mock()
        product_manager.filter.return_value.distinct.return_value = products
        stock_manager = Mock()
        stock_manager.filter.return_value = count_query
        cache = Mock()
        namespace = {'Decimal': Decimal, 'configuration': configuration, 'POLICY_KEY': 'fuzcake_finite_stock_policy_v1',
                     'ShopProduct': SimpleNamespace(objects=product_manager),
                     'StockCount': SimpleNamespace(objects=stock_manager), 'context_cache': cache,
                     'reference': lambda name: {'products': [{'sku': 'fuzcake-rose-nocturne'}]}}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        supplier = SimpleNamespace(stock_managed=False, save=Mock())
        return SimpleNamespace(run=namespace[function.name], shop=object(), supplier=supplier,
                               products=products, counts=counts, config=configuration,
                               products_manager=product_manager, stocks_manager=stock_manager, cache=cache)

    def test_original_supplier_default_is_repaired_without_restoring_stock(self):
        """Enable native finite inventory while retaining the actual counts."""
        f = self.fixture()
        self.assertTrue(f.run(f.shop, f.supplier))
        self.assertTrue(f.supplier.stock_managed)
        self.assertTrue(f.counts.stock_managed)
        self.assertEqual(f.products[0].backorder_maximum, Decimal('0'))
        self.assertEqual((f.counts.logical_count, f.counts.physical_count), (Decimal('19'), Decimal('23')))
        f.products_manager.filter.assert_called_once_with(shop=f.shop,
            product__sku__in=['fuzcake-rose-nocturne'], suppliers=f.supplier)
        f.stocks_manager.filter.assert_called_once_with(supplier=f.supplier, product_id=1)
        f.config.set.assert_called_once_with(f.shop, 'fuzcake_finite_stock_policy_v1', True)
        f.cache.bump_cache_for_product.assert_called_once_with(1)

    def test_completed_marker_preserves_later_operator_policy(self):
        """Repeated setup does not reapply or silently reset policy edits."""
        f = self.fixture(completed=True)
        self.assertFalse(f.run(f.shop, f.supplier))
        self.assertFalse(f.supplier.stock_managed)
        f.products_manager.filter.assert_not_called()
        f.supplier.save.assert_not_called()
        f.config.set.assert_not_called()

    def test_empty_catalogue_does_not_mark_the_repair_complete(self):
        """Keep a later real initialization eligible instead of marking an empty store."""
        f = self.fixture(empty=True)
        self.assertFalse(f.run(f.shop, f.supplier))
        f.config.set.assert_not_called()
        f.supplier.save.assert_not_called()

    def quantity_fixture(self, multiple=0, fractions=False, completed=False, empty=False):
        """Load the actual one-time multiple repair with isolated native model boundaries."""
        source=ROOT/'apps/shuup/storefront/stock_policy.py'
        function=next(node for node in ast.parse(source.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='repair_fixture_quantity_policy')
        item=SimpleNamespace(product=SimpleNamespace(sales_unit=SimpleNamespace(allow_fractions=fractions)),
                             product_id=1,purchase_multiple=Decimal(multiple),save=Mock())
        config=Mock();config.get.return_value=completed
        manager=Mock();manager.filter.return_value.distinct.return_value=[] if empty else [item]
        cache=Mock()
        namespace={'Decimal':Decimal,'configuration':config,'WHOLE_BOTTLE_KEY':'fuzcake_whole_bottle_policy_v1',
                   'ShopProduct':SimpleNamespace(objects=manager),'context_cache':cache,
                   'reference':lambda name:{'products':[{'sku':'fuzcake-rose-nocturne'}]}}
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
        return SimpleNamespace(run=namespace[function.name],item=item,config=config,manager=manager,cache=cache)

    def test_default_multiple_is_repaired_through_native_field(self):
        """A zero native multiple becomes one without any stock/count/transaction writes."""
        f=self.quantity_fixture()
        self.assertTrue(f.run('shop','supplier'))
        self.assertEqual(f.item.purchase_multiple,Decimal('1'))
        f.item.save.assert_called_once_with(update_fields=['purchase_multiple'])
        f.config.set.assert_called_once_with('shop','fuzcake_whole_bottle_policy_v1',True)

    def test_quantity_repair_preserves_custom_multiples_and_fractional_units(self):
        """Existing positive multiples and intentionally fractional units retain their policy."""
        for multiple,fractions in [(3,False),(0,True)]:
            f=self.quantity_fixture(multiple=multiple,fractions=fractions)
            self.assertFalse(f.run('shop','supplier'))
            self.assertEqual(f.item.purchase_multiple,Decimal(multiple))
            f.item.save.assert_not_called()

    def test_quantity_repair_marker_and_empty_store_are_safe(self):
        """An applied marker prevents repeated changes; an empty store gets no marker."""
        f=self.quantity_fixture(completed=True)
        self.assertFalse(f.run('shop','supplier'))
        f.manager.filter.assert_not_called()
        f=self.quantity_fixture(empty=True)
        self.assertFalse(f.run('shop','supplier'))
        f.config.set.assert_not_called()
