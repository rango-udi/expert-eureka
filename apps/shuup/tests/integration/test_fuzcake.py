"""Exercise the real themed store and ledger only in the Django Docker test database."""
from decimal import Decimal
import os
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Sum
from django.test import Client, TestCase, override_settings
from shuup.core.models import Product, Shop, PersonContact, MutableAddress
from shuup.xtheme import get_current_theme
from shuup.simple_supplier.models import StockAdjustment
from storefront.business_data import reference
from storefront.models import WalletMovement
from storefront.views import funding_amount
from storefront.management.commands.seed_demo import seed_customer_addresses, seed_coupon


class FuzcakeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """Keep test uploads outside the operator's persisted media directory."""
        cls.media = tempfile.TemporaryDirectory()
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media.name)
        cls.settings_override.enable()
        try:
            super().setUpClass()
        except Exception:
            cls.settings_override.disable()
            cls.media.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        """Remove isolated uploads after the test database has been released."""
        try:
            super().tearDownClass()
        finally:
            cls.settings_override.disable()
            cls.media.cleanup()

    @classmethod
    def setUpTestData(cls):
        """Initialize isolated shop records with non-production credentials."""
        with patch.dict(os.environ, {"COUPON_CODE": "FUZCAKE10", **{
                        role + suffix: value for role in ("ADMIN", "CUSTOMER", "STAFF")
                        for suffix, value in (("_EMAIL", role.lower() + "@fuzcake.test"), ("_PASSWORD", "local-only-password"))}}):
            call_command("seed_demo", verbosity=0)

    def setUp(self):
        """Select the seeded customer for account-scoped ledger assertions."""
        self.customer = get_user_model().objects.get(username="customer@fuzcake.test")
        self.environment = patch.dict(os.environ, {"CUSTOMER_EMAIL": "customer@fuzcake.test"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_common_identity_fields_are_mapped_to_the_native_user(self):
        """Phone metadata used by another adapter must not become an auth.User field."""
        identity = reference("store")["roles"]["CUSTOMER"]
        self.assertIn("phone", identity)
        self.assertEqual(self.customer.first_name, identity["first_name"])
        self.assertEqual(self.customer.last_name, identity["last_name"])

    def test_customer_has_independent_native_address_defaults(self):
        """Both native profile sections use the shared customer address and login email."""
        contact = PersonContact.objects.get(user=self.customer)
        self.assertNotEqual(contact.default_billing_address_id, contact.default_shipping_address_id)
        for address in (contact.default_billing_address, contact.default_shipping_address):
            self.assertEqual(address.street, "42 Fuzzy Future Street")
            self.assertEqual(address.email, self.customer.email)
        self.assertIn(Shop.objects.get(identifier="default"), contact.shops.all())

    def test_missing_address_is_filled_without_replacing_customer_edits(self):
        """Repeated initialization preserves edited shipping and creates only missing billing."""
        contact = PersonContact.objects.get(user=self.customer)
        shipping_id = contact.default_shipping_address_id
        contact.default_shipping_address.street = "81 Silvercloud Lane"
        contact.default_shipping_address.save()
        contact.default_billing_address = None
        contact.phone = ""
        contact.save()
        before = MutableAddress.objects.count()
        shop = Shop.objects.get(identifier="default")
        seed_customer_addresses(self.customer, shop)
        seed_customer_addresses(self.customer, shop)
        contact.refresh_from_db()
        self.assertEqual(MutableAddress.objects.count(), before + 1)
        self.assertEqual(contact.default_shipping_address_id, shipping_id)
        self.assertEqual(contact.default_shipping_address.street, "81 Silvercloud Lane")
        self.assertIsNotNone(contact.default_billing_address_id)
        self.assertEqual(contact.default_billing_address.phone, reference("store")["roles"]["CUSTOMER"]["phone"])

    def test_coupon_uses_native_matching_and_preserves_admin_changes(self):
        """A code gates the native percentage effect and reseeding never resets it."""
        from shuup.campaigns.models import BasketCampaign

        campaign = BasketCampaign.objects.get(identifier="fuzcake-welcome")
        self.assertFalse(campaign.rules_match(SimpleNamespace(codes=[]), []))
        self.assertTrue(campaign.rules_match(SimpleNamespace(codes=[campaign.coupon.code.lower()]), []))
        effect = campaign.discount_effects.first()
        self.assertEqual(effect.value, Decimal("0.10"))
        campaign.coupon.active = False
        campaign.coupon.save()
        seed_coupon(campaign.shop)
        campaign.refresh_from_db()
        self.assertFalse(campaign.coupon.active)
        self.assertEqual(campaign.discount_effects.count(), 1)

    def test_blank_coupon_does_not_create_an_unconditional_campaign(self):
        """Opting out must not accidentally discount every basket."""
        from shuup.campaigns.models import BasketCampaign

        BasketCampaign.objects.filter(identifier="fuzcake-welcome").delete()
        with patch.dict(os.environ, {"COUPON_CODE": ""}):
            seed_coupon(Shop.objects.get(identifier="default"))
        self.assertFalse(BasketCampaign.objects.filter(identifier="fuzcake-welcome").exists())

    def test_reference_balance_uses_posted_movements(self):
        """Pending and failed entries must not change the available balance."""
        total = WalletMovement.objects.filter(owner=self.customer, status="posted").aggregate(v=Sum("amount_minor"))["v"]
        self.assertEqual(total, reference("wallet")["expected_balance_minor"])

    def test_home_uses_brand_and_native_product_routes(self):
        """Resolve the registered theme, shared context, actual images and product links."""
        self.assertEqual(get_current_theme(Shop.objects.get(identifier="default")).identifier, "storefront.fuzcake")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Make it a scent")
        self.assertContains(response, "Rose Nocturne")
        self.assertContains(response, "Floral &amp; romantic")
        self.assertNotContains(response, "Welcome to Store")

    def test_public_information_pages_render(self):
        """Keep delivery, identity and partner pages connected through real routes."""
        for path in ("/our-house/", "/delivery/", "/payment-partners/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertContains(response, "fuzcake")

    def test_collection_and_native_navigation_are_available(self):
        """Retain native menu hooks and resolve both collection entry points."""
        from django.urls import reverse

        home = self.client.get("/")
        self.assertContains(home, 'id="navigation-basket-partial"')
        self.assertContains(home, "toggle-mobile-nav")
        self.assertContains(home, "fc-menu")
        self.assertEqual(home.content.decode().count('<footer '), 1)
        self.assertNotContains(home, 'class="fc-secondary-nav"')
        self.assertNotContains(home, 'Custom Footer Content')
        self.assertContains(home, reverse("shuup:all-categories"))
        self.assertEqual(self.client.get(reverse("shuup:all-categories")).status_code, 200)
        legacy = reverse("shuup:xtheme_extra_view", kwargs={"view": "products"})
        self.assertEqual(self.client.get(legacy).status_code, 200)

    def test_repeat_seed_keeps_stock_password_and_custom_brand(self):
        """Repeated initialization adds no products or ledger entries and preserves edits."""
        shop = Shop.objects.get(identifier="default")
        shop.public_name = "Moonberry Scent Studio"
        shop.save()
        product = Product.objects.get(sku="fuzcake-rose-nocturne")
        product.name = "A personal fragrance"
        product.save()
        password = self.customer.password
        adjustments = StockAdjustment.objects.filter(product=product).count()
        count = WalletMovement.objects.count()
        accounts = {role + suffix: value for role in ("ADMIN", "CUSTOMER", "STAFF")
                    for suffix, value in (("_EMAIL", role.lower() + "@fuzcake.test"), ("_PASSWORD", "replacement-unused"))}
        with patch.dict(os.environ, accounts):
            call_command("seed_demo", verbosity=0)
        self.customer.refresh_from_db()
        shop.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(self.customer.password, password)
        self.assertEqual(shop.public_name, "Moonberry Scent Studio")
        self.assertEqual(product.name, "A personal fragrance")
        self.assertEqual(WalletMovement.objects.count(), count)
        self.assertEqual(StockAdjustment.objects.filter(product=product).count(), adjustments)
        self.assertEqual(Product.objects.filter(sku__startswith="fuzcake-").count(), 16)

    def test_wallet_requires_login_and_does_not_share_customer_ledger(self):
        """Another account starts with its own empty ledger and no linked funding methods."""
        self.assertEqual(self.client.get("/wallet/").status_code, 302)
        other = get_user_model().objects.create_user(username="visitor@fuzcake.test", password="private")
        self.client.force_login(other)
        response = self.client.get("/wallet/")
        self.assertContains(response, "0.00 USD")
        self.assertNotContains(response, "FW-2026-0904-0182")
        self.assertNotContains(response, "card-trb-4286")

    def test_funding_is_exact_and_duplicate_post_does_not_credit_twice(self):
        """A valid local top-up changes the ledger once and a stale token is rejected."""
        self.client.force_login(self.customer)
        self.client.get("/wallet/")
        token = self.client.session["fuzcake_funding_token"]
        data = {"token": token, "amount": "25.10", "method": "card-trb-4286"}
        self.assertEqual(self.client.post("/wallet/", data).status_code, 302)
        self.assertEqual(self.client.post("/wallet/", data).status_code, 400)
        self.assertEqual(WalletMovement.objects.get(reference="FW-LOCAL-" + token).amount_minor, 2510)

    def test_invalid_amounts_and_methods_create_no_movements(self):
        """Reject non-finite, rounded, out-of-range amounts and unknown funding sources."""
        for value in ("NaN", "Infinity", "1e2", "5.001", "-10", "4.99", "500.01", ""):
            with self.assertRaises(ValueError):
                funding_amount(value)
        self.assertEqual(funding_amount("5.01"), 501)
        self.client.force_login(self.customer)
        self.client.get("/wallet/")
        token = self.client.session["fuzcake_funding_token"]
        before = WalletMovement.objects.count()
        self.assertEqual(self.client.post("/wallet/", {"token": token, "amount": "20", "method": "unknown"}).status_code, 400)
        self.assertEqual(WalletMovement.objects.count(), before)

    def test_funding_requires_a_real_csrf_token(self):
        """The session idempotency token does not bypass Django's CSRF middleware."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.customer)
        client.get("/wallet/")
        token = client.session["fuzcake_funding_token"]
        before = WalletMovement.objects.count()
        response = client.post("/wallet/", {"token": token, "method": "card-trb-4286", "amount": "25.00"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WalletMovement.objects.count(), before)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_customer_registration_delivers_native_activation_link(self):
        """A fresh registration must activate only through its delivered email link."""
        import re
        from django.core import mail
        from urllib.parse import urlsplit
        from storefront.management.commands.seed_demo import seed_registration_notification
        from shuup.notify.models import Script

        shop = Shop.objects.first()
        before = Script.objects.filter(shop=shop, event_identifier="registration_received").count()
        seed_registration_notification(shop)
        self.assertEqual(Script.objects.filter(shop=shop, event_identifier="registration_received").count(), before)
        response = self.client.post("/register/", {"username": "aster_native", "email": "aster.native@fuzcake.test",
            "password1": "Local-Registration-9!", "password2": "Local-Registration-9!"})
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="aster_native")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["aster.native@fuzcake.test"])
        content = mail.outbox[0].body + " ".join(str(value[0]) for value in getattr(mail.outbox[0], "alternatives", []))
        link = re.search(r"https?://[^\s<>\"']+/activate/[A-Za-z0-9_]+/", content)
        self.assertIsNotNone(link)
        self.client.get(urlsplit(link.group()).path, follow=True)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_registration_seed_preserves_an_existing_disabled_notification(self):
        """Customer test support must not re-enable or overwrite operator notification choices."""
        from storefront.management.commands.seed_demo import seed_registration_notification
        from shuup.notify.models import Script

        shop = Shop.objects.first()
        script = Script.objects.get(shop=shop, event_identifier="registration_received")
        script.enabled = False
        script.name = "Operator registration policy"
        script.save()
        seed_registration_notification(shop)
        script.refresh_from_db()
        self.assertFalse(script.enabled)
        self.assertEqual(script.name, "Operator registration policy")
        self.assertEqual(Script.objects.filter(shop=shop, event_identifier="registration_received").count(), 1)

    def test_documented_customer_fixture_has_literal_credentials(self):
        """The dedicated active customer must match the account displayed in manual cases."""
        from test_design.specification import load_specification
        from pathlib import Path
        model = load_specification(Path('tests/data/CUSTOMER_DESIGN.yaml'))
        fixture = model['test_data']['existing_customer']
        user = get_user_model().objects.get(username=fixture['username'])
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.email, fixture['email'])
        self.assertTrue(user.check_password(fixture['password']))

    def test_fixture_preparation_does_not_reset_changed_passwords(self):
        """A collision is reported without overwriting existing account access."""
        from django.core.management.base import CommandError
        user = get_user_model().objects.get(username='oliver.bennett')
        user.set_password('Operator!Changed4826')
        user.save()
        with self.assertRaises(CommandError):
            call_command('seed_customer_tests', verbosity=0)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Operator!Changed4826'))

    def test_native_supplier_enforces_the_quantity_boundary(self):
        """The real native module permits 25 and rejects 26 without a theme rule."""
        from shuup.core.models import ShopProduct, Supplier
        from shuup.simple_supplier.models import StockCount
        from shuup.simple_supplier.module import SimpleSupplierModule
        supplier = Supplier.objects.get(identifier='default')
        product = Product.objects.get(sku='fuzcake-rose-nocturne')
        item = ShopProduct.objects.get(shop__identifier='default', product=product)
        stock = StockCount.objects.get(supplier=supplier, product=product)
        self.assertTrue(supplier.stock_managed)
        self.assertTrue(stock.stock_managed)
        self.assertEqual(item.backorder_maximum, Decimal('0'))
        self.assertEqual(stock.logical_count, Decimal('25'))
        module = SimpleSupplierModule(supplier, {})
        self.assertEqual(list(module.get_orderability_errors(item, Decimal('25'), None)), [])
        errors = list(module.get_orderability_errors(item, Decimal('26'), None))
        self.assertIn('stock_insufficient', [error.code for error in errors])

    def test_legacy_stock_policy_repair_keeps_quantities_and_adjustments(self):
        """Repair flags once on legacy records without restocking or deleting orders."""
        from shuup import configuration
        from shuup.core.models import ShopProduct, Supplier
        from shuup.simple_supplier.models import StockCount
        from storefront.stock_policy import POLICY_KEY, repair_fixture_stock_policy
        shop = Shop.objects.get(identifier='default')
        supplier = Supplier.objects.get(identifier='default')
        item = ShopProduct.objects.get(shop=shop, product__sku='fuzcake-rose-nocturne')
        stock = StockCount.objects.get(supplier=supplier, product=item.product)
        stock.logical_count = Decimal('19')
        stock.physical_count = Decimal('23')
        stock.stock_managed = False
        stock.save()
        supplier.stock_managed = False
        supplier.save()
        item.backorder_maximum = None
        item.save()
        configuration.set(shop, POLICY_KEY, None)
        adjustments = list(StockAdjustment.objects.values_list('pk', 'delta'))
        self.assertTrue(repair_fixture_stock_policy(shop, supplier))
        stock.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual((stock.logical_count, stock.physical_count), (Decimal('19'), Decimal('23')))
        self.assertTrue(stock.stock_managed)
        self.assertEqual(item.backorder_maximum, Decimal('0'))
        self.assertEqual(list(StockAdjustment.objects.values_list('pk', 'delta')), adjustments)
        self.assertFalse(repair_fixture_stock_policy(shop, supplier))

    def test_completed_stock_repair_preserves_later_operator_policy(self):
        """Ordinary setup never repeatedly overwrites a policy edited after repair."""
        from shuup.core.models import ShopProduct, Supplier
        from storefront.stock_policy import repair_fixture_stock_policy
        supplier = Supplier.objects.get(identifier='default')
        supplier.stock_managed = False
        supplier.save()
        item = ShopProduct.objects.get(shop__identifier='default', product__sku='fuzcake-rose-nocturne')
        item.backorder_maximum = Decimal('4')
        item.save()
        self.assertFalse(repair_fixture_stock_policy(Shop.objects.get(identifier='default'), supplier))
        supplier.refresh_from_db()
        item.refresh_from_db()
        self.assertFalse(supplier.stock_managed)
        self.assertEqual(item.backorder_maximum, Decimal('4'))

    def test_saved_address_native_title_boundaries(self):
        """The pinned native form accepts 1/255 characters and rejects 0/256 server-side."""
        from shuup.front.apps.customer_information.forms import SavedAddressForm
        for size, valid in [(0, False), (1, True), (2, True), (254, True), (255, True), (256, False)]:
            form = SavedAddressForm(data={'title': 'W' * size, 'role': '1', 'status': '1'})
            self.assertEqual(form.is_valid(), valid, str(size))

    def test_extension_accounts_are_dedicated_and_active(self):
        """Fixture initialization creates both reviewed identities without privileged access."""
        from pathlib import Path
        from test_design.specification import load_specification
        model = load_specification(Path('tests/data/CUSTOMER_DESIGN.yaml'))
        for data in model['extensions']['accounts']:
            user = get_user_model().objects.get(username=data['username'])
            self.assertTrue(user.is_active)
            self.assertFalse(user.is_staff or user.is_superuser)
            self.assertEqual(user.email, data['email'])
            self.assertTrue(user.check_password(data['password']))

    def test_saved_address_cross_account_delete_preserves_owner_record(self):
        """Native edit/delete paths cannot expose or delete a different customer address."""
        from shuup.core.models import SavedAddress, SavedAddressRole, SavedAddressStatus
        from shuup.core.models import get_person_contact
        owner = get_user_model().objects.get(username='grace.mitchell')
        other = get_user_model().objects.get(username='henry.foster')
        address = MutableAddress.objects.create(name='Grace Mitchell', street='64 Willow Garden Lane', city='Moonberry', country='US')
        saved = SavedAddress.objects.create(owner=get_person_contact(owner), address=address, title='Willow Studio',
                                            role=SavedAddressRole.SHIPPING, status=SavedAddressStatus.ENABLED)
        self.client.force_login(other)
        response = self.client.get('/address-book/')
        self.assertNotContains(response, 'Willow Studio')
        response = self.client.get('/address-book/edit/' + str(saved.pk))
        self.assertNotContains(response, '64 Willow Garden Lane')
        response = self.client.get('/address-book/delete/' + str(saved.pk))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SavedAddress.objects.filter(pk=saved.pk, owner=get_person_contact(owner)).exists())

    def test_native_basket_uses_product_cards_with_mutation_controls(self):
        """Verify the server-rendered DOM that Browser uses for basket updates/deletion."""
        product=Product.objects.get(sku='fuzcake-rose-nocturne')
        self.client.force_login(self.customer)
        response=self.client.post('/basket/',{'command':'add','product_id':product.pk,'quantity':'2'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,200)
        response=self.client.get('/basket/')
        self.assertContains(response,'class="single-item"')
        self.assertContains(response,'class="product-details"')
        self.assertContains(response,'name="dq_')
        self.assertContains(response,'name="delete_')

    def test_invalid_basket_updates_render_native_warning_and_keep_quantity(self):
        """Real native min/stock/multiple errors warn and preserve two saved bottles."""
        import re
        product=Product.objects.get(sku='fuzcake-rose-nocturne')
        self.client.force_login(self.customer)
        self.client.post('/basket/',{'command':'add','product_id':product.pk,'quantity':'2'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        page=self.client.get('/basket/')
        key=re.search(r'name="(dq_[^"]+)"',page.content.decode()).group(1)
        for value in ['0','26','1.5']:
            response=self.client.post('/basket/',{'command':'update',key:value},follow=True)
            self.assertContains(response,'alert-warning')
            self.assertContains(response,'Warning!')
            self.assertEqual(response.wsgi_request.basket.get_product_ids_and_quantities()[product.pk],Decimal('2'))

    def test_whole_bottle_repair_rejects_fractions_using_native_quantity_errors(self):
        """The configured native purchase multiple makes update and add semantics agree."""
        from shuup.core.models import ShopProduct
        item=ShopProduct.objects.get(shop__identifier='default',product__sku='fuzcake-rose-nocturne')
        self.assertEqual(item.purchase_multiple,Decimal('1'))
        self.assertIn('invalid_purchase_multiple',[error.code for error in item.get_quantity_errors(Decimal('1.5'),False)])

    def test_display_fraction_is_rejected_before_native_rounding_to_existing_quantity(self):
        """The actual configured update class must warn instead of rounding 1.5 to existing 2."""
        import re
        from django.conf import settings
        self.assertEqual(settings.SHUUP_BASKET_UPDATE_METHODS_SPEC,'storefront.basket:WholeUnitBasketUpdateMethods')
        product=Product.objects.get(sku='fuzcake-rose-nocturne')
        self.client.force_login(self.customer)
        self.client.post('/basket/',{'command':'add','product_id':product.pk,'quantity':'2'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        page=self.client.get('/basket/')
        key=re.search(r'name="(dq_[^"]+)"',page.content.decode()).group(1)
        response=self.client.post('/basket/',{'command':'update',key:'1.5'},follow=True)
        self.assertContains(response,'Quantity must resolve to a whole number of items')
        self.assertContains(response,'alert-warning')
        self.assertEqual(response.wsgi_request.basket.get_product_ids_and_quantities()[product.pk],Decimal('2'))
