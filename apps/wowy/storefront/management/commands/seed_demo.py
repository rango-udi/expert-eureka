"""Map shared fuzcake references onto real Wowy models without importing upstream fixtures."""
from decimal import Decimal
import os
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from categories.models import Category
from core.models import SiteSettings
from products.models import Product, ProductImage
from users.models import Address
from fuzcake_data import asset_path, reference, validate


def account(role, staff=False, administrator=False):
    """Create configured local identities once; preserve saved passwords and privileges."""
    identity = reference("store")["roles"][role]
    user, created = get_user_model().objects.get_or_create(email=os.environ[role + "_EMAIL"], defaults={
        "name": identity["first_name"] + " " + identity["last_name"], "phone": identity["phone"],
        "is_staff": staff, "is_superuser": administrator})
    if created:
        user.set_password(os.environ[role + "_PASSWORD"])
        user.save()
    return user, created


class Command(BaseCommand):
    help = "Create missing Wowy catalogue and role accounts from fuzcake-data."

    @transaction.atomic
    def handle(self, *args, **options):
        """Seed stable SKUs and slugs; keep operator changes and all runtime orders intact."""
        validate("wowy")
        store = reference("store")
        address = store["addresses"][0]
        SiteSettings.objects.get_or_create(pk=1, defaults={"site_name": store["name"],
            "contact_email": store["support_email"], "contact_phone": store["phone"], "currency": "USD",
            "address": address["street"] + ", " + address["street2"] + ", " + address["city"]})
        account("ADMIN", staff=True, administrator=True)
        account("STAFF", staff=True)
        customer, created_customer = account("CUSTOMER")
        categories = {}
        records = reference("catalogue")
        for row in records["categories"]:
            category, created = Category.objects.get_or_create(slug="fuzcake-" + row["id"], defaults={"name": row["name"], "status": "active"})
            if created:
                product = next(p for p in records["products"] if p["category"] == row["id"])
                photograph = asset_path(product["image"])
                category.image.save(photograph.name, ContentFile(photograph.read_bytes()), save=True)
            categories[row["id"]] = category
        for row in records["products"]:
            product, created = Product.objects.get_or_create(sku=row["sku"], defaults={
                "slug": row["sku"], "name": row["name"], "brand": row["brand"],
                "description": row["description"], "additional_details": row["size"],
                "original_price": Decimal(row["price"]), "selling_price": Decimal(row["price"]),
                "category": categories[row["category"]], "stock": row["stock"],
                "stock_unit": Product.StockUnitChoices.UNIT, "top_featured": True, "is_active": True})
            if created:
                photograph = asset_path(row["image"])
                image = ProductImage(product=product, is_primary=True)
                image.image.save(photograph.name, ContentFile(photograph.read_bytes()), save=True)
        if created_customer:
            for row in store["addresses"]:
                if row["id"] not in ("customer-home", "customer-office"):
                    continue
                Address.objects.create(user=customer, phone=store["roles"]["CUSTOMER"]["phone"],
                    address=row["street"] + ", " + row["street2"], city=row["city"],
                    postal_code=row["postal_code"], is_default=row["id"] == "customer-home")
        self.stdout.write("Wowy store data is ready. Run cmdc urls --app wowy for storefront and administration links.")
