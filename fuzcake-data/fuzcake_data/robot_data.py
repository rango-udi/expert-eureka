"""Expose shared fixture values as Robot keywords without importing any application."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fuzcake_data import reference


def get_shipping_address():
    """Return the customer home address with the common fictional account identity."""
    store = reference("store")
    address = next(a for a in store["addresses"] if a["id"] == "customer-home")
    identity = store["roles"]["CUSTOMER"]
    return {**address, "first_name": identity["first_name"], "last_name": identity["last_name"], "phone": identity["phone"]}
