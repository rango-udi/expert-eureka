"""Protect ordered inventory and store each local checkout token once."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("orders", "0002_order_payment_intent_id"), ("products", "0001_initial")]
    operations = [
        migrations.CreateModel(name="CheckoutReceipt", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("token", models.CharField(max_length=32, unique=True)),
            ("carrier", models.CharField(max_length=40)),
            ("stock_restored", models.BooleanField(default=False)),
            ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="local_receipt", to="orders.order")),
        ]),
        migrations.CreateModel(name="OrderLineSnapshot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("sku", models.CharField(max_length=50)), ("name", models.CharField(max_length=255)),
            ("quantity", models.PositiveIntegerField()), ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
            ("receipt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="storefront.checkoutreceipt")),
            ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="products.product")),
            ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="products.productvariant")),
        ]),
    ]
