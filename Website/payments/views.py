import json
import time
import stripe
from stripe import error as stripe_error
import random
import logging

logger = logging.getLogger(__name__)

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from typing import Union

from core.decorators import oauth_required, AuthHttpRequest
import stacks.services as stack_services
from stacks.models import PurchasableStack, StackDatabase, Stack
from organizations.models import Organization
from organizations.services import get_organization
from accounts.models import UserProfile
from core.helpers import request_helpers
from projects.models import Project
from payments.models import usage_information, billing_history
from core.utils.DeployBoxIAC.main import DeployBoxIAC

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


def save_stripe_payment_method(request: AuthHttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    try:
        data = json.loads(request.body)
        payment_method_id = data.get("payment_method_id")
        organization_id = data.get(
            "organization_id"
        )  # Assuming organizationId is used as customerId

        organization = get_object_or_404(Organization, id=organization_id)
        customer_id = organization.stripe_customer_id

        print(
            f"Payment Method ID: {payment_method_id}, Customer ID: {customer_id}",
            "Organization ID:",
            organization_id,
        )

        if not payment_method_id or not customer_id:
            return JsonResponse(
                {"error": "Missing paymentMethodId or customerId"}, status=400
            )

        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,
        )

        # Set the payment method as the default for the customer
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        return JsonResponse(
            {"message": "Payment method saved successfully."}, status=200
        )

    except stripe_error.StripeError as e:  # type: ignore
        return JsonResponse({"error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse(
            {"error": f"An error occurred while saving the payment method: {e}"}, status=400
        )

def create_payment_intent(request: AuthHttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    try:
        data = json.loads(request.body)
        organization_id = data.get("organization_id")

        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
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


@oauth_required()
def create_checkout_session(request: AuthHttpRequest, org_id: str) -> JsonResponse:
    auth_user = request.auth_user

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

    price_id = PurchasableStack.objects.get(id=stack_id).price_id

    try:
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


def record_usage(subscription_item_id, quantity):
    try:
        stripe.UsageRecord.create(
            subscription_item=subscription_item_id,
            quantity=quantity,  # Number of resources consumed
            timestamp=int(time.time()),  # Current timestamp
            action="increment",  # Add usage incrementally
        )
    except Exception as e:
        print(f"Error recording usage: {e}")


def stripe_webhook(request: HttpRequest) -> Union[HttpResponse, JsonResponse]:
    # Use `stripe listen --forward-to http://127.0.0.1:8000/api/v1/payments/webhook/` to listen for events
    WEBHOOK_SECRET = settings.STRIPE.get("WEBHOOK_SECRET", None)
    # WEBHOOK_SECRET = (
    #     "whsec_cae902cfa6db0bd7ecb8d400c97120467be8afb9304229d650f0dc3f4a24aca2"
    # )
    print(f"Webhook secret: {WEBHOOK_SECRET}")

    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        print(f"Error parsing webhook payload: {e}")
        return HttpResponse("Invalid payload", status=400)
    except stripe_error.SignatureVerificationError as e:  # type: ignore
        # Invalid signature
        print(f"Error verifying signature: {e}")
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

        list_of_adjectives = [
            "Superb",
            "Incredible",
            "Fantastic",
            "Amazing",
            "Awesome",
            "Brilliant",
            "Exceptional",
            "Outstanding",
            "Remarkable",
            "Extraordinary",
            "Magnificent",
            "Spectacular",
            "Stunning",
            "Impressive",
        ]

        list_of_nouns = [
            "Stack",
            "Project",
            "Application",
            "Service",
            "Solution",
            "Platform",
            "System",
            "Framework",
            "Architecture",
            "Design",
            "Model",
            "Structure",
            "Configuration",
        ]

        # Generate a random name for the stack
        random_adjective = random.choice(list_of_adjectives)
        random_noun = random.choice(list_of_nouns)
        random_name = f"{random_adjective} {random_noun}"

        # Create a stack entry for the user
        stack_services.add_stack(
            name=random_name,
            project_id=project.id,
            purchasable_stack_id=purchased_stack.id,
        )

    return HttpResponse(status=200)


def create_invoice(customer_id, dollar_amount, description) -> str:
    try:
        # Step 1: Create an invoice item
        stripe.InvoiceItem.create(
            customer=customer_id,
            amount=int(100 * dollar_amount),
            currency="usd",  # You can change the currency if needed
            description=description,
        )

        # Step 2: Create the invoice for the customer
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=False,  # Automatically finalizes and sends the invoice
        )

        # Step 3: Finalize the invoice (send to customer)
        invoice.finalize_invoice()

        return invoice.id, invoice.hosted_invoice_url

    except stripe_error.StripeError as e:  # type: ignore
        print(f"Error creating invoice: {e}")
        return None

    except Exception as e:
        print(f"Error creating invoice: {e}")
        return None


def get_customer_id(org_id):
    # Query the UserProfile by the provided user_id
    try:
        org = Organization.objects.get(id=org_id)
        customer_id = (
            org.stripe_customer_id
        )  # Assuming customer_id is a field in UserProfile

        return customer_id

    except UserProfile.DoesNotExist:
        return None


def update_invoice_billing(request):
    if request.method == "POST":
        data = json.loads(request.body)
        stack_id = data.get("stack_id")
        cost = data.get("cost")
        updated_count = StackDatabase.objects.filter(stack_id=stack_id).update(
            current_usage=0
        )
        # billing = StackDatabase.objects.filter(stack_id=stack_id).update(
        #     pending_billed=F("pending_billed") + cost
        # )

        # Check if any rows were updated
        if updated_count > 0:
            # Successfully updated
            return JsonResponse(
                {"message": "Invoice billing updated successfully."}, status=200
            )
        else:
            # Failed to update (either no such stack_id or no change made)
            return JsonResponse(
                {"error": "Stack ID not found or already updated."}, status=400
            )


# @oauth_required()
# def create_price_item(request: HttpRequest) -> JsonResponse:
#     return pricing_services.create_price_item(request)


# @oauth_required()
# def update_price_item(request: HttpRequest) -> JsonResponse:
#     return pricing_services.update_price_item(request)


# @oauth_required()
# def delete_price_item(request: HttpRequest) -> JsonResponse:
#     return pricing_services.delete_price_item(request)


# @oauth_required()
# def get_price_item_by_name(request: HttpRequest, name: str) -> JsonResponse:
#     return pricing_services.get_price_item_by_name(request, name)


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

        organization = get_object_or_404(Organization, id=org_id)
        customer_id = organization.stripe_customer_id

        if not customer_id:
            return JsonResponse(
                {"error": "No Stripe customer found for this organization"}, status=404
            )

        # Get all payment methods for the customer
        payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card")

        # Get the customer to find the default payment method
        customer = stripe.Customer.retrieve(customer_id)
        default_payment_method_id = customer.invoice_settings.default_payment_method if customer.invoice_settings else None

        # Format all payment methods
        formatted_methods = []
        for pm in payment_methods.data:
            if pm.card:  # Check if card exists
                formatted_methods.append({
                    "id": pm.id,
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                    "is_default": pm.id == default_payment_method_id,
                })

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

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
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
        print(customer)
        default_payment_method_id = customer.invoice_settings.default_payment_method if customer.invoice_settings else None

        if default_payment_method_id:
            # Detach the payment method
            stripe.PaymentMethod.detach(default_payment_method_id)

            # Set the next available payment method as default
            if payment_methods.data:
                next_payment_method = next(
                    (
                        pm
                        for pm in payment_methods.data
                        if pm.id != default_payment_method_id
                    ),
                    None,
                )
                if next_payment_method:
                    stripe.Customer.modify(
                        customer_id,
                        invoice_settings={
                            "default_payment_method": next_payment_method.id
                        },
                    )

        else:
            stripe.PaymentMethod.detach(payment_method_id)

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

    try:
        organization_id = request.GET.get("organization_id")
        if not organization_id:
            return JsonResponse({"error": "organization_id is required"}, status=400)

        organization = get_object_or_404(Organization, id=organization_id)
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


def update_organization_usage(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":

        data = json.loads(request.body)
        return JsonResponse({"message": "Usage updated successfully."}, status=200)
    else:
        return JsonResponse({"error": "Invalid request method."}, status=405)

def update_billing_history(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":

        deploy_box = DeployBoxIAC()
        billing_info = deploy_box.get_billing_info(request.body)

        print("Billing info: ", billing_info)

        for stack_id, usage in billing_info.items():
            if usage.get("cost") < 1:
                usage["cost"] = 1.00
            try:
                stack = Stack.objects.get(pk=stack_id)
            except Stack.DoesNotExist:
                print(f"Stack with id {stack_id} not found.")
                continue
            description = f"Billed usage for stack {stack_id}"
            organization = stack.project.organization

            customer_id = get_customer_id(organization.id)
            if not customer_id:
                print(f"No customer id found for organization {organization.id}")
                continue

            invoice_id, invoice_url = create_invoice(customer_id, usage.get("cost", 0.0), description)

            if not invoice_id:
                print(f"Failed to create invoice for stack {stack_id}")
                continue

            billing_history.objects.create(
                organization_id=organization.id,
                billed_usage=usage.get("billed_usage", 0),
                amount=usage.get("cost", 0.0),
                description=description,
                stripe_invoice_id=invoice_id,
                stripe_invoice_hosted_url=invoice_url,
                payment_method="default",
                status="pending",
            )

        return JsonResponse({"message": "Billing history updated successfully.", "billing_info": billing_info}, status=200)

        data = json.loads(request.body)
        update_status = data.get("status", None)
        billing_id = data.get("billing_id", None)
        print("update_status: ", update_status)
        billed_ids = []

        if update_status:
            try:
                entry = billing_history.objects.get(id=billing_id)
                entry.status = update_status
                entry.save()
                return JsonResponse({"message": "Billing history updated successfully."}, status=200)
            except billing_history.DoesNotExist:
                print(f"Billing history entry with id {billing_id} not found.")
                return JsonResponse({"error": "Billing history entry not found."}, status=404)

        try:
            print("Data: ", data)
            for stack_id, usage in data.items():
                stack_id = stack_id.strip('-rg')  # Remove '-rg' suffix if present
                stack = get_object_or_404(Stack, id=stack_id)
                organization = stack.project.organization

                # Create new entry
                try:
                    billed_instance = billing_history.objects.create(
                        organization_id=organization.id,
                        billed_usage=usage.get("billed_usage", 0),
                        amount=usage.get("cost", 0.0),
                        description=usage.get("description", "No description provided"),
                        payment_method=usage.get("payment_method", "default"),
                        status=usage.get("status", "pending"),
                    )

                    billed_ids.append(billed_instance.id)

                except Exception as e:
                    print(f"Failed to update billing history for stack {stack_id}: {str(e)}")
                    continue
            return JsonResponse({"message": "Billing history updated successfully.", "billed_ids": billed_ids}, status=200)
        except Exception as e:
            return JsonResponse({"message": "Failed to update billing history."}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method."}, status=405)
