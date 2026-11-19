"""Load immutable business reference records from one source outside templates."""
from fuzcake_data import reference


def storefront_context(request):
    """Provide shared identity and shop-scoped, publicly visible catalogue links."""
    shop = getattr(request, "shop", None)
    if shop is None:
        return {}
    context = {"fuzcake_store": reference("store"), "fuzcake_currency": shop.currency,
               "fuzcake_partners": reference("partners")}
    match = getattr(request, "resolver_match", None)
    if getattr(match, "view_name", None) != "shuup:index":
        return context
    # Only the landing-page family links need this query. Native catalogue plugins own products/pricing.
    from shuup.core.models import Category
    catalogue = reference("catalogue")
    context["fuzcake_categories"] = list(Category.objects.all_visible(
        shop=shop, customer=getattr(request, "customer", None)).filter(
            identifier__in=["fuzcake-" + category["id"] for category in catalogue["categories"]]
        ).prefetch_related("translations"))
    return context
