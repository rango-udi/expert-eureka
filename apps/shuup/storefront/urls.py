"""Expose real Shuup storefront/admin routes and a local readiness identity."""
from django.http import JsonResponse
from django.urls import include, path
from storefront.views import information, wallet


def health(request):
    """Return the fixture target identity without opening a database transaction."""
    return JsonResponse({"target": "shuup", "version": "3.1.0"})


urlpatterns = [
    path("_cmdc/health", health),
    path("wallet/", wallet, name="fuzcake-wallet"),
    path("our-house/", information, {"section": "house"}, name="fuzcake-house"),
    path("delivery/", information, {"section": "delivery"}, name="fuzcake-delivery"),
    path("payment-partners/", information, {"section": "partners"}, name="fuzcake-partners"),
    path("sa/", include("shuup.admin.urls", namespace="shuup_admin")),
    path("", include("shuup.front.urls", namespace="shuup")),
]
