"""Seed real Oscar models without resetting existing account passwords or stock."""

from decimal import Decimal
from pathlib import Path
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from oscar.core.loading import get_model
from PIL import Image
from django.db import transaction
from fuzcake_data import asset_path, reference, validate




class Command(BaseCommand):
    help = "Create missing local accounts, products, stock, countries and an OSCAR10 voucher."

    @transaction.atomic
    def handle(self, *args, **options):
        """Create missing fixtures through Oscar models; preserve existing account and stock data."""
        validate("oscar")
        users = get_user_model()
        created_accounts = {}
        for prefix, staff in [("ADMIN", True), ("CUSTOMER", False), ("SELLER", False)]:
            email = os.environ[prefix + "_EMAIL"]
            identity = reference("store")["roles"]["STAFF" if prefix == "SELLER" else prefix]
            user, created = users.objects.get_or_create(
                username=email,
                defaults={
                    "email": email,
                    "first_name": identity["first_name"],
                    "last_name": identity["last_name"],
                    "is_staff": staff,
                    "is_superuser": prefix == "ADMIN",
                },
            )
            created_accounts[prefix] = created
            if created:
                user.set_password(os.environ[prefix + "_PASSWORD"])
                user.save()
            if prefix == "SELLER" and created:
                from django.contrib.auth.models import Permission

                user.is_staff = False
                user.is_superuser = False
                user.save(update_fields=["is_staff", "is_superuser"])
                user.user_permissions.add(
                    Permission.objects.get(
                        content_type__app_label="partner", codename="dashboard_access"
                    )
                )
        site, _ = Site.objects.get_or_create(pk=1, defaults={"domain": "localhost", "name": "fuzcake"})
        if site.name in ("example.com", "Oscar Market"):
            site.name = "fuzcake"
            if site.domain == "example.com":
                site.domain = "localhost"
            site.save()
        Country = get_model("address", "Country")
        for code, name in [("US", "United States"), ("GB", "United Kingdom")]:
            Country.objects.get_or_create(
                iso_3166_1_a2=code,
                defaults={
                    "name": name,
                    "printable_name": name,
                    "is_shipping_country": True,
                },
            )
        ProductClass = get_model("catalogue", "ProductClass")
        Category = get_model("catalogue", "Category")
        Product = get_model("catalogue", "Product")
        ProductCategory = get_model("catalogue", "ProductCategory")
        ProductImage = get_model("catalogue", "ProductImage")
        StockRecord = get_model("partner", "StockRecord")
        Partner = get_model("partner", "Partner")
        product_class, _ = ProductClass.objects.get_or_create(
            name="Fragrance", defaults={"requires_shipping": True, "track_stock": True})
        categories = {}
        for record in reference("catalogue")["categories"]:
            slug = "fuzcake-" + record["id"]
            category = Category.objects.filter(slug=slug).first()
            if category is None:
                category = Category.add_root(name=record["name"], slug=slug)
            categories[record["id"]] = category
        partner, created_partner = Partner.objects.get_or_create(
            code="oscar-market", defaults={"name": "fuzcake Fragrance Supply"})
        if partner.name == "Oscar Market":
            partner.name = "fuzcake Fragrance Supply"
            partner.save()
        if created_partner or created_accounts["SELLER"]:
            partner.users.add(users.objects.get(username=os.environ["SELLER_EMAIL"]))
        for record in reference("catalogue")["products"]:
            product, created_product = Product.objects.get_or_create(upc=record["sku"], defaults={
                "title": record["name"], "description": record["description"] + " " + record["size"],
                "product_class": product_class})
            if created_product:
                ProductCategory.objects.create(product=product, category=categories[record["category"]])
                StockRecord.objects.create(product=product, partner=partner, partner_sku=record["sku"],
                    price_currency="USD", price=Decimal(record["price"]), num_in_stock=record["stock"])
                picture = ProductImage(product=product, caption=record["name"])
                original = asset_path(record["image"])
                picture.original.save(original.name, ContentFile(original.read_bytes()), save=True)
        Range = get_model("offer", "Range")
        Condition = get_model("offer", "Condition")
        Benefit = get_model("offer", "Benefit")
        Offer = get_model("offer", "ConditionalOffer")
        Voucher = get_model("voucher", "Voucher")
        from django.utils import timezone
        from datetime import timedelta

        Range.objects.filter(name="Demo catalogue").update(name="Everyday collection")
        if not Voucher.objects.filter(code="OSCAR10").exists():
            product_range = Range.objects.create(
                name="Everyday collection", includes_all_products=True
            )
            condition = Condition.objects.create(
                range=product_range, type=Condition.COUNT, value=1
            )
            benefit = Benefit.objects.create(
                range=product_range, type=Benefit.PERCENTAGE, value=10
            )
            offer = Offer.objects.create(
                name="OSCAR10 discount",
                offer_type=Offer.VOUCHER,
                condition=condition,
                benefit=benefit,
            )
            voucher = Voucher.objects.create(
                name="Ten percent discount",
                code="OSCAR10",
                start_datetime=timezone.now() - timedelta(days=1),
                end_datetime=timezone.now() + timedelta(days=3650),
            )
            voucher.offers.add(offer)
        missing = Path(settings.MEDIA_ROOT) / "image_not_found.jpg"
        if not missing.exists():
            Image.new("RGB", (200, 200), "#e5e7eb").save(missing)
        self.stdout.write(
            self.style.SUCCESS(
                "Oscar fixtures are ready. Existing account passwords and stock were preserved."
            )
        )
