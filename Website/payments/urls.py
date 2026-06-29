from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.stripe_config, name="stripe_config"),
    path("checkout/create/<str:org_id>/", views.create_checkout_session, name="checkout_create"),
    path("save-payment-method/", views.save_stripe_payment_method, name="save_payment_method"),
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("create-intent/", views.create_payment_intent, name="create_payment_intent"),
    path("payment-method/delete/", views.delete_payment_method, name="delete_payment_method"),
    path("payment-method/set-default/", views.set_default_payment_method, name="set_default_payment_method"),
    # path("payment-method/<str:org_id>/", views.get_payment_method, name="get_payment_method"),
    path("payment-method/<str:org_id>/", views.get_all_payment_methods, name="get_all_payment_methods"),
    path("usage/<str:org_id>/", views.get_usage_data, name="get_usage_data"),
    path("billing-history/<str:org_id>/", views.get_billing_history, name="get_billing_history"),
    path("update_billing_history/", views.update_billing_history, name="update_billing_history"),
]
