"""Validate exact unit quantities before native display conversion can round them."""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from shuup.front.basket.update_methods import BasketUpdateMethods as FrontBasketUpdateMethods
from shuup.utils.numbers import parse_decimal_string


class WholeUnitBasketUpdateMethods(FrontBasketUpdateMethods):
    """Retain native warning, stock and mutation behavior for valid display quantities."""

    def update_display_quantity(self, line, value, **kwargs):
        """Reject fractional internal units before from_display rounds to unit precision.

        For example, 1.5 bottles rounds to 2 at zero decimal precision. If the
        line already holds 2, native _update_quantity returns without validation.
        Validate the exact ratio conversion first; fractional display quantities
        that convert to whole internal items remain valid.
        """
        quantity = parse_decimal_string(value)
        if line and quantity is not None:
            basket_line = self.basket.get_basket_line(line['line_id'])
            if basket_line and basket_line.product and not basket_line.product.sales_unit.allow_fractions:
                exact = Decimal(quantity) * basket_line.shop_product.unit.display_unit.ratio
                if not exact.is_finite() or exact % 1:
                    self._handle_orderability_error(line, ValidationError(
                        _('Quantity must resolve to a whole number of items for this product.'),
                        code='invalid_quantity'))
                    return False
        return super().update_display_quantity(line, value, **kwargs)
