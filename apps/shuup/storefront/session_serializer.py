"""Store native checkout form objects as allowlisted JSON without executable pickle."""
import json
from decimal import Decimal
from shuup.core.models import CompanyContact, MutableAddress


def encode_checkout_value(value):
    """Encode only native checkout addresses and the two company form fields."""
    if isinstance(value, MutableAddress):
        fields = {}
        for field in value._meta.concrete_fields:
            if field.primary_key or field.is_relation:
                continue
            item = getattr(value, field.attname)
            if field.name == "country":
                item = item.code
            if isinstance(item, Decimal):
                item = str(item)
            fields[field.name] = item
        return {"$fuzcake_checkout": "address-v1", "fields": fields}
    if isinstance(value, CompanyContact):
        return {"$fuzcake_checkout": "company-v1", "fields": {
            "name": value.name, "tax_number": value.tax_number}}
    raise TypeError("Unsupported checkout session value: " + type(value).__name__)


def decode_checkout_value(value):
    """Recreate unsaved allowlisted form objects; never import a payload class or save data."""
    if set(value) != {"$fuzcake_checkout", "fields"}:
        return value
    kinds = {"address-v1": MutableAddress, "company-v1": CompanyContact}
    model = kinds.get(value["$fuzcake_checkout"])
    if model is None or not isinstance(value["fields"], dict):
        raise ValueError("Unknown checkout session representation.")
    allowed = {field.name for field in model._meta.concrete_fields
               if not field.primary_key and not field.is_relation}
    if model is CompanyContact:
        allowed = {"name", "tax_number"}
    if not set(value["fields"]) <= allowed:
        raise ValueError("Unexpected checkout session fields.")
    fields = {}
    for name, item in value["fields"].items():
        if item is not None and not isinstance(item, (str, int, float, bool)):
            raise ValueError("Checkout session fields must be scalar values.")
        fields[name] = model._meta.get_field(name).to_python(item)
    return model(**fields)


class CheckoutJSONSerializer:
    """Implement Django's byte-oriented serializer contract and retain legacy plain JSON."""

    def dumps(self, value):
        """Return JSON bytes, converting only the checkout objects supported above."""
        return json.dumps(value, default=encode_checkout_value, separators=(",", ":")).encode("utf-8")

    def loads(self, value):
        """Read existing JSON sessions and reconstruct explicit checkout tags."""
        return json.loads(value.decode("utf-8"), object_hook=decode_checkout_value)
