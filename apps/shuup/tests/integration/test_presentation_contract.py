"""Guard native commerce behavior while presentation and asset delivery evolve."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
from wsgiref.util import setup_testing_defaults
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from shuup.front.views.basket import BasketView
from shuup.front.views.category import AllCategoriesView, CategoryView
from shuup.front.views.product import ProductDetailView
from storefront.business_data import storefront_context
from storefront.theme import FuzcakeTheme


class PresentationContractTests(TestCase):
    def test_native_product_and_basket_routes_keep_original_views(self):
        """Do not replace catalogue, product or cart logic while restyling their links."""
        for name, arguments, expected in (
            ("all-categories", {}, AllCategoriesView),
            ("category", {"pk": 1, "slug": "floral"}, CategoryView),
            ("product", {"pk": 1, "slug": "rose-nocturne"}, ProductDetailView),
            ("basket", {}, BasketView),
        ):
            callback = resolve(reverse("shuup:" + name, kwargs=arguments)).func
            self.assertIs(callback.view_class, expected)

    def test_legacy_collection_view_uses_native_catalogue(self):
        """Keep old theme links usable without a separate product-list implementation."""
        theme = object.__new__(FuzcakeTheme)
        self.assertIs(theme.get_view("products"), AllCategoriesView)

    def test_non_home_context_does_not_query_the_catalogue(self):
        """A product, checkout or account page must not load landing-page product records."""
        for view in ("shuup:product", "shuup:checkout", "shuup:customer_edit", "fuzcake-wallet"):
            request = SimpleNamespace(shop=SimpleNamespace(currency="USD"),
                                      resolver_match=SimpleNamespace(view_name=view))
            with self.assertNumQueries(0):
                context = storefront_context(request)
            self.assertNotIn("fuzcake_categories", context)
            self.assertNotIn("fuzcake_cards", context)

    def test_new_media_is_served_without_caching_business_responses(self):
        """Keep live upload discovery while indexing only collected static at startup."""
        from storefront.wsgi import create_application

        def dynamic(environ, start_response):
            """Represent an uncached native business endpoint."""
            start_response("200 OK", [("Content-Type", "text/plain"), ("Cache-Control", "private, no-store")])
            return [b"native response"]

        def request(application, path):
            """Exercise the real WSGI wrappers without a socket or external server."""
            environ = {}
            setup_testing_defaults(environ)
            environ["PATH_INFO"] = path
            status = []

            def start_response(code, headers, exc_info=None):
                """Collect the response metadata from WhiteNoise or the native endpoint."""
                status.append((code, dict(headers)))

            response = application(environ, start_response)
            try:
                return status, b"".join(response)
            finally:
                if hasattr(response, "close"):
                    response.close()

        with tempfile.TemporaryDirectory() as folder:
            static = Path(folder) / "static"
            media = Path(folder) / "media"
            static.mkdir()
            media.mkdir()
            (static / "theme.css").write_text("body { color: black; }")
            with override_settings(STATIC_ROOT=str(static), MEDIA_ROOT=str(media)):
                application = create_application(dynamic)
                (media / "new-upload.txt").write_text("new upload")
                self.assertEqual(request(application, "/media/new-upload.txt")[1], b"new upload")
                self.assertIn(b"color: black", request(application, "/static/theme.css")[1])
                status, body = request(application, "/checkout/")
                self.assertEqual(body, b"native response")
                self.assertEqual(status[0][1]["Cache-Control"], "private, no-store")
