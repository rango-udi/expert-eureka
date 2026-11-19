"""Register the small checkout extension through Oscar's supported app loading."""

from oscar.apps.checkout.apps import CheckoutConfig as OscarCheckoutConfig


class CheckoutConfig(OscarCheckoutConfig):
    name = "storefront.checkout"
