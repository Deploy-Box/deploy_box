from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.stripe_config),
    path("create-checkout-session/", views.create_checkout_session),
    path("create-payment-method/", views.create_stripe_user),
    path("create-subscription/", views.create_subscription),
    path("create-intent/", views.create_intent),
    path("save-payment-method/", views.save_payment_method),
    path("webhook", views.stripe_webhook),
    path("webhook/", views.stripe_webhook),
    path("create-invoice/", views.create_invoice),
]
