"""Serve local reference information and a deliberately isolated wallet simulation."""
from decimal import Decimal, InvalidOperation
from uuid import uuid4
import os
import re
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from storefront.business_data import reference
from storefront.models import WalletMovement


def information(request, section):
    """Render one allowlisted public business page using the shared reference source."""
    return render(request, "fuzcake/information.jinja", {"section": section,
                  "reference_orders": reference("wallet")["orders"]})


def funding_amount(raw):
    """Validate exact cents without rounding, infinities or scientific notation."""
    if not isinstance(raw, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", raw):
        raise ValueError("Enter an amount from 5.00 to 500.00, with at most two decimal places.")
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError):
        raise ValueError("Enter an amount from 5.00 to 500.00, with at most two decimal places.")
    if not value.is_finite() or value < 5 or value > 500 or value.as_tuple().exponent < -2:
        raise ValueError("Enter an amount from 5.00 to 500.00, with at most two decimal places.")
    return int(value * 100)


@login_required(login_url="/login/")
@require_http_methods(["GET", "POST"])
def wallet(request):
    """Show only the signed-in ledger and post idempotent, local simulation credits."""
    methods = reference("partners")["funding_methods"] if request.user.username == os.environ.get("CUSTOMER_EMAIL") else []
    movements = WalletMovement.objects.filter(owner=request.user)
    opening = movements.order_by("occurred_at", "pk").first()
    currency = opening.currency if opening else request.shop.currency
    movements = movements.filter(currency=currency)
    if request.method == "POST":
        token = request.POST.get("token", "")
        if not token or token != request.session.get("fuzcake_funding_token"):
            return HttpResponseBadRequest("This funding form has expired. Reload Wallet and try again.")
        method = request.POST.get("method", "")
        if method not in {m["id"] for m in methods}:
            return HttpResponseBadRequest("Choose a funding method linked to this wallet.")
        try:
            amount = funding_amount(request.POST.get("amount", ""))
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("fuzcake-wallet")
        with transaction.atomic():
            WalletMovement.objects.get_or_create(reference="FW-LOCAL-" + token, defaults={
                "owner": request.user, "kind": "topup", "amount_minor": amount,
                "currency": currency, "status": "posted", "method": method,
                "description": "Local wallet funding", "occurred_at": timezone.now()})
        request.session.pop("fuzcake_funding_token", None)
        messages.success(request, "Wallet updated. This is a local simulation; no funds were transferred.")
        return redirect("fuzcake-wallet")
    total = movements.filter(status="posted").aggregate(total=Sum("amount_minor"))["total"] or 0
    entries = [{"movement": m, "amount": Decimal(m.amount_minor) / 100} for m in movements[:100]]
    token = request.session.setdefault("fuzcake_funding_token", uuid4().hex)
    return render(request, "fuzcake/wallet.jinja", {"wallet_balance": Decimal(total) / 100,
                  "wallet_entries": entries, "wallet_currency": currency, "funding_methods": methods, "funding_token": token})
