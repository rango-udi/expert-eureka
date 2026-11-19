"""Read shared, versioned fixture references without an application dependency."""
from copy import deepcopy
from functools import lru_cache
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("store", "catalogue", "partners", "wallet", "events", "app-profiles", "asset-provenance")


@lru_cache(maxsize=8)
def _read(name):
    """Cache one allowlisted reference document; never accept an arbitrary file path."""
    if name not in DOCUMENTS:
        raise ValueError("Unknown fuzcake reference. Use a document registered in fuzcake-data.")
    try:
        path = ROOT / "records" / (name + ".json")
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("Shared reference documents must not be filesystem links.")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("The shared fuzcake data is missing or invalid. Extract the complete source package and retry.") from error


def reference(name):
    """Return an independent copy so one adapter cannot mutate another reader's records."""
    return deepcopy(_read(name))


def asset_path(relative):
    """Resolve an existing shared asset and reject traversal and filesystem links."""
    base = ROOT / "assets"
    path = base / relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != base.parent):
        raise ValueError("Shared fixture assets must not be filesystem links.")
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError as error:
        raise ValueError("Fixture assets must remain inside fuzcake-data/assets.") from error
    if not path.is_file():
        raise ValueError("A fixture asset is missing: " + relative + ". Extract the complete source package.")
    return path


def validate(app):
    """Check the declared consumer, references, cents and original asset hashes before seeding."""
    profiles = reference("app-profiles")
    if profiles.get("schema_version") != 1:
        raise ValueError("The shared data schema is unsupported. Use matching source and adapter versions.")
    if app not in profiles["apps"]:
        raise ValueError("The selected application has no fuzcake data profile.")
    catalogue = reference("catalogue")
    partners = reference("partners")
    wallet = reference("wallet")
    store = reference("store")
    address_ids = {item["id"] for item in store["addresses"]}
    if any(store["roles"]["CUSTOMER"].get(kind + "_address") not in address_ids for kind in ("billing", "shipping")):
        raise ValueError("Customer billing and shipping defaults must reference existing shared addresses.")
    offer = store["welcome_offer"]
    if not Decimal("0") < Decimal(offer["percentage"]) < Decimal("1"):
        raise ValueError("The welcome offer must use a percentage strictly between zero and one.")
    products = {p["sku"]: p for p in catalogue["products"]}
    if len(products) != len(catalogue["products"]):
        raise ValueError("The shared catalogue contains duplicate product SKUs.")
    categories = {c["id"] for c in catalogue["categories"]}
    brands = {b["id"] for b in partners["banks"] + partners["wallets"]}
    methods = {m["id"] for m in partners["funding_methods"]}
    for records, key in ((catalogue["categories"], "id"), (partners["banks"] + partners["wallets"], "id"),
                         (partners["carriers"], "id"), (partners["funding_methods"], "id"),
                         (store["addresses"], "id"), (wallet["ledger"], "reference")):
        if len({r[key] for r in records}) != len(records):
            raise ValueError("Shared data contains a duplicate " + key + ". Keep stable identifiers unique.")
    for product in products.values():
        money_minor(product["price"])
        if type(product["stock"]) is not int or product["stock"] < 0:
            raise ValueError("Initial product stock must be a nonnegative whole number.")
    for method in partners["funding_methods"]:
        if any(key in method for key in ("pan", "cvv", "iban", "account_number")):
            raise ValueError("Use masked card digits and local tokens in shared payment references.")
    if any(p["category"] not in categories for p in products.values()):
        raise ValueError("A product references an unknown fragrance family.")
    if any(m["brand"] not in brands for m in partners["funding_methods"]):
        raise ValueError("A funding method references an unknown partner.")
    if any(m["method"] not in methods for m in wallet["ledger"]):
        raise ValueError("A wallet movement references an unknown funding method.")
    if any(type(m["amount_minor"]) is not int or m["status"] not in ("posted", "pending", "failed") for m in wallet["ledger"]):
        raise ValueError("Wallet movements require integer cents and a known posting status.")
    if sum(m["amount_minor"] for m in wallet["ledger"] if m["status"] == "posted") != wallet["expected_balance_minor"]:
        raise ValueError("The opening wallet ledger does not reconcile. Correct fuzcake-data before setup.")
    carriers = {c["id"]: c for c in partners["carriers"]}
    addresses = {a["id"] for a in store["addresses"]}
    for order in wallet["orders"]:
        if order["sku"] not in products or order["carrier"] not in carriers or order["address"] not in addresses:
            raise ValueError("A reference order points to an unknown product, carrier or address.")
        if type(order["quantity"]) is not int or order["quantity"] < 1:
            raise ValueError("Reference order quantities must be positive whole numbers.")
        goods = money_minor(products[order["sku"]]["price"]) * order["quantity"]
        fee = money_minor(carriers[order["carrier"]]["fee"])
        if (goods, fee, goods + fee) != (order["items_minor"], order["shipping_minor"], order["total_minor"]):
            raise ValueError("A reference order does not reconcile its product price, delivery fee and total.")
        times = [event["at"] for event in order["events"]]
        if times != sorted(times):
            raise ValueError("Reference shipment events must follow chronological order.")
    manifest = reference("asset-provenance")
    if {p["image"] for p in products.values()} != {a["asset"] for a in manifest}:
        raise ValueError("The product photograph manifest must cover the shared catalogue exactly.")
    for asset in manifest:
        digest = hashlib.sha256()
        with asset_path(asset["asset"]).open("rb") as stream:
            for chunk in iter(lambda: stream.read(65536), b""):
                digest.update(chunk)
        if digest.hexdigest() != asset["sha256"]:
            raise ValueError("A shared product photograph differs from its recorded original: " + asset["asset"])
    for partner in partners["banks"] + partners["wallets"] + partners["carriers"]:
        asset_path(partner["logo"])


def money_minor(value):
    """Validate reference money as finite nonnegative exact cents, without rounding."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Reference prices must be finite decimal amounts.") from error
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Reference prices require nonnegative amounts with at most two decimal places.")
    return int(amount * 100)
