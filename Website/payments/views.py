import datetime
import json
import stripe
from stripe import error as stripe_error
import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from typing import Union

from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
import calendar

import stacks.services as stack_services
from stacks.models import PurchasableStack, Stack
from stacks.metrics.models import MetricUsageRecord
from organizations.models import Organization
from organizations.services import get_organization
from core.helpers import request_helpers
from projects.models import Project
from payments.models import Invoice
from payments import services as payment_services

stripe.api_key = settings.STRIPE.get("SECRET_KEY")


def stripe_config(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        # Handle non-GET requests
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)
    stripe_config = {"public_key": STRIPE_PUBLISHABLE_KEY}
    return JsonResponse(stripe_config, status=200)


def save_stripe_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        data = json.loads(request.body)
        payment_method_id = data.get("payment_method_id")
        organization_id = data.get("organization_id")

        organization = get_organization(request.user, organization_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)
        customer_id = organization.stripe_customer_id

        if not payment_method_id or not customer_id:
            return JsonResponse(
                {"error": "Missing paymentMethodId or customerId"}, status=400
            )

        result = payment_services.save_payment_method(payment_method_id, customer_id)
        return JsonResponse(result, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while saving the payment method: {e}"}, status=400
        )

def create_payment_intent(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        data = json.loads(request.body)
        organization_id = data.get("organization_id")

        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_organization(request.user, organization_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Create a SetupIntent for adding payment methods without charging
        setup_intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=["card"],
            usage="off_session",  # This allows the payment method to be used for future payments
        )

        return JsonResponse({
            "client_secret": setup_intent.client_secret,
            "setup_intent_id": setup_intent.id
        }, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while creating the setup intent: {e}"}, status=400
        )


def create_checkout_session(request: HttpRequest, org_id: str) -> JsonResponse:
    auth_user = request.user

    if not org_id:
        return JsonResponse({"error": "Organization ID is required"}, status=400)

    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    domain_url = settings.HOST

    try:
        stack_id, project_id = request_helpers.assertRequestFields(
            request, ["stack_id", "project_id"]
        )
    except request_helpers.MissingFieldError as e:
        return e.to_response()

    organization = get_organization(auth_user, org_id)

    if not organization:
        return JsonResponse({"error": "Organization not found"}, status=404)

    purchasable_stack = PurchasableStack.objects.get(id=stack_id)
    price_id = purchasable_stack.price_id

    try:
        # Check if the price is free (amount = 0)
        price = stripe.Price.retrieve(price_id)
        is_free = price.unit_amount == 0
        
        # Ensure organization has a Stripe customer ID
        if not organization.stripe_customer_id:
            # Create a new Stripe customer for the organization
            customer = stripe.Customer.create(
                email=organization.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                }
            )
            organization.stripe_customer_id = customer.id
            organization.save()
        
        has_payment_method, _ = check_organization_payment_methods(organization)

        if is_free and not has_payment_method:
            # Use setup mode for free stacks
            checkout_session = stripe.checkout.Session.create(
                metadata={
                    "purchasable_stack_id": stack_id,
                    "organization_id": organization.id,
                    "project_id": project_id,
                },
                customer=organization.stripe_customer_id,
                success_url=domain_url
                + "/payments/checkout/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/payments/cancelled",
                payment_method_types=["card"],
                mode="setup",
            )
        else:
            # Use payment mode for paid stacks
            checkout_session = stripe.checkout.Session.create(
                metadata={
                    "purchasable_stack_id": stack_id,
                    "organization_id": organization.id,
                    "project_id": project_id,
                },
                customer=organization.stripe_customer_id,
                success_url=domain_url
                + "/payments/checkout/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=domain_url + "/payments/cancelled",
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                payment_intent_data={
                    "setup_future_usage": "off_session",  # This tells Stripe to save the card for future payments
                },
            )
        return JsonResponse({"sessionId": checkout_session["id"]})
    except Exception as e:
        return JsonResponse({"error": str(e)})


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> Union[HttpResponse, JsonResponse]:
    # Use `stripe listen --forward-to http://127.0.0.1:8000/api/v1/payments/webhook/` to listen for events
    WEBHOOK_SECRET = settings.STRIPE.get("WEBHOOK_SECRET", None)

    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        logger.error("Error parsing webhook payload: %s", e)
        return HttpResponse("Invalid payload", status=400)
    except stripe_error.SignatureVerificationError as e:  # type: ignore
        # Invalid signature
        logger.error("Error verifying signature: %s", e)
        return HttpResponse("Invalid signature", status=400)

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        metadata = session.get("metadata", {})

        purchasable_stack_id = metadata.get("purchasable_stack_id")
        project_id = metadata.get("project_id")
        organization_id = metadata.get("organization_id")

        # Fetch the user based on the Stripe Customer ID
        organization = get_object_or_404(Organization, id=organization_id)

        project = get_object_or_404(Project, id=project_id, organization=organization)

        purchased_stack = get_object_or_404(PurchasableStack, id=purchasable_stack_id)

        random_name = payment_services.generate_random_stack_name()

        # Create a stack entry for the user
        stack_services.add_stack(
            name=random_name,
            project_id=project.id,
            purchasable_stack_id=purchased_stack.id,
        )

    elif event["type"] == "invoice.paid":
        invoice_data = event["data"]["object"]
        stripe_invoice_id = invoice_data["id"]
        try:
            invoice = Invoice.objects.get(stripe_invoice_id=stripe_invoice_id)
            invoice.status = "paid"
            invoice.save()
            logger.info(f"Invoice {stripe_invoice_id} marked as paid")
        except Invoice.DoesNotExist:
            logger.warning(f"Received invoice.paid for unknown invoice: {stripe_invoice_id}")

    elif event["type"] == "invoice.payment_failed":
        invoice_data = event["data"]["object"]
        stripe_invoice_id = invoice_data["id"]
        customer_id = invoice_data.get("customer", "unknown")
        logger.error(f"Payment failed for invoice {stripe_invoice_id}, customer {customer_id}")
        try:
            invoice = Invoice.objects.get(stripe_invoice_id=stripe_invoice_id)
            invoice.status = "open"  # Keep as open so retry can happen
            invoice.save()
        except Invoice.DoesNotExist:
            pass

    elif event["type"] == "payment_method.detached":
        pm_data = event["data"]["object"]
        pm_id = pm_data["id"]
        logger.info(f"Payment method {pm_id} detached from Stripe")

    return HttpResponse(status=200)


def create_invoice(customer_id, dollar_amount, description) -> tuple[str, str] | None:
    return payment_services.create_invoice(customer_id, dollar_amount, description)


def get_customer_id(org_id):
    try:
        org = Organization.objects.get(id=org_id)
        return org.stripe_customer_id
    except Organization.DoesNotExist:
        return None


def check_organization_payment_methods(organization):
    """Check if an organization has payment methods set up."""
    payment_services.ensure_stripe_customer(organization)
    has_methods = payment_services.organization_has_payment_method(organization)
    if not has_methods:
        return False, "No payment methods found for this organization. Please add a payment method before making purchases."
    return True, None


def get_payment_method(request: HttpRequest, org_id: str) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        if not org_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=org_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Retrieve the customer's default payment method
        customer = stripe.Customer.retrieve(
            customer_id, expand=["invoice_settings.default_payment_method"]
        )

        if not customer:
            return JsonResponse({"error": "No customer found"}, status=404)

        if not customer.invoice_settings:
            return JsonResponse({"error": "Invoice settings not found"}, status=404)

        default_payment_method_id = customer.invoice_settings.default_payment_method  # type: ignore

        if not default_payment_method_id:
            return JsonResponse({"error": "No payment method found"}, status=404)

        # Format the card information
        card_info = {
            "brand": default_payment_method_id.card.brand,  # type: ignore
            "last4": default_payment_method_id.card.last4,  # type: ignore
            "exp_month": default_payment_method_id.card.exp_month,  # type: ignore
            "exp_year": default_payment_method_id.card.exp_year,  # type: ignore
        }

        return JsonResponse(card_info, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while retrieving the payment method."},
            status=400,
        )


def get_all_payment_methods(request: HttpRequest, org_id: str) -> JsonResponse:
    """Get all payment methods for an organization."""
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        if not org_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        organization = get_organization(request.user, org_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        formatted_methods = payment_services.get_all_payment_methods(customer_id)
        return JsonResponse({"payment_methods": formatted_methods}, status=200)

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while retrieving payment methods."},
            status=400,
        )


def delete_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "DELETE":
        return JsonResponse(
            {"error": "Invalid request method. Only DELETE is allowed."}, status=405
        )

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_organization(request.user, organization_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Get all payment methods for the customer
        payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card")

        if len(payment_methods.data) <= 1:
            return JsonResponse(
                {
                    "error": "Cannot remove the only payment method. Please add another payment method first."
                },
                status=400,
            )

        payment_method_id = request.GET.get("payment_method_id")
        if not payment_method_id:
            return JsonResponse({"error": "payment_method_id is required"}, status=400)

        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        if not payment_method:
            return JsonResponse({"error": "Payment method not found"}, status=404)

        customer = stripe.Customer.retrieve(customer_id)
        logger.debug("Customer: %s", customer)
        default_payment_method_id = customer.invoice_settings.default_payment_method if customer.invoice_settings else None

        # Always detach the user-requested payment method
        stripe.PaymentMethod.detach(payment_method_id)

        # If the deleted card was the default, promote the next available card
        if default_payment_method_id and payment_method_id == default_payment_method_id:
            next_payment_method = next(
                (pm for pm in payment_methods.data if pm.id != payment_method_id),
                None,
            )
            if next_payment_method:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        "default_payment_method": next_payment_method.id
                    },
                )

        return JsonResponse(
            {"message": "Payment method removed successfully."}, status=200
        )

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while removing the payment method."},
            status=400,
        )


def set_default_payment_method(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_organization(request.user, organization_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        payment_method_id = request.GET.get("payment_method_id")
        if not payment_method_id:
            return JsonResponse({"error": "payment_method_id is required"}, status=400)

        # Verify the payment method exists and belongs to the customer
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        if not payment_method or payment_method.customer != customer_id:
            return JsonResponse({"error": "Payment method not found or doesn't belong to this customer"}, status=404)

        # Set the payment method as default for the customer
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        return JsonResponse(
            {"message": "Default payment method updated successfully."}, status=200
        )

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": "An error occurred while setting the default payment method."},
            status=400,
        )


def get_usage_data(request: HttpRequest, org_id: str) -> JsonResponse:
    """Get usage statistics for an organization."""
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        organization = get_organization(request.user, org_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)

        data = payment_services.get_usage_data(organization)
        return JsonResponse(data)

    except Exception as e:
        logger.error(f"Error fetching usage data: {e}")
        return JsonResponse(
            {"error": "An error occurred while retrieving usage data."},
            status=400,
        )


def get_billing_history(request: HttpRequest, org_id: str) -> JsonResponse:
    """Get billing history for an organization."""
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        organization = get_organization(request.user, org_id)
        if not organization:
            return JsonResponse({"error": "Organization not found or access denied"}, status=403)

        records = payment_services.get_billing_history(organization)
        return JsonResponse({"billing_history": records})

    except Exception as e:
        logger.error(f"Error fetching billing history: {e}")
        return JsonResponse(
            {"error": "An error occurred while retrieving billing history."},
            status=400,
        )


@csrf_exempt  # Called by crontainer (machine-to-machine)
def update_billing_history(request: HttpRequest) -> JsonResponse:
    """Trigger monthly invoice generation. Called by crontainer cron job."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    # TODO: Add authentication (e.g., shared secret or OAuth token check)

    try:
        results = payment_services.generate_monthly_invoices()
        return JsonResponse({"results": results, "count": len(results)})
    except Exception as e:
        logger.error(f"Error generating invoices: {e}")
        return JsonResponse({"error": "Invoice generation failed"}, status=500)
