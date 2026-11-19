"""Expose Oscar storefront/dashboard and a local health probe."""

from django.apps import apps
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    """Return the target identity for launcher readiness checks; no data is changed."""
    return JsonResponse({"target": "django-oscar", "version": "4.2.1"})


urlpatterns = [
    path("_cmdc/health", health),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include(apps.get_app_config("oscar").urls[0])),
]
