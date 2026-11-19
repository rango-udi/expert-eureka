"""Repair the original finite-inventory fixture configuration through native Shuup fields."""
from decimal import Decimal
from shuup import configuration
from shuup.core.models import ShopProduct
from shuup.core.utils import context_cache
from shuup.simple_supplier.models import StockCount
from fuzcake_data import reference

POLICY_KEY = 'fuzcake_finite_stock_policy_v1'


def repair_fixture_stock_policy(shop, supplier):
    """Apply once to fixture SKUs without resetting counts, adjustments or orders.

    Native Supplier.stock_managed defaults to False. Recording 25 units does
    not activate orderability checks. A completed repair marker also preserves
    subsequent operator policy edits during ordinary repeated setup.
    """
    if configuration.get(shop, POLICY_KEY):
        return False
    skus = [row['sku'] for row in reference('catalogue')['products']]
    products = list(ShopProduct.objects.filter(shop=shop, product__sku__in=skus, suppliers=supplier).distinct())
    if not products:
        return False
    supplier.stock_managed = True
    supplier.save(update_fields=['stock_managed'])
    for item in products:
        item.backorder_maximum = Decimal('0')
        item.save(update_fields=['backorder_maximum'])
        StockCount.objects.filter(supplier=supplier, product_id=item.product_id).update(stock_managed=True)
        context_cache.bump_cache_for_product(item.product_id)
    configuration.set(shop, POLICY_KEY, True)
    return True

WHOLE_BOTTLE_KEY = 'fuzcake_whole_bottle_policy_v1'


def repair_fixture_quantity_policy(shop, supplier):
    """Set native integer multiples once without changing counts or custom positive multiples.

    Upstream handle_add checks sales-unit fractions explicitly; basket updates
    rely on ShopProduct.purchase_multiple instead. The default zero multiple
    leaves that native check disabled even when the unit forbids fractions.
    """
    if configuration.get(shop, WHOLE_BOTTLE_KEY):
        return False
    skus = [row['sku'] for row in reference('catalogue')['products']]
    products = list(ShopProduct.objects.filter(shop=shop, product__sku__in=skus, suppliers=supplier).distinct())
    if not products:
        return False
    changed = False
    for item in products:
        if not item.product.sales_unit.allow_fractions and item.purchase_multiple == 0:
            item.purchase_multiple = Decimal('1')
            item.save(update_fields=['purchase_multiple'])
            context_cache.bump_cache_for_product(item.product_id)
            changed = True
    configuration.set(shop, WHOLE_BOTTLE_KEY, True)
    return changed
