"""Register the local storefront theme without modifying upstream Shuup."""
from shuup.apps import AppConfig


class StorefrontConfig(AppConfig):
    name = "storefront"
    verbose_name = "fuzcake Fragrance House"
    # Shuup scans app defaults; project settings import upstream values and must stay separate.
    default_settings_module = ".default_settings"
    provides = {"xtheme": "storefront.theme:FuzcakeTheme"}
