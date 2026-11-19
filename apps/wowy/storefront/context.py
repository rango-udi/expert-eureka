"""Keep Wowy templates connected to the shared reference registry."""
from fuzcake_data import reference
from core.models import SiteSettings
from categories.models import Category


def business_context(request):
    """Provide immutable branding and delivery records; native products remain database-owned."""
    return {"settings": SiteSettings.load(), "categories": Category.objects.filter(status="active"), "fuzcake_store": reference("store"), "fuzcake_partners": reference("partners")}
