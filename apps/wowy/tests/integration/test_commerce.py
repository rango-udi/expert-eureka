"""Exercise native Wowy models, rendered navigation and local checkout in Docker."""
import json
import os
import tempfile
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from products.models import Product
from users.models import Address
from orders.models import Order
from cart.models import CartItem
from storefront.models import CheckoutReceipt
from fuzcake_data import reference


class CommerceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """Isolate uploaded fixture images from the persisted operator media directory."""
        cls.media = tempfile.TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.override.enable()
        try:
            super().setUpClass()
        except Exception:
            cls.override.disable()
            cls.media.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        """Release test uploads after Django closes the isolated database."""
        try:
            super().tearDownClass()
        finally:
            cls.override.disable()
            cls.media.cleanup()

    @classmethod
    def setUpTestData(cls):
        """Create only the registered shared catalogue in the disposable database."""
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        """Use a real CSRF-enforcing session and the configured customer identity."""
        self.customer = get_user_model().objects.get(email=os.environ["CUSTOMER_EMAIL"])
        self.product = Product.objects.get(sku="fuzcake-rose-nocturne")
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.customer)
        self.client.get("/")

    def post_api(self, path, data):
        """Submit JSON through SessionAuthentication with the page-issued CSRF cookie."""
        return self.client.post(path, data=json.dumps(data), content_type="application/json",
                                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)

    def place(self):
        """Follow the native cart API and submit the rendered checkout form's values."""
        added = self.post_api(reverse("cart:add"), {"product_id": self.product.pk, "quantity": 1})
        self.assertEqual(added.status_code, 200)
        response = self.client.get(reverse("cart:checkout"))
        self.assertContains(response, "Rose Nocturne")
        token = self.client.session["wowy_checkout_token"]
        address = self.customer.addresses.filter(shipping_orders__isnull=True).first()
        data = {"token": token, "shipping_address": address.pk,
                "carrier": reference("partners")["carriers"][0]["id"], "payment_method": "cash_on_delivery",
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value}
        result = self.client.post(reverse("cart:checkout"), data)
        self.assertEqual(result.status_code, 302)
        return Order.objects.get(user=self.customer), data, address

    def test_home_health_and_login_are_real_routes(self):
        """Render the branded collection and use the native email/password form."""
        self.assertEqual(self.client.get("/_cmdc/health").json()["target"], "wowy")
        home = self.client.get("/")
        self.assertContains(home, "Rose Nocturne")
        self.assertContains(home, reverse("products:detail", args=[self.product.slug]))
        anonymous = Client()
        response = anonymous.post(reverse("users:login"), {"email": os.environ["CUSTOMER_EMAIL"],
                                  "password": os.environ["CUSTOMER_PASSWORD"]})
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", anonymous.session)

    def test_checkout_total_stock_replay_and_unpaid_status(self):
        """Charge shipping once, reserve inventory once and keep COD explicitly unpaid."""
        before = self.product.stock
        order, data, _ = self.place()
        self.assertEqual(order.total_amount, Decimal("89.00"))
        self.assertEqual(order.delivery_charge, Decimal("4.95"))
        self.assertEqual(order.grand_total, Decimal("93.95"))
        self.assertEqual(order.payment_status, "pending")
        again = self.client.post(reverse("cart:checkout"), data)
        self.assertEqual(again.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, before - 1)
        self.assertFalse(CartItem.objects.exists())

    def test_cancel_restores_stock_once_and_protects_history(self):
        """Repeated cancellation cannot replenish inventory twice or delete an ordered SKU."""
        before = self.product.stock
        order, _, _ = self.place()
        for _ in range(2):
            result = self.post_api(reverse("orders:cancel", args=[order.pk]), {})
            self.assertEqual(result.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, before)
        self.assertTrue(CheckoutReceipt.objects.get(order=order).stock_restored)
        with self.assertRaises(ProtectedError):
            self.product.delete()

    def test_accumulated_quantity_cannot_exceed_stock_and_csrf_is_required(self):
        """Validate the complete cart quantity and reject missing CSRF before mutation."""
        self.product.stock = 1
        self.product.save()
        path = reverse("cart:add")
        response = self.client.post(path, json.dumps({"product_id": self.product.pk, "quantity": 1}), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.post_api(path, {"product_id": self.product.pk, "quantity": 1}).status_code, 200)
        self.assertEqual(self.post_api(path, {"product_id": self.product.pk, "quantity": 1}).status_code, 400)
        self.assertEqual(CartItem.objects.get().quantity, 1)
        for value in (0, -1, "1.5", True, "abc"):
            self.assertEqual(self.post_api(path, {"product_id": self.product.pk, "quantity": value}).status_code, 400)

    def test_foreign_address_and_non_cod_selection_are_rejected(self):
        """Client IDs and payment names cannot override account ownership or local scope."""
        self.post_api(reverse("cart:add"), {"product_id": self.product.pk, "quantity": 1})
        self.client.get(reverse("cart:checkout"))
        other = get_user_model().objects.create_user(email="ivy@fuzcake.test", name="Ivy Marin", phone="12025550149", password="local-only-password")
        address = Address.objects.create(user=other, phone=other.phone, address="71 Silvercloud Lane", city="Moonberry", postal_code="99949")
        base = {"token": self.client.session["wowy_checkout_token"], "shipping_address": address.pk,
                "carrier": "fuzcake-delivery", "payment_method": "cash_on_delivery"}
        self.assertEqual(self.post_api(reverse("cart:place_order"), base).status_code, 400)
        base["payment_method"] = "stripe"
        self.assertEqual(self.post_api(reverse("cart:place_order"), base).status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 25)

    def test_customer_cannot_read_custom_administration(self):
        """The global admin boundary covers dashboard, reports and customer records."""
        for path in ("/users/admin/", "/users/admin/orders/", "/users/admin/customers/", "/users/admin/reports/"):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_seed_preserves_price_stock_password_and_runtime_orders(self):
        """A second setup keeps interaction data while reading the same stable reference IDs."""
        order, _, _ = self.place()
        self.product.stock = 7
        self.product.selling_price = Decimal("91.00")
        self.product.save()
        self.customer.set_password("operator-kept-password")
        self.customer.save()
        call_command("seed_demo", verbosity=0)
        self.product.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(self.product.stock, 7)
        self.assertEqual(self.product.selling_price, Decimal("91.00"))
        self.assertTrue(self.customer.check_password("operator-kept-password"))
        self.assertEqual(Product.objects.count(), 16)
        self.assertEqual(Order.objects.get().pk, order.pk)

    def test_order_address_is_a_snapshot_and_does_not_pollute_address_book(self):
        """Editing a saved address leaves the order's original delivery details intact."""
        order, _, source = self.place()
        original = order.shipping_address.address
        result = self.post_api("/users/api/address/update/", {"address_id": source.pk, "phone": source.phone,
            "address": "88 Velvet Garden Boulevard", "city": "Moonberry", "postal_code": "99944", "is_default": True})
        self.assertEqual(result.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.shipping_address.address, original)
        self.assertEqual(self.customer.addresses.filter(shipping_orders__isnull=True).count(), 2)
        result = self.post_api("/users/api/address/update/", {"address_id": order.shipping_address_id})
        self.assertEqual(result.status_code, 404)
