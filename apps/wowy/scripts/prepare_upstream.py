"""Fetch one verified Wowy revision inside Docker and retain only runtime source."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def git(root, *arguments):
    """Run Git without a shell and return metadata for the selected working tree."""
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True).strip()


def patch(path, old, new):
    """Apply a reviewed compatibility patch only if its exact upstream anchor is present."""
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError("The locked Wowy source differs at " + str(path) + ". Review source-lock.json before building.")
    path.write_text(text.replace(old, new), encoding="utf-8")


def prepare(destination):
    """Verify commit/tree IDs and exclude bundled databases, secrets, media and fixtures."""
    lock = json.loads(Path("/source-lock.json").read_text())
    with tempfile.TemporaryDirectory(prefix="wowy-source-") as temporary:
        root = Path(temporary)
        git(root, "init", "--quiet")
        git(root, "remote", "add", "origin", lock["repository"] + ".git")
        git(root, "-c", "protocol.file.allow=never", "fetch", "--depth=1", "origin", lock["commit"])
        git(root, "checkout", "--quiet", "--detach", "FETCH_HEAD")
        if git(root, "rev-parse", "HEAD") != lock["commit"] or git(root, "rev-parse", "HEAD^{tree}") != lock["tree"]:
            raise ValueError("Wowy source verification failed. No runtime source was copied.")
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("cart", "categories", "core", "offers", "orders", "products", "users", "utils", "wishlist", "templates", "static"):
            if any(p.is_symlink() for p in (root / name).rglob("*")):
                raise ValueError("The pinned runtime source contains an unexpected filesystem link.")
            shutil.copytree(root / name, destination / name, ignore=shutil.ignore_patterns("fixtures", "__pycache__", "*.pyc"))
        shutil.copyfile(root / "LICENSE", destination / "LICENSE")
    patch(destination / "core/models.py", '("BDT", "Bangladeshi Taka"),', '("USD", "US Dollar"), ("EUR", "Euro"), ("BDT", "Bangladeshi Taka"),')
    patch(destination / "core/models.py", 'default="BDT", choices=CURRENCY_CHOICES', 'default="USD", choices=CURRENCY_CHOICES')
    # The local root URL configuration does not import upstream Stripe checkout views.
    patch(destination / "users/views/admin_views.py", 'status="completed"', 'status="delivered"')
    patch(destination / "users/views/admin_views.py", 'Q(address__street_address__icontains=search_query)', 'Q(shipping_address__address__icontains=search_query)')
    patch(destination / "products/views.py", 'queryset = super().get_queryset()', 'queryset = super().get_queryset().filter(is_active=True, category__status="active")')
    patch(destination / "products/views.py", 'Product.objects.filter(category=self.category)', 'Product.objects.filter(category=self.category, is_active=True, category__status="active")')
    patch(destination / "products/views.py", 'model = Product\n    template_name = "products/detail.html"', 'model = Product\n    queryset = Product.objects.filter(is_active=True, category__status="active")\n    template_name = "products/detail.html"')
    patch(destination / "core/views.py", 'Product.objects.all()', 'Product.objects.filter(is_active=True, category__status="active")')
    patch(destination / "static/frontend/js/cart.js", "return '\u09f3' + parseFloat(price).toFixed(2);", "return (document.body.dataset.currency || 'USD') + ' ' + parseFloat(price).toFixed(2);")
    for path in (destination / "templates").rglob("*.html"):
        text = path.read_text(encoding="utf-8").replace("WOWY", "{{ settings.site_name }}").replace("\u09f3", "{{ settings.currency }} ")
        # Local notifications replace the external SweetAlert CDN dependency.
        text = text.replace('https://cdn.jsdelivr.net/npm/sweetalert2@11', '/static/wowy/notifications.js').replace('https://cdn.jsdelivr.net/npm/sweetalert2@10', '/static/wowy/notifications.js')
        text = text.replace("frontend/images/fav.png", "fuzcake/brands/fuzcake.svg")
        text = text.replace("frontend/images/logo.svg", "fuzcake/brands/fuzcake.svg").replace("frontend/images/dark-logo.svg", "fuzcake/brands/fuzcake.svg")
        text = text.replace("order.address.", "order.shipping_address.")
        text = text.replace("https://via.placeholder.com/150'", "/static/fuzcake/brands/fuzcake.svg'")
        if path.name in ("login.html", "signup.html") or path == destination / "templates/users/admin/base.html":
            text = text.replace("</head>", '<link rel="stylesheet" href="{% static \'fuzcake/storefront.css\' %}"><link rel="stylesheet" href="{% static \'wowy/adapter.css\' %}"></head>')
        path.write_text(text, encoding="utf-8")
    patch(destination / "templates/base.html", 'data-auth="{{ request.user.is_authenticated|lower }}"', 'data-auth="{{ request.user.is_authenticated|lower }}" data-currency="{{ settings.currency }}"')
    patch(destination / "templates/base.html", '{% block style %}{% endblock %}', '<link rel="stylesheet" href="{% static \'fuzcake/storefront.css\' %}"><link rel="stylesheet" href="{% static \'wowy/adapter.css\' %}">{% block style %}{% endblock %}')
    patch(destination / "static/frontend/js/cart.js", "https://via.placeholder.com/150x150?text=No+Image", "/static/fuzcake/brands/fuzcake.svg")
    patch(destination / "templates/users/dashboard/index.html", 'href="#" class="btn btn-sm btn-secondary"', 'href="{% url \'orders:success\' order.order_number %}" class="btn btn-sm btn-secondary"')
    patch(destination / "templates/users/admin/base.html", '<a class="dropdown-item admin-dropdown-item" href="{% url \'users:logout\' %}">Logout</a>', '<form action="{% url \'users:logout\' %}" method="post">{% csrf_token %}<button class="dropdown-item admin-dropdown-item" type="submit">Logout</button></form>')
    patch(destination / "users/views/admin_views.py", 'Category.objects.create(name=name, status=status, image=image)', 'Category.objects.create(name=name, slug=slugify(name), status=status, image=image)')
    patch(destination / "users/views/user_views.py", 'return Address.objects.filter(user=self.request.user)', 'return Address.objects.filter(user=self.request.user, shipping_orders__isnull=True)')
    patch(destination / "static/frontend/js/cart.js", "const quantityInput = this.closest('.product-item')?.querySelector('.qty.text');", "const quantityInput = this.closest('.product-item')?.querySelector('.qty.text') || (this.closest('.ordr-crt-share') ? document.querySelector('.qty-product .qty.text') : null);")
    patch(destination / "templates/base.html", '<script src="{% static \'frontend/js/cart.js\' %}"></script>', '<script src="{% static \'frontend/js/cart.js\' %}"></script><script src="{% static \'wowy/interactions.js\' %}"></script>')
    patch(destination / "users/views/user_views.py", 'address_count = Address.objects.filter(user=user).count()', 'address_count = Address.objects.filter(user=user, shipping_orders__isnull=True).count()')
    patch(destination / "products/views.py", 'from django.http import Http404, JsonResponse', 'from django.http import Http404, JsonResponse\nfrom django.shortcuts import get_object_or_404')
    patch(destination / "products/views.py", 'Category.objects.get(slug=self.kwargs["slug"])', 'get_object_or_404(Category, slug=self.kwargs["slug"], status="active")')
    patch(destination / "templates/users/dashboard/base.html", '<div class="img-add">\n                                <input type="file" id="file">\n                                <label for="file"><i class="uil uil-camera-plus"></i></label>\n                            </div>', '')
    patch(destination / "static/frontend/js/cart.js", 'function updateCartCount(count) {', 'function escapeCartText(value) { const node = document.createElement("span"); node.textContent = String(value); return node.innerHTML.replace(/"/g, "&quot;").replace(/\'/g, "&#39;"); }\nfunction updateCartCount(count) {')
    patch(destination / "static/frontend/js/cart.js", '${product.name}', '${escapeCartText(product.name)}')
    patch(destination / "users/models.py", '    def __str__(self):\n        return f"{self.name} - {self.email} - {self.phone}"', '    def get_full_name(self):\n        """Use the native single-name field in Django account administration."""\n        return self.name\n\n    def get_short_name(self):\n        """Provide a readable account label for the standard Django admin header."""\n        return self.name.split()[0] if self.name else self.email\n\n    def __str__(self):\n        return f"{self.name} - {self.email} - {self.phone}"')
    print("Verified Wowy source prepared: " + lock["commit"])


if __name__ == "__main__":
    try:
        prepare(Path(sys.argv[1]))
    except subprocess.CalledProcessError as error:
        print("ERROR: The pinned Wowy source could not be retrieved or verified. Check GitHub connectivity and source-lock.json, then retry setup --app wowy.", file=sys.stderr)
        raise SystemExit(error.returncode or 2)
    except (OSError, ValueError) as error:
        print("ERROR: Wowy source preparation stopped: " + str(error), file=sys.stderr)
        raise SystemExit(2)
