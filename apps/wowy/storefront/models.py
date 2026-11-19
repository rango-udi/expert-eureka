"""Record idempotent local checkout and immutable variant/price snapshots."""
from django.db import models


class CheckoutReceipt(models.Model):
    token = models.CharField(max_length=32, unique=True)
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="local_receipt")
    carrier = models.CharField(max_length=40)
    stock_restored = models.BooleanField(default=False)


class OrderLineSnapshot(models.Model):
    receipt = models.ForeignKey(CheckoutReceipt, related_name="lines", on_delete=models.CASCADE)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    variant = models.ForeignKey("products.ProductVariant", null=True, blank=True, on_delete=models.PROTECT)
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
