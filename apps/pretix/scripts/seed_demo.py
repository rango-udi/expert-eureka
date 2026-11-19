"""Run through `pretix shell`; create missing test fixtures without changing orders."""
import os
import sys
sys.path.insert(0, "/fuzcake-data")
from fuzcake_data import reference, validate
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django_scopes import scopes_disabled
from pretix.base.models import Event, Item, Organizer, Quota, Team, User, Voucher


def seed_data() -> None:
    """Create missing pretix test fixtures in one database transaction.

    Reads ADMIN_* and STAFF_* credentials from the container environment.
    Uses Django models with organizer scoping disabled only during initialization.
    Existing account passwords, event settings, orders, and used quotas are kept.
    Returns:
        None. Missing accounts, organizer, team, event, tickets, quotas, and voucher
        are persisted; database errors propagate to the management command.
    """
    validate("pretix")
    profile = reference("events")
    with scopes_disabled(), transaction.atomic():
        users = []
        for role, staff in (("ADMIN", True), ("STAFF", False)):
            email = os.environ[f"{role}_EMAIL"]
            user, created = User.objects.get_or_create(email=email, defaults={"is_staff": staff})
            if created:
                user.set_password(os.environ[f"{role}_PASSWORD"])
                user.save()
            users.append(user)
    
        organizer, _ = Organizer.objects.get_or_create(
            slug=profile["organizer"]["slug"], defaults={"name": {"en": profile["organizer"]["name"]}}
        )
        if str(organizer.name) == "Demo":
            organizer.name = {"en": profile["organizer"]["name"]}
            organizer.save()
        old_team = Team.objects.filter(organizer=organizer, name="Demo organizers").first()
        if old_team is not None:
            old_team.name = profile["team"]
            old_team.save()
        team, _ = Team.objects.get_or_create(
            organizer=organizer, name=profile["team"],
            defaults={"all_events": True, "all_event_permissions": True,
                      "all_organizer_permissions": True},
        )
        team.members.add(*users)
        event, created = Event.objects.get_or_create(
            organizer=organizer, slug=profile["event"]["slug"],
            defaults={
                "name": {"en": profile["event"]["name"]},
                "date_from": timezone.now() + timedelta(days=profile["event"]["starts_in_days"]),
                "date_to": timezone.now() + timedelta(days=profile["event"]["starts_in_days"] + profile["event"]["duration_days"]),
                "live": True, "testmode": False, "currency": os.environ.get("PRETIX_PRETIX_CURRENCY", profile["event"]["currency"]),
                "plugins": "pretix.plugins.banktransfer,pretix.plugins.ticketoutputpdf",
            },
        )
        if str(event.name) == "Demo Conference":
            event.name = {"en": profile["event"]["name"]}
            event.save()
        if created:
            for key, value in {
                "locales": ["en"], "locale": "en",
                "attendee_names_asked": False, "attendee_names_required": False,
                "payment_banktransfer__enabled": True,
                "payment_banktransfer_bank_details": {"en": profile["manual_payment_note"]},
                "ticketoutput_pdf__enabled": True,
                "max_items_per_order": 10,
                "redirect_to_checkout_directly": False,
            }.items():
                event.settings.set(key, value)
        for ticket in profile["tickets"]:
            name, price = ticket["name"], ticket["price"]
            item, _ = Item.objects.get_or_create(
                event=event, name={"en": name},
                defaults={"default_price": Decimal(price), "admission": True, "active": True},
            )
            quota, _ = Quota.objects.get_or_create(event=event, name=name, defaults={"size": ticket["quota"]})
            quota.items.add(item)
        Voucher.objects.get_or_create(
            event=event, code=profile["voucher"]["code"],
            defaults={"max_usages": profile["voucher"]["max_usages"], "price_mode": "percent", "value": Decimal(profile["voucher"]["percent"])},
        )


seed_data()
print("Event data is ready. Run cmdc urls --app pretix to open the ticket shop or administration page.")
