"""Follow rendered Oscar links/forms with CSRF enabled; these are HTTP tests, not browser tests."""

import os
from decimal import Decimal
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from django.test import Client, TestCase
from django.core.management import call_command
from oscar.core.loading import get_model
from fuzcake_data.robot_data import get_shipping_address


class HttpJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Seed real Oscar accounts and commerce models into a disposable database."""
        call_command("seed_demo", verbosity=0)
        call_command("rebuild_index", interactive=False, verbosity=0)

    def setUp(self):
        """Start a fresh CSRF-enforcing session at the storefront root."""
        call_command("rebuild_index", interactive=False, verbosity=0)
        self.client = Client(enforce_csrf_checks=True)
        self.response = self.client.get("/", follow=True)

    def follow_link(self, text):
        """Navigate an existing rendered local anchor by visible text without constructing its URL."""
        soup = BeautifulSoup(self.response.content, "html.parser")
        links = [
            link
            for link in soup.find_all("a", href=True)
            if text in link.get_text(" ", strip=True)
        ]
        self.assertTrue(links, f"No rendered navigation link contains: {text}")
        href = links[0]["href"]
        self.assertFalse(urlsplit(href).netloc)
        self.response = self.client.get(href, follow=True)
        self.assertEqual(self.response.status_code, 200)
        return self.response

    def submit_form(self, selector, changes=None):
        """Submit a rendered form with its CSRF token and caller-selected values to its own action."""
        soup = BeautifulSoup(self.response.content, "html.parser")
        form = soup.select_one(selector)
        self.assertIsNotNone(form, f"No rendered form matches: {selector}")
        data = {}
        for field in form.select(
            "input[name], button[name], select[name], textarea[name]"
        ):
            if field.has_attr("disabled"):
                continue
            if field.get("type") in ("checkbox", "radio") and not field.has_attr(
                "checked"
            ):
                continue
            if field.name == "select":
                option = field.select_one("option[selected]") or field.select_one(
                    "option"
                )
                value = option.get("value", option.get_text()) if option else ""
            else:
                value = field.get("value", "")
            data[field["name"]] = value
        data.update(changes or {})
        action = form.get("action") or self.response.wsgi_request.path
        self.assertFalse(urlsplit(action).netloc)
        self.response = self.client.post(action, data, follow=True)
        self.assertEqual(self.response.status_code, 200)
        return self.response

    def login_role(self, role):
        """Log in through the storefront form and confirm its rendered logout control."""
        self.follow_link("Login or register")
        self.submit_form(
            "#login_form",
            {
                "login-username": os.environ[role + "_EMAIL"],
                "login-password": os.environ[role + "_PASSWORD"],
            },
        )
        if role == "ADMIN":
            self.assertContains(self.response, "logout_form")
            self.follow_link("Return to site")
        self.assertContains(self.response, "logout_link")

    def place_customer_order(self):
        """Complete customer checkout through linked product, basket, shipping and COD forms."""
        self.login_role("CUSTOMER")
        self.follow_link("Rose Nocturne")
        self.submit_form("#add_to_basket_form", {"quantity": "1"})
        self.follow_link("View basket")
        self.follow_link("Proceed to checkout")
        self.submit_form(
            "#new_shipping_address",
            {
                "first_name": get_shipping_address()["first_name"],
                "last_name": get_shipping_address()["last_name"],
                "line1": get_shipping_address()["street"],
                "line4": get_shipping_address()["city"],
                "postcode": get_shipping_address()["postal_code"],
                "country": get_shipping_address()["country"],
            },
        )
        self.assertContains(self.response, "Cash on delivery")
        self.assertNotContains(self.response, "This page needs implementing")
        self.follow_link("Review order")
        self.submit_form("#place_order_form")
        self.assertContains(self.response, "confirmation")
        order = get_model("order", "Order").objects.get()
        self.assertEqual(order.status, "Pending")
        self.assertEqual(order.total_incl_tax, Decimal("89.00"))
        self.assertEqual(order.sources.get().amount_debited, Decimal("0.00"))
        return order

    def test_guest_can_place_an_unpaid_order(self):
        """Complete guest checkout through its email choice and the real COD confirmation."""
        self.follow_link("Rose Nocturne")
        self.submit_form("#add_to_basket_form", {"quantity": "1"})
        self.follow_link("View basket")
        self.follow_link("Proceed to checkout")
        self.submit_form(
            "form.card", {"username": "guest@example.test", "options": "anonymous"}
        )
        self.submit_form(
            "#new_shipping_address",
            {
                "first_name": get_shipping_address()["first_name"],
                "last_name": get_shipping_address()["last_name"],
                "line1": get_shipping_address()["street"],
                "line4": get_shipping_address()["city"],
                "postcode": get_shipping_address()["postal_code"],
                "country": get_shipping_address()["country"],
            },
        )
        self.follow_link("Review order")
        self.submit_form("#place_order_form")
        self.assertContains(self.response, "confirmation")
        order = get_model("order", "Order").objects.get()
        self.assertIsNone(order.user)
        self.assertEqual(order.sources.get().amount_debited, Decimal("0.00"))

    def test_customer_completes_checkout_and_reads_history(self):
        """Persist an unpaid order, decrement stock and show the same order in account history."""
        order = self.place_customer_order()
        self.follow_link("Continue shopping")
        self.follow_link("Account")
        self.follow_link("Order History")
        self.assertContains(self.response, order.number)
        stock = get_model("partner", "StockRecord").objects.get(partner_sku="fuzcake-rose-nocturne")
        self.assertEqual(stock.num_in_stock - stock.num_allocated, 39)

    def test_admin_manages_customer_order_through_dashboard(self):
        """Navigate from storefront login to a real order and change its status using its dashboard form."""
        order = self.place_customer_order()
        self.client = Client(enforce_csrf_checks=True)
        self.response = self.client.get("/", follow=True)
        self.login_role("ADMIN")
        self.follow_link("Dashboard")
        self.follow_link("Orders")
        self.follow_link(order.number)
        self.submit_form("#order_status_form", {"new_status": "Being processed"})
        order.refresh_from_db()
        self.assertEqual(order.status, "Being processed")

    def test_seller_catalogue_excludes_foreign_partner_product(self):
        """Show assigned stock while excluding a product stocked only by another partner."""
        Product = get_model("catalogue", "Product")
        Partner = get_model("partner", "Partner")
        product = Product.objects.create(
            upc="FOREIGN-001",
            title="Restricted Product",
            product_class=Product.objects.first().product_class,
        )
        partner = Partner.objects.create(code="foreign", name="Foreign seller")
        get_model("partner", "StockRecord").objects.create(
            product=product,
            partner=partner,
            partner_sku="FOREIGN",
            price_currency="USD",
            price=10,
            num_in_stock=5,
        )
        self.login_role("SELLER")
        self.follow_link("Dashboard")
        self.follow_link("Products")
        self.assertContains(self.response, "Rose Nocturne")
        self.assertNotContains(self.response, "Restricted Product")

    def test_voucher_changes_real_basket_total(self):
        """Apply OSCAR10 using the rendered basket form and assert the real percentage discount."""
        self.follow_link("Rose Nocturne")
        self.submit_form("#add_to_basket_form", {"quantity": 1})
        self.follow_link("View basket")
        self.submit_form("#voucher_form", {"code": "OSCAR10"})
        self.assertContains(self.response, "OSCAR10")
        basket = get_model("basket", "Basket").objects.get(status="Open")
        self.assertEqual(basket.vouchers.get().code, "OSCAR10")
        self.assertContains(self.response, "80.10")
