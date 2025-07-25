from django.urls import path
from . import views

urlpatterns = [
    # Stripe configuration
    path("config/", views.stripe_config, name="stripe_config"),
    # Checkout and webhook
    path("checkout/create/<str:org_id>/", views.create_checkout_session, name="checkout_create"),
    path("save-payment-method/", views.save_stripe_payment_method, name="save_payment_method"),
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),
    # Invoice management
    path("invoices/create/", views.create_invoice, name="invoice_create"),
    # Customer management
    path("customers/get_customer_id/", views.get_customer_id, name="customer_detail"),
    # Payment method management
    path("create-intent/", views.create_payment_intent, name="create_payment_intent"),
    path("payment-method/delete/", views.delete_payment_method, name="delete_payment_method"),
    path("payment-method/set-default/", views.set_default_payment_method, name="set_default_payment_method"),
    path("payment-method/<str:org_id>/", views.get_payment_method, name="get_payment_method"),
    path("payment-methods/<str:org_id>/", views.get_all_payment_methods, name="get_all_payment_methods"),
    path("update_billing_history/", views.update_billing_history, name="update_billing_history"),
    # Price management
    # path("prices/", views.create_price_item, name="price_create"),
    # path("prices/<str:price_id>/update/", views.update_price_item, name="price_update"),
    # path("prices/<str:price_id>/delete/", views.delete_price_item, name="price_delete"),
    # path("prices/name/<str:name>/", views.get_price_item_by_name, name="price_by_name"),
]
