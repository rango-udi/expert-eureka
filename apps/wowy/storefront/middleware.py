"""Apply the local administration boundary before invoking upstream view functions."""
import logging
from django.db.models.deletion import ProtectedError
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from orders.models import Order
from storefront.commerce import CheckoutError, cancel
from storefront.views import local_payment_settings


class LocalAccessBoundary:
    def __init__(self, get_response):
        """Retain the downstream handler while leaving Django authentication and CSRF intact."""
        self.get_response = get_response

    def __call__(self, request):
        """Pass responses through the standard Django middleware chain."""
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Guard every native custom-admin route and delegate safe inventory transitions."""
        if not request.path.startswith("/users/admin/"):
            return None
        if not request.user.is_authenticated:
            return redirect(reverse("users:login"))
        if not request.user.is_superuser:
            return HttpResponseForbidden("Administration requires the configured administrator account.")
        name = getattr(view_func, "__name__", "")
        if name == "admin_payment_settings":
            return local_payment_settings(request)
        if name in ("admin_product_delete", "admin_product_image_delete", "admin_offer_delete", "admin_product_variant_delete"):
            if request.method != "POST":
                return HttpResponseNotAllowed(["POST"])
        if name == "update_order_status" and request.method == "POST":
            order = Order.objects.filter(pk=view_kwargs.get("order_id")).first()
            if order is None:
                return None
            status = request.POST.get("status")
            try:
                if status == "cancelled":
                    cancel(order)
                    messages.success(request, "Order cancelled and reserved stock restored.")
                    return redirect("users:admin.order_edit", order_id=order.pk)
                if order.status == "cancelled":
                    raise CheckoutError("A cancelled order cannot be reopened. Create a new order to reserve stock.")
            except CheckoutError as error:
                messages.error(request, str(error))
                return redirect("users:admin.order_edit", order_id=order.pk)
        return None

    def process_exception(self, request, exception):
        """Keep unexpected diagnostics in container logs and return a readable page or API error."""
        if isinstance(exception, ProtectedError) and request.path.startswith("/users/admin/"):
            messages.error(request, "This record is referenced by an order. Deactivate the product instead of deleting its history.")
            return redirect("users:admin_products")
        logging.getLogger("wowy.local").error("Wowy request failed at %s", request.path, exc_info=(type(exception), exception, exception.__traceback__))
        if "/api/" in request.path:
            return JsonResponse({"error": "This action could not finish. Check the submitted values and try again; review cmdc logs --app wowy if it continues."}, status=500)
        from django.shortcuts import render
        return render(request, "operation-error.html", status=500)
