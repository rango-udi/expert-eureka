"""Create a coherent fragrance catalogue while preserving operator-owned data."""
from decimal import Decimal
import os
import re
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from filer.models.imagemodels import Image
from shuup import configuration
from shuup.admin.utils.permissions import set_permissions_for_group
from shuup.core.models import (
    Category, CategoryStatus, CustomCarrier, CustomPaymentProcessor,
    FixedCostBehaviorComponent, Manufacturer, MutableAddress, PaymentMethod, PersonContact, Product,
    ProductMedia, ProductMediaKind, ProductType, SalesUnit, ShippingMethod,
    Shop, ShopProduct, ShopProductVisibility, Supplier, SupplierModule, TaxClass,
)
from shuup.simple_supplier.models import StockAdjustment
from shuup.simple_supplier.module import SimpleSupplierModule
from shuup.xtheme import get_current_theme, set_current_theme
from fuzcake_data import asset_path, reference, validate
from storefront.models import WalletMovement
from storefront.stock_policy import repair_fixture_stock_policy, repair_fixture_quantity_policy


def seed_customer_addresses(user, shop):
    """Fill missing native defaults with independent billing and shipping addresses."""
    store = reference("store")
    identity = store["roles"]["CUSTOMER"]
    contact, _ = PersonContact.objects.get_or_create(user=user, defaults={
        "first_name": user.first_name, "last_name": user.last_name,
        "email": user.email, "phone": identity["phone"], "registration_shop": shop})
    missing = []
    for field, value in (("first_name", user.first_name), ("last_name", user.last_name),
                         ("email", user.email), ("phone", identity["phone"])):
        if not getattr(contact, field) and value:
            setattr(contact, field, value)
            missing.append(field)
    if missing:
        contact.save(update_fields=missing)
    contact.shops.add(shop)
    addresses = {item["id"]: item for item in store["addresses"]}
    for kind in ("billing", "shipping"):
        field = "default_" + kind + "_address"
        if getattr(contact, field + "_id"):
            continue
        record = addresses[identity[kind + "_address"]]
        data = {key: value for key, value in record.items()
                if key in ("name", "street", "street2", "city", "region", "postal_code", "country")}
        data.update(email=contact.email, phone=contact.phone)
        setattr(contact, field, MutableAddress.objects.create(**data))
        contact.save(update_fields=[field])


def seed_coupon(shop):
    """Create a native coupon once; preserve administrator edits and usage history."""
    from shuup.campaigns.models import BasketCampaign, Coupon
    from shuup.campaigns.models.basket_effects import BasketDiscountPercentage

    offer = reference("store")["welcome_offer"]
    code = os.environ.get("COUPON_CODE", offer["code"]).strip()
    if code and not re.fullmatch(r"[A-Za-z0-9_-]{1,12}", code):
        raise CommandError("COUPON_CODE must contain 1..12 ASCII letters, digits, underscores or hyphens; leave blank to skip coupon creation.")
    if not code or BasketCampaign.objects.filter(identifier=offer["id"]).exists():
        return
    if Coupon.objects.filter(code__iexact=code).exists():
        raise CommandError("COUPON_CODE is already used by another coupon. Choose a unique code in .env or leave it blank; existing campaigns were preserved.")
    coupon = Coupon.objects.create(shop=shop, code=code, active=True)
    campaign = BasketCampaign.objects.create(shop=shop, identifier=offer["id"],
        name=offer["name"], public_name=offer["name"], basket_line_text=offer["name"],
        coupon=coupon, active=True)
    BasketDiscountPercentage.objects.create(campaign=campaign,
        discount_percentage=Decimal(offer["percentage"]))


def seed_registration_notification(shop):
    """Provide the missing native activation mail template without bypassing activation.

    Any existing registration script, even disabled, belongs to the operator and
    is preserved. The browser suite reads the delivered local email, never the
    database activation key. This makes a fresh demo usable for registration.
    """
    from shuup.front.apps.registration.notify_events import RegistrationReceived, RegistrationReceivedEmailScriptTemplate
    from shuup.notify.models import Script

    if Script.objects.filter(shop=shop, event_identifier=RegistrationReceived.identifier).exists():
        return
    template = RegistrationReceivedEmailScriptTemplate()
    form = template.get_form(data={
        "base-send_to": "customer", "base-recipient": "",
        "en-subject": "Activate your fuzcake account",
        "en-body": '<p>Welcome to fuzcake.</p><p><a href="{{ activation_url }}">Activate your account</a></p>'})
    if not form.is_valid():
        raise CommandError("The native registration email template is invalid.")
    script = template.create_script(shop, form)
    script.template = template.identifier
    script.save(update_fields=["template"])


def create_account(role, staff=False, superuser=False):
    """Set identity and password only at first creation; preserve existing access."""
    email = os.environ[role + "_EMAIL"]
    identity = reference("store")["roles"][role]
    user, created = get_user_model().objects.get_or_create(username=email, defaults={
        "email": email, "is_staff": staff, "is_superuser": superuser,
        "first_name": identity["first_name"], "last_name": identity["last_name"]})
    if created:
        user.set_password(os.environ[role + "_PASSWORD"])
        user.save()
    return user


def rename_legacy(instance, field, old_names, replacement):
    """Migrate only exact old scaffold labels; retain every operator customization."""
    if getattr(instance, field) in old_names:
        setattr(instance, field, replacement)
        instance.save()


def create_manual_service(model, provider_model, shop, tax_class, identifier, name, fee="0.00"):
    """Create one manual local checkout service; never replace existing prices."""
    if model.objects.filter(identifier=identifier).exists():
        return
    provider, _ = provider_model.objects.get_or_create(identifier=identifier, defaults={"name": name})
    service = provider.create_service(None, identifier=identifier, shop=shop,
                                     enabled=True, name=name, tax_class=tax_class)
    if Decimal(fee):
        service.behavior_components.add(FixedCostBehaviorComponent.objects.create(price_value=Decimal(fee)))


def attach_photograph(product, shop, record):
    """Attach the supplied original only when the product has no operator image."""
    if product.primary_image_id:
        return
    identifier = record["sku"] + "-photo"
    media = ProductMedia.objects.filter(identifier=identifier).first()
    if media is None:
        asset = asset_path(record["image"])
        image = Image(name=record["name"], original_filename=asset.name)
        image.file.save(asset.name, ContentFile(asset.read_bytes()), save=True)
        media = ProductMedia.objects.create(identifier=identifier, product=product,
                 kind=ProductMediaKind.IMAGE, file=image, title=record["name"], public=True)
        media.shops.add(shop)
    product.primary_image = media
    product.save()


class Command(BaseCommand):
    help = "Create missing fuzcake catalogue, local accounts and wallet reference history."

    @transaction.atomic
    def handle(self, *args, **options):
        """Seed stable IDs once; repeated setup preserves stock, themes and transactions."""
        # The upstream initializer resets the theme, so use it only for an empty store.
        validate("shuup")
        if not Shop.objects.exists():
            call_command("shuup_init", verbosity=0)
        shop = Shop.objects.get(identifier="default")
        if shop.currency not in ("USD", "EUR"):
            raise CommandError("The fragrance seed supports USD or EUR stores. Keep this database unchanged and adapt the reference currency before initialization.")
        rename_legacy(shop, "name", ("Default Shop", "Store"), "fuzcake Fragrance House")
        rename_legacy(shop, "public_name", ("Default Shop", "Store"), "fuzcake")
        if not shop.contact_address_id:
            address = {k: v for k, v in reference("store")["addresses"][0].items()
                       if k in ("name", "street", "street2", "city", "region", "postal_code", "country")}
            shop.contact_address = MutableAddress.objects.create(**address)
            shop.save()
        admin = create_account("ADMIN", staff=True, superuser=True)
        customer = create_account("CUSTOMER")
        seed_customer_addresses(customer, shop)
        seed_coupon(shop)
        seed_registration_notification(shop)
        staff = create_account("STAFF", staff=True)
        group = Group.objects.filter(name="Fixture shop dashboard").first()
        if group is not None:
            group.name = "Boutique operations"
            group.save()
        else:
            group, created = Group.objects.get_or_create(name="Boutique operations")
            if created:
                set_permissions_for_group(group.pk, ("dashboard",))
        staff.groups.add(group)
        shop.staff_members.add(staff, admin)
        tax_class, _ = TaxClass.objects.get_or_create(identifier="fixture-standard", defaults={"name": "Standard"})
        supplier = Supplier.objects.get(identifier="default")
        rename_legacy(supplier, "name", ("Default Supplier",), "fuzcake Fragrance Supply")
        supplier.shops.add(shop)
        module, _ = SupplierModule.objects.get_or_create(module_identifier="simple_supplier")
        supplier.supplier_modules.add(module)
        product_type = ProductType.objects.get(identifier="default")
        rename_legacy(product_type, "name", ("Standard Product", "Default Product Type"), "Fragrance & personal care")
        unit = SalesUnit.objects.get(identifier="pcs")
        categories = {}
        for record in reference("catalogue")["categories"]:
            category, _ = Category.objects.get_or_create(identifier="fuzcake-" + record["id"],
                defaults={"name": record["name"], "status": CategoryStatus.VISIBLE})
            category.shops.add(shop)
            categories[record["id"]] = category
        for record in reference("catalogue")["products"]:
            maker, _ = Manufacturer.objects.get_or_create(
                identifier="fuzcake-maker-" + slugify(record["brand"]), defaults={"name": record["brand"]})
            maker.shops.add(shop)
            product, created = Product.objects.get_or_create(sku=record["sku"], defaults={
                "name": record["name"], "description": record["description"] + " " + record["size"] + ".",
                "short_description": record["description"], "manufacturer": maker,
                "type": product_type, "sales_unit": unit, "tax_class": tax_class})
            if created:
                item = ShopProduct.objects.create(shop=shop, product=product,
                    default_price_value=Decimal(record["price"]),
                    visibility=ShopProductVisibility.ALWAYS_VISIBLE, purchasable=True,
                    primary_category=categories[record["category"]], backorder_maximum=Decimal("0"), purchase_multiple=Decimal("1"))
                item.suppliers.add(supplier)
                item.categories.add(categories[record["category"]])
                if not StockAdjustment.objects.filter(product=product, supplier=supplier).exists():
                    SimpleSupplierModule(supplier, {}).adjust_stock(product.pk, record["stock"], created_by=admin)
                attach_photograph(product, shop, record)
        # Existing backpack/mug/notebook records and their order links remain intact.
        if repair_fixture_quantity_policy(shop, supplier):
            self.stdout.write("Native whole-bottle purchase multiples enabled; stock quantities and transactions were preserved.")
        if repair_fixture_stock_policy(shop, supplier):
            self.stdout.write("Finite stock checks enabled for fuzcake catalogue products; existing stock quantities and transactions were preserved.")
        for carrier in reference("partners")["carriers"]:
            create_manual_service(ShippingMethod, CustomCarrier, shop, tax_class,
                carrier["id"], carrier["name"] + " - " + carrier["service"], carrier["fee"])
        create_manual_service(PaymentMethod, CustomPaymentProcessor, shop, tax_class,
                              "fixture-payment", "Pay on delivery")
        for record in reference("wallet")["ledger"]:
            defaults = {k: record[k] for k in ("kind", "amount_minor", "status", "description", "method")}
            defaults.update(owner=customer, currency=shop.currency, occurred_at=parse_datetime(record["occurred_at"]))
            WalletMovement.objects.get_or_create(reference=record["reference"], defaults=defaults)
        theme = get_current_theme(shop)
        if theme is None or theme.identifier == "shuup.themes.classic_gray":
            set_current_theme("storefront.fuzcake", shop)
        if configuration.get(shop, "setup_wizard_complete") is None:
            configuration.set(shop, "setup_wizard_complete", True)
        call_command("seed_customer_tests")
        self.stdout.write("fuzcake store data is ready. Run cmdc urls --app shuup for storefront and administration links.")
