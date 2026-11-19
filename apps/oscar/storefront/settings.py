"""Run Oscar with SQLite, local search, local email and sequential web requests."""

from pathlib import Path
import os
import sys
import tempfile
import atexit
import shutil
from oscar.defaults import *

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / ".runtime" / "data"
if os.environ.get("CMDC_TESTING") == "1" or sys.argv[1:2] == ["test"]:
    temporary_parent = BASE_DIR / ".runtime/tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR = Path(tempfile.mkdtemp(prefix="oscar-test-", dir=temporary_parent))
    atexit.register(shutil.rmtree, DATA_DIR, ignore_errors=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]", "testserver", "oscar"]
ROOT_URLCONF = "storefront.urls"
WSGI_APPLICATION = "storefront.wsgi.application"
SITE_ID = 1
USE_TZ = True
TIME_ZONE = os.environ.get("TIMEZONE", "Asia/Bangkok")
LANGUAGE_CODE = "en-gb"
LANGUAGES = [("en-gb", "English")]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
        "ATOMIC_REQUESTS": True,
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "OPTIONS": {"MAX_ENTRIES": 128},
    }
}
STATIC_URL = "/static/"
STATIC_ROOT = DATA_DIR / "static"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = DATA_DIR / "mail"
DEFAULT_FROM_EMAIL = "shop@example.test"
OSCAR_FROM_EMAIL = DEFAULT_FROM_EMAIL
AUTHENTICATION_BACKENDS = [
    "oscar.apps.customer.auth_backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    }
]
LOGIN_REDIRECT_URL = "/"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "oscar.config.Shop",
    "oscar.apps.analytics.apps.AnalyticsConfig",
    "storefront.checkout.apps.CheckoutConfig",
    "oscar.apps.address.apps.AddressConfig",
    "oscar.apps.shipping.apps.ShippingConfig",
    "oscar.apps.catalogue.apps.CatalogueConfig",
    "oscar.apps.catalogue.reviews.apps.CatalogueReviewsConfig",
    "oscar.apps.communication.apps.CommunicationConfig",
    "oscar.apps.partner.apps.PartnerConfig",
    "oscar.apps.basket.apps.BasketConfig",
    "oscar.apps.payment.apps.PaymentConfig",
    "oscar.apps.offer.apps.OfferConfig",
    "oscar.apps.order.apps.OrderConfig",
    "oscar.apps.customer.apps.CustomerConfig",
    "oscar.apps.search.apps.SearchConfig",
    "oscar.apps.voucher.apps.VoucherConfig",
    "oscar.apps.wishlists.apps.WishlistsConfig",
    "oscar.apps.dashboard.apps.DashboardConfig",
    "oscar.apps.dashboard.reports.apps.ReportsDashboardConfig",
    "oscar.apps.dashboard.users.apps.UsersDashboardConfig",
    "oscar.apps.dashboard.orders.apps.OrdersDashboardConfig",
    "oscar.apps.dashboard.catalogue.apps.CatalogueDashboardConfig",
    "oscar.apps.dashboard.offers.apps.OffersDashboardConfig",
    "oscar.apps.dashboard.partners.apps.PartnersDashboardConfig",
    "oscar.apps.dashboard.pages.apps.PagesDashboardConfig",
    "oscar.apps.dashboard.ranges.apps.RangesDashboardConfig",
    "oscar.apps.dashboard.reviews.apps.ReviewsDashboardConfig",
    "oscar.apps.dashboard.vouchers.apps.VouchersDashboardConfig",
    "oscar.apps.dashboard.communications.apps.CommunicationsDashboardConfig",
    "oscar.apps.dashboard.shipping.apps.ShippingDashboardConfig",
    "widget_tweaks",
    "haystack",
    "treebeard",
    "sorl.thumbnail",
    "django_tables2",
    "storefront",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "oscar.apps.basket.middleware.BasketMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "storefront" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.contrib.messages.context_processors.messages",
                "oscar.apps.search.context_processors.search_form",
                "oscar.apps.communication.notifications.context_processors.notifications",
                "oscar.apps.checkout.context_processors.checkout",
                "oscar.core.context_processors.metadata",
            ]
        },
    }
]
HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.whoosh_backend.WhooshEngine",
        "PATH": DATA_DIR / "search",
    }
}
# Whoosh supports field facets but not Haystack's query-based price buckets.
OSCAR_SEARCH_FACETS = {"fields": OSCAR_SEARCH_FACETS["fields"], "queries": {}}
OSCAR_SHOP_NAME = "fuzcake"
OSCAR_SHOP_TAGLINE = "A little scent. A lasting feeling."
OSCAR_DEFAULT_CURRENCY = "USD"
OSCAR_ALLOW_ANON_CHECKOUT = True
OSCAR_MAX_BASKET_QUANTITY_THRESHOLD = 10
OSCAR_INITIAL_ORDER_STATUS = "Pending"
OSCAR_INITIAL_LINE_STATUS = "Pending"
OSCAR_ORDER_STATUS_PIPELINE = {
    "Pending": ("Being processed", "Cancelled"),
    "Being processed": ("Complete", "Cancelled"),
    "Complete": (),
    "Cancelled": (),
}
OSCAR_ORDER_STATUS_CASCADE = {
    "Being processed": "Being processed",
    "Cancelled": "Cancelled",
    "Complete": "Shipped",
}
THUMBNAIL_KVSTORE = "sorl.thumbnail.kvstores.cached_db_kvstore.KVStore"

# Shared fixtures remain outside application secrets and runtime data.
FUZCAKE_DATA_ROOT = Path("/fuzcake-data")
sys.path.insert(0, str(FUZCAKE_DATA_ROOT))
STATICFILES_DIRS = [str(FUZCAKE_DATA_ROOT / "assets")]

# Keep the full initial fragrance collection visible during catalogue journeys.
OSCAR_PRODUCTS_PER_PAGE = 24
