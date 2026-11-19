"""Reproduce native checkout session persistence in Django's isolated database."""
from decimal import Decimal
from types import SimpleNamespace
from django.contrib.sessions.serializers import JSONSerializer
from django.test import TestCase
from shuup.core.models import MutableAddress, CompanyContact
from shuup.front.checkout._storage import CheckoutPhaseStorage
from storefront.session_serializer import CheckoutJSONSerializer


class CheckoutSessionTests(TestCase):
    """Exercise the exact native storage contract used after Continue."""

    def test_plain_json_cannot_store_the_native_address(self):
        """Document the adapter incompatibility independently of the unknown user traceback."""
        with self.assertRaises(TypeError):
            JSONSerializer().dumps({"checkout_addresses:billing": MutableAddress(street="42 Fuzzy Future Street")})

    def test_native_phase_storage_round_trips_both_addresses(self):
        """Signed database sessions must restore unsaved native address objects."""
        session = self.client.session
        storage = CheckoutPhaseStorage(SimpleNamespace(session=session), "addresses")
        for kind in ("billing", "shipping"):
            storage[kind] = MutableAddress(name="Mira Solen", street="42 Fuzzy Future Street",
                city="Moonberry", country="US", longitude=Decimal("1.250000"))
        session.save()
        restored = self.client.session
        for kind in ("billing", "shipping"):
            address = restored["checkout_addresses:" + kind]
            self.assertIsInstance(address, MutableAddress)
            self.assertIsNone(address.pk)
            self.assertEqual(address.country.code, "US")
            self.assertEqual(address.longitude, Decimal("1.250000"))

    def test_company_and_legacy_json_remain_compatible(self):
        """Keep existing login/cart dictionaries and native guest-company form values."""
        serializer = CheckoutJSONSerializer()
        legacy = {"_auth_user_id": "7", "cart": [1, 2], "token": "local-token"}
        self.assertEqual(serializer.loads(JSONSerializer().dumps(legacy)), legacy)
        company = CompanyContact(name="Moonberry Studio", tax_number="LOCAL-COMPANY")
        self.assertEqual(serializer.loads(serializer.dumps(company)).name, company.name)

    def test_unknown_types_and_primary_keys_are_not_deserialized(self):
        """Session tags cannot import arbitrary classes or restore a persisted model key."""
        serializer = CheckoutJSONSerializer()
        for value in (b'{"$fuzcake_checkout":"address-v1","fields":{"id":1}}',
                      b'{"$fuzcake_checkout":"arbitrary.module.Class","fields":{}}'):
            with self.assertRaises(ValueError):
                serializer.loads(value)
