"""Connect native Wowy pages to validated local cart and COD checkout actions."""
from uuid import uuid4
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cart.models import Cart, CartItem
from cart.serializers import CartSerializer
from orders.models import Order
from products.models import Product, ProductVariant
from users.models import Address
from storefront.commerce import CheckoutError, cancel, carrier_choice, checkout, integer
from storefront.models import CheckoutReceipt
from fuzcake_data import reference


def health(request):
    """Return an app-specific readiness identity without querying a database."""
    return JsonResponse({"target": "wowy", "commit": "1781390d41c991e0211f4e1042f0e54033dae2ed"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cart_list(request):
    """Keep the upstream cart serializer shape used by the native drawer."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return Response([CartSerializer(cart, context={"request": request}).data])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cart_add(request):
    """Validate complete accumulated quantity, product status and variant ownership."""
    try:
        product = get_object_or_404(Product, pk=integer(request.data.get("product_id")), is_active=True, category__status="active")
        quantity = integer(request.data.get("quantity", 1))
        variant_id = request.data.get("variant_id")
        variant = get_object_or_404(ProductVariant, pk=integer(variant_id), product=product) if variant_id else None
        if product.has_variants and variant is None:
            raise CheckoutError("Choose a product variant before adding it to the cart.")
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart = Cart.objects.select_for_update().get(pk=cart.pk)
        line = CartItem.objects.filter(cart=cart, product=product, variant=variant).first()
        combined = quantity + (line.quantity if line else 0)
        if combined > (variant or product).stock:
            raise CheckoutError("The requested total quantity exceeds available stock.")
        if line:
            line.quantity = combined
            line.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=quantity)
        return Response({"message": "Item added to cart", "cart_total": cart.total_items})
    except CheckoutError as error:
        return Response({"error": str(error)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cart_update(request):
    """Update only the caller's line; zero removes it and variants use their own stock."""
    try:
        line = get_object_or_404(CartItem.objects.select_related("product", "variant", "cart"),
                                 pk=integer(request.data.get("item_id")), cart__user=request.user)
        quantity = integer(request.data.get("quantity"), minimum=0)
        if quantity > (line.variant or line.product).stock:
            raise CheckoutError("The requested quantity exceeds available stock.")
        cart = line.cart
        removed = quantity == 0
        if removed:
            line.delete()
        else:
            line.quantity = quantity
            line.save(update_fields=["quantity"])
        return Response({"message": "Item removed from cart" if removed else "Quantity updated",
            "item_subtotal": "0.00" if removed else str(line.subtotal),
            "cart_total": cart.total_items, "cart_total_price": str(cart.total_price)})
    except CheckoutError as error:
        return Response({"error": str(error)}, status=400)


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def checkout_page(request):
    """Render the local checkout form; navigation continues through actual page links."""
    error = None
    if request.method == "POST":
        try:
            token = request.POST.get("token", "")
            existing = CheckoutReceipt.objects.filter(token=token, order__user=request.user).first()
            if existing:
                return redirect("orders:success", order_number=existing.order.order_number)
            if not token or token != request.session.get("wowy_checkout_token"):
                raise CheckoutError("This checkout form has expired. Reload checkout and try again.")
            if request.POST.get("payment_method") != "cash_on_delivery":
                raise CheckoutError("Choose cash on delivery for this local store.")
            order = checkout(request.user, request.POST.get("shipping_address"), request.POST.get("carrier"), token)
            request.session.pop("wowy_checkout_token", None)
            return redirect("orders:success", order_number=order.order_number)
        except CheckoutError as failure:
            error = str(failure)
    cart = Cart.objects.filter(user=request.user).first()
    token = request.session.setdefault("wowy_checkout_token", uuid4().hex)
    return render(request, "cart/checkout.html", {"cart": cart,
        "cart_items": cart.items.select_related("product", "variant") if cart else [],
        "addresses": request.user.addresses.filter(shipping_orders__isnull=True), "checkout_token": token, "checkout_error": error,
        "carriers": reference("partners")["carriers"]}, status=400 if error else 200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def place_order(request):
    """Preserve a native API alias while requiring the same session token and COD rules."""
    try:
        token = request.data.get("token", "")
        existing = CheckoutReceipt.objects.filter(token=token, order__user=request.user).first()
        if existing:
            order = existing.order
        else:
            if token != request.session.get("wowy_checkout_token") or not token:
                raise CheckoutError("Open checkout and submit its current form.")
            if request.data.get("payment_method") != "cash_on_delivery":
                raise CheckoutError("Only cash on delivery is available in this local store.")
            order = checkout(request.user, request.data.get("shipping_address"), request.data.get("carrier"), token)
            request.session.pop("wowy_checkout_token", None)
        return Response({"message": "Order placed successfully", "redirect_url": reverse("orders:success", args=[order.order_number])})
    except CheckoutError as error:
        return Response({"error": str(error)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Scope cancellation to the caller and restore inventory through one shared action."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    try:
        cancel(order)
        return Response({"message": "Order cancelled successfully"})
    except CheckoutError as error:
        return Response({"error": str(error)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_address(request):
    """Keep addresses referenced by any order and avoid leaking protected-model exceptions."""
    try:
        address = get_object_or_404(Address, pk=integer(request.data.get("address_id")), user=request.user)
        if address.is_default or Order.objects.filter(Q(shipping_address=address) | Q(billing_address=address)).exists():
            raise CheckoutError("Keep the default address and addresses already used by an order.")
        address.delete()
        return Response({"message": "Address deleted successfully"})
    except CheckoutError as error:
        return Response({"error": str(error)}, status=400)


def disabled_payment(request):
    """Explain the local payment scope without initiating an external gateway request."""
    return JsonResponse({"error": "This local target uses cash on delivery. Return to checkout to place an order."}, status=400)


def local_payment_settings(request):
    """Keep the native administration navigation with accurate local payment information."""
    return render(request, "local-payment-settings.html")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_address(request):
    """Update address-book rows while refusing changes to immutable order addresses."""
    try:
        address = get_object_or_404(Address, pk=integer(request.data.get("address_id")), user=request.user,
                                  shipping_orders__isnull=True, billing_orders__isnull=True)
        values = {field: request.data.get(field, "") for field in ("phone", "address", "city", "postal_code")}
        if any(not isinstance(v, str) or not v.strip() for v in values.values()):
            raise CheckoutError("Complete the phone, address, city and postal code fields.")
        if not values["phone"].isdigit() or not 10 <= len(values["phone"]) <= 15:
            raise CheckoutError("Enter a numeric local phone value from 10 to 15 digits.")
        if len(values["city"]) > 100 or len(values["postal_code"]) > 10 or len(values["address"]) > 1000:
            raise CheckoutError("The address is too long. Shorten the city, postal code or street fields.")
        for field, value in values.items():
            setattr(address, field, value.strip())
        default = request.data.get("is_default", False)
        if default not in (True, False):
            raise CheckoutError("Choose a valid default-address option.")
        address.is_default = default
        address.save()
        return Response({"message": "Address updated successfully"})
    except CheckoutError as error:
        return Response({"error": str(error)}, status=400)
