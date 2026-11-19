"""Use native Wowy navigation with isolated local cart and checkout routes."""
from django.contrib import admin
from django.urls import include, path
from orders.views import order_success
from storefront import views

cart_patterns = [path("api/list/", views.cart_list, name="cart"),
    path("api/add/", views.cart_add, name="add"), path("api/update/", views.cart_update, name="update"),
    path("checkout/", views.checkout_page, name="checkout"), path("api/place-order/", views.place_order, name="place_order"),
    path("create-payment-intent/", views.disabled_payment, name="create_payment_intent"),
    path("confirm-payment/", views.disabled_payment, name="confirm_payment")]
order_patterns = [path("success/<str:order_number>/", order_success, name="success"),
                  path("api/<int:order_id>/cancel/", views.cancel_order, name="cancel")]
urlpatterns = [
    path("_cmdc/health", views.health), path("super-admin/", admin.site.urls),
    path("users/api/address/delete/", views.delete_address),
    path("users/api/address/update/", views.update_address),
    path("cart/", include((cart_patterns, "cart"), namespace="cart")),
    path("orders/", include((order_patterns, "orders"), namespace="orders")),
    path("", include("core.urls")), path("", include("categories.urls")),
    path("users/", include("users.urls")), path("products/", include("products.urls")),
    path("wishlist/", include("wishlist.urls")), path("offers/", include("offers.urls")),
]
