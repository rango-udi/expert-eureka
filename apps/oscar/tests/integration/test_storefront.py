"""Verify real fixture roles, repeatable seeding and unpaid COD payment behavior."""

from decimal import Decimal
import os
from types import SimpleNamespace
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from oscar.core.loading import get_model


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Seed real Oscar records into Django's isolated test database once per class."""
        call_command("seed_demo", verbosity=0)
        call_command("rebuild_index", interactive=False, verbosity=0)

    def test_fixture_accounts_have_distinct_roles(self):
        """Keep customer, partner-linked seller and superuser privileges distinct."""
        users = get_user_model()
        customer = users.objects.get(email=os.environ["CUSTOMER_EMAIL"])
        seller = users.objects.get(email=os.environ["SELLER_EMAIL"])
        admin = users.objects.get(email=os.environ["ADMIN_EMAIL"])
        self.assertFalse(customer.is_staff)
        self.assertFalse(seller.is_staff)
        self.assertTrue(seller.has_perm("partner.dashboard_access"))
        self.assertFalse(seller.is_superuser)
        self.assertTrue(seller.partners.filter(code="oscar-market").exists())
        self.assertTrue(admin.is_superuser)

    def test_seed_preserves_existing_password_and_stock(self):
        """Reinitialization must not undo a purchase or reset an operator's existing password."""
        user = get_user_model().objects.get(email=os.environ["CUSTOMER_EMAIL"])
        user.set_password("operator-changed-password")
        user.save()
        record = get_model("partner", "StockRecord").objects.get(partner_sku="fuzcake-rose-nocturne")
        record.num_in_stock = 37
        record.save()
        call_command("seed_demo", verbosity=0)
        user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(user.check_password("operator-changed-password"))
        self.assertEqual(record.num_in_stock, 37)
        self.assertEqual(get_model("catalogue", "Product").objects.count(), 16)

    def test_storefront_uses_real_oscar_templates(self):
        """Render the seeded catalogue through Oscar and expose real product links."""
        response = self.client.get("/", follow=True)
        self.assertContains(response, "Rose Nocturne")
        self.assertContains(response, "fuzcake")
        self.assertTemplateUsed(response, "oscar/catalogue/browse.html")

    def test_cod_does_not_claim_money_was_collected(self):
        """Record the selected offline payment method with zero allocation and zero debit."""
        from storefront.checkout.views import PaymentDetailsView

        view = PaymentDetailsView()
        view.handle_payment(
            "100001", SimpleNamespace(currency="USD", incl_tax=Decimal("39.00"))
        )
        source = view._payment_sources[0]
        self.assertEqual(source.amount_allocated, Decimal("0.00"))
        self.assertEqual(source.amount_debited, Decimal("0.00"))
        self.assertEqual(source.source_type.code, "cash-on-delivery")
