from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.stripe_config),
    path("create-checkout-session/", views.create_checkout_session),
    path("webhook", views.stripe_webhook),
    path("webhook/", views.stripe_webhook),
    path("create-invoice", views.create_invoice),
    path("get_customer_id", views.get_customer_id),
    path("create-price-item", views.create_price_item, name="create-price-item"),
    path("update-price-item", views.update_price_item, name="update-price-item"),
    path("delete-price-item", views.delete_price_item, name="delete-price-item"),
    path("get_price_item_by_name/<str:name>/", views.get_price_item_by_name, name="get_price_item_by_name"),
]
