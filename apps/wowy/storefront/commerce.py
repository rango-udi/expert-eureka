"""Perform local COD checkout with exact totals, stock reservations and replay protection."""
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
from django.db.models import F
from orders.models import Order, OrderItem
from products.models import Product, ProductVariant
from cart.models import Cart
from users.models import Address
from storefront.models import CheckoutReceipt, OrderLineSnapshot
from fuzcake_data import reference


class CheckoutError(ValueError):
    """Describe a recoverable cart or order problem without exposing source internals."""


def integer(value, minimum=1):
    """Accept an integer form/JSON value and reject fractional, boolean or oversized input."""
    text = str(value)
    if not text.isascii() or not text.isdigit() or len(text) > 8 or int(text) < minimum:
        raise CheckoutError("Enter a whole-number quantity within the available stock.")
    return int(text)


def carrier_choice(identifier):
    """Resolve the shared delivery choice without trusting a client-supplied fee."""
    for carrier in reference("partners")["carriers"]:
        if carrier["id"] == identifier:
            return carrier
    raise CheckoutError("Choose a delivery service listed at checkout.")


@transaction.atomic
def checkout(user, shipping_id, carrier_id, token):
    """Create one unpaid COD order and reserve real product/variant stock atomically."""
    existing = CheckoutReceipt.objects.filter(token=token, order__user=user).first()
    if existing:
        return existing.order
    address = Address.objects.filter(pk=integer(shipping_id), user=user, shipping_orders__isnull=True).first()
    if address is None:
        raise CheckoutError("Choose a shipping address from your account.")
    carrier = carrier_choice(carrier_id)
    cart = Cart.objects.select_for_update().filter(user=user).first()
    if cart is None:
        raise CheckoutError("Your cart is empty. Add a fragrance before checkout.")
    items = list(cart.items.select_related("product", "variant").order_by("product_id", "variant_id"))
    if not items:
        raise CheckoutError("Your cart is empty. Add a fragrance before checkout.")
    snapshots = []
    total = Decimal("0.00")
    for line in items:
        quantity = integer(line.quantity)
        product = Product.objects.get(pk=line.product_id)
        if not product.is_active or product.category.status != "active":
            raise CheckoutError("A product is no longer available. Update your cart before checkout.")
        variant = line.variant
        if (variant and variant.product_id != product.pk) or (product.has_variants and variant is None):
            raise CheckoutError("Choose a valid variant for each product in your cart.")
        inventory = ProductVariant.objects if variant else Product.objects
        item = variant or product
        if item.selling_price < 0:
            raise CheckoutError("A product price needs correction. Contact the store team.")
        if inventory.filter(pk=item.pk, stock__gte=quantity).update(stock=F("stock") - quantity) != 1:
            raise CheckoutError("Stock changed while you were shopping. Update the cart and try again.")
        total += item.selling_price * quantity
        snapshots.append((product, variant, quantity, item.selling_price, item.sku))
    # Native address-book rows remain editable; an order keeps its own immutable copy.
    snapshot_address = Address.objects.create(user=user, phone=address.phone, address=address.address,
        city=address.city, postal_code=address.postal_code, is_default=False)
    order = Order.objects.create(user=user, shipping_address=snapshot_address, billing_address=snapshot_address,
        order_number="FC-" + uuid4().hex[:16].upper(), total_amount=total,
        delivery_charge=Decimal(carrier["fee"]), payment_method="cash_on_delivery",
        payment_status="pending", status="pending")
    receipt = CheckoutReceipt.objects.create(token=token, order=order, carrier=carrier["id"])
    for product, variant, quantity, price, sku in snapshots:
        OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price)
        OrderLineSnapshot.objects.create(receipt=receipt, product=product, variant=variant,
            name=product.name, sku=sku, quantity=quantity, unit_price=price)
    cart.items.all().delete()
    return order


@transaction.atomic
def cancel(order):
    """Cancel an unpaid pending local order and restore each reserved stock line once."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    receipt = CheckoutReceipt.objects.select_for_update().filter(order=order).first()
    if order.status == "cancelled" and receipt and receipt.stock_restored:
        return order
    if order.status != "pending" or order.payment_status != "pending" or receipt is None:
        raise CheckoutError("Only pending unpaid local orders can be cancelled here.")
    if not receipt.stock_restored:
        for line in receipt.lines.all():
            model = ProductVariant if line.variant_id else Product
            key = line.variant_id or line.product_id
            model.objects.filter(pk=key).update(stock=F("stock") + line.quantity)
        receipt.stock_restored = True
        receipt.save(update_fields=["stock_restored"])
    order.status = "cancelled"
    order.save(update_fields=["status"])
    return order
