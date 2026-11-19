"""Record a real unpaid cash-on-delivery payment source without a payment gateway."""

from oscar.apps.checkout.views import PaymentDetailsView as OscarPaymentDetailsView
from oscar.core.loading import get_model


class PaymentDetailsView(OscarPaymentDetailsView):
    def handle_payment(self, order_number, total, **kwargs):
        """Attach an unpaid COD source to the order; allocate and debit no money."""
        SourceType = get_model("payment", "SourceType")
        Source = get_model("payment", "Source")
        source_type, _ = SourceType.objects.get_or_create(
            code="cash-on-delivery", defaults={"name": "Cash on delivery"}
        )
        source = Source(
            source_type=source_type,
            currency=total.currency,
            reference="COD-" + str(order_number),
        )
        self.add_payment_source(source)
