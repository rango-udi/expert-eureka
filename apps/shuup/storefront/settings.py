"""Use upstream Shuup workbench apps with private SQLite data and local-only access."""
from pathlib import Path
import hashlib
import os
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / ".runtime/data"
(DATA_DIR / "workbench").mkdir(parents=True, exist_ok=True)
# Keep the upstream settings module's temporary SQLite/addon paths inside private data.
os.environ["SHUUP_WORKBENCH_BASE_DIR"] = str(DATA_DIR / "workbench")
from shuup_workbench.settings.base_settings import *

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / ".runtime/data"
SECRET_KEY = os.environ["SECRET_KEY"]
# Stable 32-character encryption key derived from the persisted signing secret.
MIRAGE_SECRET_KEY = hashlib.sha256(SECRET_KEY.encode("utf-8")).hexdigest()[:32]
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "shuup", "testserver"]
ROOT_URLCONF = "storefront.urls"
WSGI_APPLICATION = "storefront.wsgi.application"

# Django 2.2 and legacy integrations expect text paths, including connection cleanup.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(DATA_DIR / "db.sqlite3"), "OPTIONS": {"timeout": 20}}}
MEDIA_ROOT = str(DATA_DIR / "media")
STATIC_ROOT = str(DATA_DIR / "static")
MEDIA_URL = "/media/"
STATIC_URL = "/static/"
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = str(DATA_DIR / "mail")
DEFAULT_FROM_EMAIL = "care@fuzcake.test"
TIME_ZONE = os.environ.get("TIMEZONE", "Asia/Bangkok")
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English")]
PARLER_DEFAULT_LANGUAGE_CODE = "en"
PARLER_LANGUAGES = {None: [{"code": "en"}], "default": {"hide_untranslated": False}}
SHUUP_TELEMETRY_ENABLED = False
# New stores use the reference currency; persisted shops retain their own currency.
SHUUP_HOME_CURRENCY = "USD"
SESSION_SERIALIZER = "storefront.session_serializer.CheckoutJSONSerializer"
# Check exact whole units before the native display converter rounds them.
SHUUP_BASKET_UPDATE_METHODS_SPEC = "storefront.basket:WholeUnitBasketUpdateMethods"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "OPTIONS": {"MAX_ENTRIES": 128}}}
INSTALLED_APPS = list(INSTALLED_APPS) + ["storefront.apps.StorefrontConfig"]
TEMPLATES[0]["DIRS"] = [str(BASE_DIR / "storefront/templates")]
TEMPLATES[0]["OPTIONS"]["context_processors"] = list(TEMPLATES[0]["OPTIONS"]["context_processors"]) + ["storefront.business_data.storefront_context"]
# Management work uses one process; the application does not need a persistent job service.
SHUUP_TASK_RUNNER = "shuup.core.tasks.DefaultTaskRunner"

# Shared fixtures remain outside application secrets and runtime data.
FUZCAKE_DATA_ROOT = Path("/fuzcake-data")
sys.path.insert(0, str(FUZCAKE_DATA_ROOT))
STATICFILES_DIRS = [str(FUZCAKE_DATA_ROOT / "assets")]

# Persist request tracebacks beside the mounted database, without logging form payloads.
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"request_error": {"format": "{asctime} {levelname} {message}", "style": "{"}},
    "handlers": {"request_errors": {"class": "logging.handlers.RotatingFileHandler",
        "filename": str(DATA_DIR / "request-errors.log"), "maxBytes": 524288,
        "backupCount": 2, "encoding": "utf-8", "formatter": "request_error", "level": "ERROR"}},
    "loggers": {"django.request": {"handlers": ["request_errors"], "level": "ERROR", "propagate": False}},
}
