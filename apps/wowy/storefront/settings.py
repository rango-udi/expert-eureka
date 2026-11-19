"""Isolate the native Wowy apps with SQLite, local email and shared fuzcake records."""
import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
UPSTREAM_DIR = Path("/opt/wowy")
FUZCAKE_DATA_ROOT = Path("/fuzcake-data")
sys.path.insert(0, str(FUZCAKE_DATA_ROOT))
sys.path.append(str(UPSTREAM_DIR))
DATA_DIR = BASE_DIR / ".runtime/data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "wowy", "testserver"]
ROOT_URLCONF = "storefront.urls"
WSGI_APPLICATION = "storefront.wsgi.application"
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
                  "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
                  "users", "core", "categories", "products", "cart", "rest_framework", "orders",
                  "wishlist", "offers", "storefront"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
              "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
              "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
              "django.middleware.clickjacking.XFrameOptionsMiddleware", "users.middleware.WishlistCountMiddleware",
              "storefront.middleware.LocalAccessBoundary"]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [str(BASE_DIR / "storefront/templates"), str(UPSTREAM_DIR / "templates")],
              "APP_DIRS": True, "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages", "storefront.context.business_context"]}}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(DATA_DIR / "db.sqlite3"),
                         "OPTIONS": {"timeout": 20}, "ATOMIC_REQUESTS": True}}
AUTH_USER_MODEL = "users.User"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                             "OPTIONS": {"min_length": 10}}]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/users/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = LOGIN_URL
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIMEZONE", "Asia/Bangkok")
USE_TZ = True
USE_I18N = True
STATIC_URL = "/static/"
STATIC_ROOT = str(DATA_DIR / "static")
STATICFILES_DIRS = [str(UPSTREAM_DIR / "static"), str(FUZCAKE_DATA_ROOT / "assets")]
MEDIA_URL = "/media/"
MEDIA_ROOT = str(DATA_DIR / "media")
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = str(DATA_DIR / "mail")
DEFAULT_FROM_EMAIL = "care@fuzcake.test"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "OPTIONS": {"MAX_ENTRIES": 128}}}
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"]}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
